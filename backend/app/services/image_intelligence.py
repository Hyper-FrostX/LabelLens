from dataclasses import dataclass
import math

import cv2
import numpy as np
from PIL import Image


MIN_OCR_DIMENSION = 1200
MAX_OCR_DIMENSION = 3200


@dataclass
class ImageVariant:
    image: np.ndarray
    method: str
    source_to_processed: np.ndarray
    skew_correction_degrees: float
    perspective_corrected: bool


def _pil_to_rgb_array(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGB"), dtype=np.uint8)


def _rgb_to_gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)


def _order_quad(points: np.ndarray) -> np.ndarray:
    ordered = np.zeros((4, 2), dtype=np.float32)
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).reshape(-1)
    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]
    ordered[1] = points[np.argmin(differences)]
    ordered[3] = points[np.argmax(differences)]
    return ordered


def _perspective_transform(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, bool]:
    height, width = image.shape[:2]
    gray = cv2.GaussianBlur(_rgb_to_gray(image), (5, 5), 0)
    edges = cv2.Canny(gray, 45, 130)
    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    image_area = float(width * height)
    candidates = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:20]:
        area = cv2.contourArea(contour)
        if not image_area * 0.25 <= area <= image_area * 0.97:
            continue
        polygon = cv2.approxPolyDP(
            contour,
            0.02 * cv2.arcLength(contour, True),
            True,
        )
        if len(polygon) == 4 and cv2.isContourConvex(polygon):
            candidates.append((area, polygon.reshape(4, 2).astype(np.float32)))
    if not candidates:
        return image, np.eye(3, dtype=np.float32), False

    _, points = max(candidates, key=lambda candidate: candidate[0])
    source = _order_quad(points)
    top_left, top_right, bottom_right, bottom_left = source
    out_width = int(
        max(
            np.linalg.norm(bottom_right - bottom_left),
            np.linalg.norm(top_right - top_left),
        )
    )
    out_height = int(
        max(
            np.linalg.norm(top_right - bottom_right),
            np.linalg.norm(top_left - bottom_left),
        )
    )
    if (
        out_width < 200
        or out_height < 200
        or out_width * out_height > image_area * 1.25
    ):
        return image, np.eye(3, dtype=np.float32), False
    destination = np.array(
        [
            [0, 0],
            [out_width - 1, 0],
            [out_width - 1, out_height - 1],
            [0, out_height - 1],
        ],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(source, destination)
    corrected = cv2.warpPerspective(
        image,
        transform,
        (out_width, out_height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return corrected, transform, True


def _deskew(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    gray = _rgb_to_gray(image)
    threshold = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )[1]
    points = cv2.findNonZero(threshold)
    if points is None or len(points) < 100:
        return image, np.eye(3, dtype=np.float32), 0.0
    raw_angle = cv2.minAreaRect(points)[-1]
    if raw_angle < -45:
        raw_angle += 90
    elif raw_angle > 45:
        raw_angle -= 90
    correction = -float(raw_angle)
    if abs(correction) < 0.35 or abs(correction) > 10:
        return image, np.eye(3, dtype=np.float32), 0.0

    height, width = image.shape[:2]
    radians = math.radians(correction)
    new_width = int(abs(height * math.sin(radians)) + abs(width * math.cos(radians)))
    new_height = int(abs(width * math.sin(radians)) + abs(height * math.cos(radians)))
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), correction, 1.0)
    matrix[0, 2] += new_width / 2 - width / 2
    matrix[1, 2] += new_height / 2 - height / 2
    corrected = cv2.warpAffine(
        image,
        matrix,
        (new_width, new_height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    transform = np.vstack([matrix, [0, 0, 1]]).astype(np.float32)
    return corrected, transform, correction


def _resize_ocr(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    height, width = image.shape[:2]
    longest = max(width, height)
    if longest < MIN_OCR_DIMENSION:
        scale = min(2.0, MIN_OCR_DIMENSION / longest)
    elif longest > MAX_OCR_DIMENSION:
        scale = MAX_OCR_DIMENSION / longest
    else:
        scale = 1.0
    if scale == 1.0:
        return image, np.eye(3, dtype=np.float32)
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    interpolation = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    resized = cv2.resize(image, size, interpolation=interpolation)
    return resized, np.diag([scale, scale, 1]).astype(np.float32)


def _enhance(image: np.ndarray) -> np.ndarray:
    gray = _rgb_to_gray(image)
    denoised = cv2.fastNlMeansDenoising(gray, None, h=5, templateWindowSize=7, searchWindowSize=21)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(denoised)
    illumination = cv2.GaussianBlur(clahe, (0, 0), sigmaX=25, sigmaY=25)
    normalized = cv2.divide(clahe, illumination, scale=255)
    blurred = cv2.GaussianBlur(normalized, (0, 0), sigmaX=1.1)
    sharpened = cv2.addWeighted(normalized, 1.25, blurred, -0.25, 2)
    return cv2.convertScaleAbs(sharpened, alpha=1.04, beta=1)


def _adaptive_threshold(image: np.ndarray) -> np.ndarray:
    gray = _enhance(image)
    denoised = cv2.medianBlur(gray, 3)
    block_size = max(15, min(51, (min(gray.shape[:2]) // 30) | 1))
    if block_size % 2 == 0:
        block_size += 1
    return cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        11,
    )


def create_preprocessed_variants(image: Image.Image) -> tuple[list[ImageVariant], dict]:
    """Create independent OCR copies; the input image is never modified."""
    original = _pil_to_rgb_array(image)
    perspective, perspective_matrix, perspective_corrected = _perspective_transform(original)

    geometries = [
        ("original", original, np.eye(3, dtype=np.float32), 0.0, False),
    ]
    deskewed, deskew_matrix, angle = _deskew(original)
    geometries.extend(
        [
            ("deskewed", deskewed, deskew_matrix, angle, False),
        ]
    )
    if perspective_corrected:
        perspective_deskewed, second_rotation, perspective_angle = _deskew(perspective)
        geometries.append(
            (
                "perspective_deskewed",
                perspective_deskewed,
                second_rotation @ perspective_matrix,
                perspective_angle,
                True,
            )
        )

    variants = []
    seen = set()
    for geometry_name, geometry, geometry_transform, skew, perspective_used in geometries:
        resized, resize_transform = _resize_ocr(geometry)
        transform = resize_transform @ geometry_transform
        if geometry_name == "original":
            method_images = [("oriented_original", resized)]
        else:
            enhanced = _enhance(resized)
            method_images = [
                (f"{geometry_name}_contrast_denoise_sharpen", enhanced),
                (f"{geometry_name}_adaptive_threshold", _adaptive_threshold(resized)),
            ]
        for method, processed in method_images:
            signature = (processed.shape, method.split("_")[-1], int(np.mean(processed)))
            if signature in seen:
                continue
            seen.add(signature)
            variants.append(
                ImageVariant(
                    image=processed,
                    method=method,
                    source_to_processed=transform,
                    skew_correction_degrees=skew,
                    perspective_corrected=perspective_used,
                )
            )
    return variants, {
        "original_image_size": {"width": image.width, "height": image.height},
        "orientation_corrected": False,
        "orientation_handling": "EXIF orientation is normalized before OpenCV preprocessing.",
        "perspective_correction_applied": perspective_corrected,
        "skew_correction_degrees": angle,
        "preprocessing_methods": [variant.method for variant in variants],
    }


def _candidate_regions(mask: np.ndarray, label: str, scale: float) -> list[dict]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = float(mask.shape[0] * mask.shape[1])
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if not max(30.0, image_area * 0.000025) <= area <= image_area * 0.04:
            continue
        x, y, width, height = cv2.boundingRect(contour)
        aspect = width / max(height, 1)
        if not 0.62 <= aspect <= 1.48:
            continue
        perimeter = cv2.arcLength(contour, True)
        circularity = (
            4 * math.pi * area / (perimeter * perimeter)
            if perimeter > 0
            else 0
        )
        polygon = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
        vertices = len(polygon)
        if label == "vegetarian" and circularity < 0.43 and not 4 <= vertices <= 8:
            continue
        if label == "non_vegetarian" and vertices != 3 and circularity < 0.43:
            continue
        strong_shape = (
            circularity >= 0.62
            if label == "vegetarian"
            else vertices == 3 or circularity >= 0.62
        )
        candidates.append(
            {
                "x": round(x / scale),
                "y": round(y / scale),
                "width": round(width / scale),
                "height": round(height / scale),
                "shape": "circle" if circularity >= 0.58 else "triangle" if vertices == 3 else "uncertain",
                "geometry_match": "strong" if strong_shape else "possible",
                "circularity": round(circularity, 2),
                "polygon_vertices": vertices,
            }
        )
    return sorted(
        candidates,
        key=lambda item: (
            item["geometry_match"] == "strong",
            item["circularity"],
            item["width"] * item["height"],
        ),
        reverse=True,
    )


def detect_food_symbols(image: Image.Image) -> dict:
    """Find plausible green circular and brown circular/triangular symbol marks."""
    rgb = _pil_to_rgb_array(image)
    height, width = rgb.shape[:2]
    scale = min(1.0, 1600 / max(width, height))
    if scale < 1:
        rgb = cv2.resize(
            rgb,
            (round(width * scale), round(height * scale)),
            interpolation=cv2.INTER_AREA,
        )
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    green_mask = cv2.inRange(
        hsv,
        np.array([32, 55, 35], dtype=np.uint8),
        np.array([95, 255, 255], dtype=np.uint8),
    )
    brown_mask = cv2.inRange(
        hsv,
        np.array([3, 45, 20], dtype=np.uint8),
        np.array([29, 255, 210], dtype=np.uint8),
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)
    brown_mask = cv2.morphologyEx(brown_mask, cv2.MORPH_CLOSE, kernel)

    results = {}
    for label, color_mask in (
        ("vegetarian", green_mask),
        ("non_vegetarian", brown_mask),
    ):
        candidates = _candidate_regions(color_mask, label, scale)
        candidate = candidates[0] if candidates else None
        if candidate is None:
            result_status = "NOT_DETECTED"
            confidence_state = "NOT_DETECTED"
            explanation = "No plausible colored symbol contour was found."
        elif candidate["geometry_match"] == "strong":
            result_status = "DETECTED"
            confidence_state = "MEDIUM_CONFIDENCE"
            explanation = (
                "A symbol-shaped region with the expected color family and geometry was detected. "
                "The heuristic is not calibrated; visually confirm the package mark."
            )
        else:
            result_status = "NEEDS_MANUAL_REVIEW"
            confidence_state = "NEEDS_MANUAL_REVIEW"
            explanation = "A possible colored mark was found, but its geometry is uncertain."
        results[label] = {
            "status": result_status,
            "confidence": None,
            "confidence_state": confidence_state,
            "method": "opencv_color_and_contour_heuristic",
            "region": (
                {
                    "x": candidate["x"],
                    "y": candidate["y"],
                    "width": candidate["width"],
                    "height": candidate["height"],
                    "coordinate_space": "exif_oriented_original_pixels",
                }
                if candidate
                else None
            ),
            "geometry_evidence": (
                {
                    "color_family": "green" if label == "vegetarian" else "brown",
                    "shape": candidate["shape"],
                    "circularity": candidate["circularity"],
                    "polygon_vertices": candidate["polygon_vertices"],
                }
                if candidate
                else None
            ),
            "candidate_count": len(candidates),
            "explanation": explanation,
        }
    return {
        **results,
        "image_inspected": True,
        "method_limitations": (
            "Color/contour heuristics can confuse branding, food imagery, and the legal mark. "
            "No symbol-specific trained model is used; confidence is not calibrated."
        ),
    }

