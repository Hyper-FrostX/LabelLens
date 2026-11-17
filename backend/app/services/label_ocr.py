import os
import re
import shutil
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
from pytesseract import Output, TesseractError, TesseractNotFoundError

from app.services.image_intelligence import (
    ImageVariant,
    create_preprocessed_variants,
    detect_food_symbols,
)

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_PIXELS = 25_000_000
MIN_OCR_IMAGE_DIMENSION = 1200
MAX_OCR_IMAGE_DIMENSION = 3200
STANDARD_WINDOWS_TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


class InvalidImageError(ValueError):
    pass


class UnsupportedImageFormatError(ValueError):
    pass


class ImageTooLargeError(ValueError):
    pass


class OCRServiceError(RuntimeError):
    pass


def configure_tesseract() -> str | None:
    """Configure pytesseract from an explicit path, PATH, or Windows default."""
    configured_path = os.environ.get("TESSERACT_CMD")
    if configured_path:
        configured_path = configured_path.strip().strip('"')
        discovered_path = shutil.which(configured_path)
        if discovered_path is None:
            try:
                if Path(configured_path).is_file():
                    discovered_path = configured_path
            except (OSError, ValueError):
                discovered_path = None
        if discovered_path is None:
            return None
        pytesseract.pytesseract.tesseract_cmd = discovered_path
        return discovered_path

    discovered_path = shutil.which("tesseract")
    if discovered_path:
        pytesseract.pytesseract.tesseract_cmd = discovered_path
        return discovered_path

    if os.name == "nt" and STANDARD_WINDOWS_TESSERACT_PATH.is_file():
        discovered_path = str(STANDARD_WINDOWS_TESSERACT_PATH)
        pytesseract.pytesseract.tesseract_cmd = discovered_path
        return discovered_path

    return None


def _resize_for_ocr(image: Image.Image) -> Image.Image:
    width, height = image.size
    longest_dimension = max(width, height)
    if longest_dimension < MIN_OCR_IMAGE_DIMENSION:
        scale = min(2, MIN_OCR_IMAGE_DIMENSION / longest_dimension)
    elif longest_dimension > MAX_OCR_IMAGE_DIMENSION:
        scale = MAX_OCR_IMAGE_DIMENSION / longest_dimension
    else:
        return image

    return image.resize(
        (max(1, round(width * scale)), max(1, round(height * scale))),
        Image.Resampling.LANCZOS,
    )


def _preprocess_image(image: Image.Image) -> Image.Image:
    """Create a grayscale, contrast-normalized copy with light noise reduction."""
    grayscale = _resize_for_ocr(image.convert("L"))
    denoised = grayscale.filter(ImageFilter.MedianFilter(size=3))
    return ImageOps.autocontrast(denoised, cutoff=1)


def _merge_ocr_text(*results: str) -> str:
    """Preserve OCR lines in order while dropping normalized duplicates."""
    lines: list[str] = []
    seen: set[str] = set()
    for result in results:
        for line in result.splitlines():
            normalized = "".join(character.casefold() for character in line if character.isalnum())
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            lines.append(line)
    return "\n".join(lines)


def _extract_right_region_text(image: Image.Image) -> str:
    """OCR the right half as a supplemental pass for narrow label columns."""
    width, height = image.size
    right_region = image.crop((width // 2, 0, width, height))
    enhanced = ImageOps.autocontrast(right_region.convert("L"), cutoff=1)
    scale = max(1, min(2, 1200 // max(1, enhanced.width)))
    if scale > 1:
        enhanced = enhanced.resize(
            (enhanced.width * scale, enhanced.height * scale),
            Image.Resampling.LANCZOS,
        )
    return pytesseract.image_to_string(enhanced, config="--psm 6")


def validate_image(image_bytes: bytes) -> None:
    """Decode the uploaded image and verify its actual format and dimensions."""
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise UnsupportedImageFormatError(
                    "Supported image formats are JPEG, PNG, and WebP."
                )

            width, height = image.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise ImageTooLargeError(
                    "Image dimensions exceed the 25-megapixel limit."
                )

            image.load()
    except (InvalidImageError, UnsupportedImageFormatError, ImageTooLargeError):
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise InvalidImageError("Uploaded file is not a valid image.") from error


_REGION_PATTERNS = {
    "product_name": re.compile(
        r"\b(?:product\s+name|name\s+of\s+(?:the\s+)?(?:product|food)|food\s+name)\b",
        re.IGNORECASE,
    ),
    "ingredients": re.compile(r"\bingredients?\b", re.IGNORECASE),
    "nutrition": re.compile(
        r"\b(?:nutrition|energy|protein|carbohydrates?|total\s+fat|"
        r"saturated\s+fat|trans\s+fat|sugars?|sodium|salt|per\s*100\s*(?:g|ml))\b",
        re.IGNORECASE,
    ),
    "allergen": re.compile(r"\b(?:allergens?|contains|may\s+contain)\b", re.IGNORECASE),
    "fssai_license": re.compile(r"\bfssai\b", re.IGNORECASE),
    "date_markings": re.compile(
        r"\b(?:mfg|mfd|manufactur|pkd|packed\s+on|best\s*before|expiry|exp\.?|use\s*by)\b",
        re.IGNORECASE,
    ),
    "net_quantity": re.compile(
        r"\b(?:net\s*(?:qty|quantity|weight|contents?)|quantity)\b",
        re.IGNORECASE,
    ),
    "manufacturer": re.compile(
        r"\b(?:manufactured|packed|marketed|imported|distributed)\s+by\b",
        re.IGNORECASE,
    ),
    "consumer_care": re.compile(
        r"\b(?:consumer|customer)\s*(?:care|complaint|service)|\bhelpline\b",
        re.IGNORECASE,
    ),
}
_FIELD_REGION = {
    "product_name": "product_name",
    "basis": "nutrition",
    "serving_size_text": "nutrition",
    "ingredients_text": "ingredients",
    "ingredients": "ingredients",
    "allergens": "allergen",
    "may_contain": "allergen",
    "fssai_license_number": "fssai_license",
    "nutrients": "nutrition",
}


def _image_to_pil(image: np.ndarray) -> Image.Image:
    if image.ndim == 2:
        return Image.fromarray(image)
    if image.shape[2] == 3:
        return Image.fromarray(image)
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA))


def _map_ocr_box(
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    transform: np.ndarray,
    source_size: tuple[int, int],
    crop_offset: tuple[int, int] = (0, 0),
) -> dict:
    x += crop_offset[0]
    y += crop_offset[1]
    corners = np.array(
        [
            [x, y],
            [x + width, y],
            [x + width, y + height],
            [x, y + height],
        ],
        dtype=np.float32,
    ).reshape(-1, 1, 2)
    inverse = np.linalg.inv(transform.astype(np.float64)).astype(np.float32)
    mapped = cv2.perspectiveTransform(corners, inverse).reshape(-1, 2)
    source_width, source_height = source_size
    left = max(0, min(source_width, int(np.floor(mapped[:, 0].min()))))
    top = max(0, min(source_height, int(np.floor(mapped[:, 1].min()))))
    right = max(left, min(source_width, int(np.ceil(mapped[:, 0].max()))))
    bottom = max(top, min(source_height, int(np.ceil(mapped[:, 1].max()))))
    return {
        "x": left,
        "y": top,
        "width": right - left,
        "height": bottom - top,
        "coordinate_space": "exif_oriented_original_pixels",
    }


def _parse_ocr_data(
    data: dict,
    *,
    variant: ImageVariant,
    source_size: tuple[int, int],
    crop_offset: tuple[int, int] = (0, 0),
) -> tuple[list[dict], list[float]]:
    grouped = {}
    confidences = []
    texts = data.get("text", [])
    for index, raw_text in enumerate(texts):
        text = str(raw_text).strip()
        if not text:
            continue
        try:
            confidence = float(data.get("conf", [])[index])
        except (IndexError, TypeError, ValueError):
            confidence = None
        if confidence is not None and confidence >= 0:
            confidences.append(confidence)
        key = tuple(
            values[index] if isinstance(values, (list, tuple)) and index < len(values) else 0
            for values in (
                data.get(name)
                for name in ("page_num", "block_num", "par_num", "line_num")
            )
        )
        item = grouped.setdefault(
            key,
            {
                "words": [],
                "confidences": [],
                "left": [],
                "top": [],
                "right": [],
                "bottom": [],
            },
        )
        item["words"].append(text)
        if confidence is not None and confidence >= 0:
            item["confidences"].append(confidence)
        try:
            left = int(data["left"][index])
            top = int(data["top"][index])
            right = left + int(data["width"][index])
            bottom = top + int(data["height"][index])
        except (IndexError, KeyError, TypeError, ValueError):
            continue
        item["left"].append(left)
        item["top"].append(top)
        item["right"].append(right)
        item["bottom"].append(bottom)

    lines = []
    for item in grouped.values():
        if not item["left"]:
            continue
        x = min(item["left"])
        y = min(item["top"])
        width = max(item["right"]) - x
        height = max(item["bottom"]) - y
        processed_box = {
            "x": x + crop_offset[0],
            "y": y + crop_offset[1],
            "width": width,
            "height": height,
        }
        lines.append(
            {
                "text": " ".join(item["words"]),
                "ocr_confidence": (
                    round(sum(item["confidences"]) / len(item["confidences"]), 2)
                    if item["confidences"]
                    else None
                ),
                "processing_method": variant.method,
                "processed_coordinates": processed_box,
                "source_coordinates": _map_ocr_box(
                    x,
                    y,
                    width,
                    height,
                    transform=variant.source_to_processed,
                    source_size=source_size,
                    crop_offset=crop_offset,
                ),
            }
        )
    return lines, confidences


def _regions_from_lines(
    lines: list[dict],
    *,
    processed_size: tuple[int, int],
    source_size: tuple[int, int],
    transform: np.ndarray,
) -> list[dict]:
    processed_width, processed_height = processed_size
    matched = {
        region_type: [
            line for line in lines if pattern.search(line["text"])
        ]
        for region_type, pattern in _REGION_PATTERNS.items()
    }
    if not matched["product_name"]:
        top_lines = [
            line
            for line in lines
            if line["processed_coordinates"]["y"] < processed_height * 0.22
        ]
        if top_lines:
            matched["product_name"] = [top_lines[0]]

    regions = []
    for region_type, anchors in matched.items():
        if not anchors:
            continue
        anchor = min(anchors, key=lambda item: item["processed_coordinates"]["y"])
        anchor_box = anchor["processed_coordinates"]
        if region_type in {"ingredients", "nutrition"}:
            y = max(0, anchor_box["y"] - 8)
            end_y = min(processed_height, y + int(processed_height * 0.36))
            supporting = [
                line for line in lines
                if y <= line["processed_coordinates"]["y"] <= end_y
            ]
            x, right = 0, processed_width
        elif region_type == "product_name":
            x, y = 0, 0
            right, end_y = processed_width, min(
                processed_height,
                max(int(processed_height * 0.24), anchor_box["y"] + anchor_box["height"] * 4),
            )
            supporting = [
                line for line in lines
                if line["processed_coordinates"]["y"] <= end_y
            ]
        else:
            pad_x = max(16, int(processed_width * 0.025))
            pad_y = max(10, int(processed_height * 0.012))
            x = max(0, anchor_box["x"] - pad_x)
            y = max(0, anchor_box["y"] - pad_y)
            right = min(processed_width, anchor_box["x"] + anchor_box["width"] + pad_x * 2)
            end_y = min(processed_height, anchor_box["y"] + anchor_box["height"] + pad_y * 2)
            supporting = anchors

        region_width = max(1, right - x)
        region_height = max(1, end_y - y)
        region_box = _map_ocr_box(
            x,
            y,
            region_width,
            region_height,
            transform=transform,
            source_size=source_size,
        )
        region_text = "\n".join(
            dict.fromkeys(
                line["text"]
                for line in sorted(
                    supporting,
                    key=lambda item: (
                        item["processed_coordinates"]["y"],
                        item["processed_coordinates"]["x"],
                    ),
                )
            )
        )
        confidences = [
            line["ocr_confidence"]
            for line in supporting
            if line["ocr_confidence"] is not None
        ]
        regions.append(
            {
                "region_type": region_type,
                "source_coordinates": region_box,
                "extracted_text": region_text,
                "ocr_confidence": (
                    round(sum(confidences) / len(confidences), 2)
                    if confidences
                    else None
                ),
                "confidence_state": (
                    "MEDIUM_CONFIDENCE"
                    if confidences
                    else "NEEDS_MANUAL_REVIEW"
                ),
                "processing_method": anchor["processing_method"],
                "review_status": "NEEDS_MANUAL_REVIEW",
                "processed_coordinates": {
                    "x": x,
                    "y": y,
                    "width": region_width,
                    "height": region_height,
                },
            }
        )
    return regions


def _region_crops(image: np.ndarray, regions: list[dict]) -> list[tuple[str, np.ndarray, tuple[int, int]]]:
    useful_types = {
        "ingredients",
        "nutrition",
        "allergen",
        "fssai_license",
        "date_markings",
        "net_quantity",
        "manufacturer",
    }
    crops = []
    seen = set()
    for region in regions:
        region_type = region["region_type"]
        if region_type not in useful_types or region_type in seen:
            continue
        box = region["processed_coordinates"]
        x, y = box["x"], box["y"]
        width, height = box["width"], box["height"]
        if width <= 0 or height <= 0:
            continue
        crops.append((region_type, image[y : y + height, x : x + width], (x, y)))
        seen.add(region_type)
    return crops[:7]


def _normalize_search_text(value: str) -> str:
    return "".join(character.casefold() for character in value if character.isalnum())


def _field_metadata(parsed: dict, lines: list[dict], regions: list[dict]) -> list[dict]:
    fields = []
    extracted_fields = parsed.get("extracted_fields", {})
    for field_name, field_value in extracted_fields.items():
        if field_name == "nutrients":
            source_fields = [
                (f"nutrients.{name}", item, "nutrient")
                for name, item in field_value.items()
            ]
        else:
            kind = (
                "ingredient"
                if field_name in {"ingredients", "ingredients_text"}
                else "allergen"
                if field_name in {"allergens", "may_contain"}
                else "license"
                if field_name == "fssai_license_number"
                else "nutrition"
                if field_name in {"basis", "serving_size_text"}
                else field_name
            )
            source_fields = [(field_name, field_value, kind)]
        for qualified_name, item, field_type in source_fields:
            if not isinstance(item, dict):
                item = {"value": item, "source_text": None, "confidence": None}
            value = item.get("value")
            source_text = item.get("source_text")
            search_source = _normalize_search_text(source_text or "")
            matching_lines = [
                line for line in lines
                if search_source
                and (
                    _normalize_search_text(line["text"]) in search_source
                    or search_source in _normalize_search_text(line["text"])
                )
            ]
            confidences = [
                line["ocr_confidence"]
                for line in matching_lines
                if line["ocr_confidence"] is not None
            ]
            ocr_confidence = (
                round(sum(confidences) / len(confidences), 2)
                if confidences
                else None
            )
            if value is None:
                confidence_state = (
                    "NEEDS_MANUAL_REVIEW"
                    if source_text
                    else "NOT_DETECTED"
                )
            elif ocr_confidence is None:
                confidence_state = "NEEDS_MANUAL_REVIEW"
            elif ocr_confidence >= 85:
                confidence_state = "HIGH_CONFIDENCE"
            elif ocr_confidence >= 60:
                confidence_state = "MEDIUM_CONFIDENCE"
            else:
                confidence_state = "LOW_CONFIDENCE"

            region_type = _FIELD_REGION.get(field_name)
            region = next(
                (entry for entry in regions if entry["region_type"] == region_type),
                None,
            )
            fields.append(
                {
                    "field_name": qualified_name,
                    "field_type": field_type,
                    "extracted_value": value,
                    "original_value": value,
                    "ocr_confidence": ocr_confidence,
                    "confidence_state": confidence_state,
                    "processing_method": (
                        ", ".join(
                            dict.fromkeys(line["processing_method"] for line in matching_lines)
                        )
                        if matching_lines
                        else "multi_pass_ocr"
                    ),
                    "source_region": (
                        {
                            key: region[key]
                            for key in (
                                "region_type",
                                "source_coordinates",
                                "extracted_text",
                                "processing_method",
                            )
                        }
                        if region
                        else None
                    ),
                    "source_text": source_text,
                    "review_status": (
                        "NOT_DETECTED"
                        if value is None and not source_text
                        else "NEEDS_MANUAL_REVIEW"
                        if confidence_state in {"LOW_CONFIDENCE", "NEEDS_MANUAL_REVIEW"}
                        or item.get("needs_review", True)
                        else "PENDING_USER_REVIEW"
                    ),
                }
            )
    return fields


def _mean_confidence(confidences: list[float]) -> float | None:
    if not confidences:
        return None
    return round(sum(confidences) / len(confidences), 2)


def _run_ocr(
    image: np.ndarray,
    *,
    variant: ImageVariant,
    source_size: tuple[int, int],
    config: str,
    crop_offset: tuple[int, int] = (0, 0),
) -> tuple[str, list[dict], list[float]]:
    pil_image = _image_to_pil(image)
    text = pytesseract.image_to_string(pil_image, config=config)
    data = pytesseract.image_to_data(
        pil_image,
        config=config,
        output_type=Output.DICT,
    )
    lines, confidences = _parse_ocr_data(
        data,
        variant=variant,
        source_size=source_size,
        crop_offset=crop_offset,
    )
    return text, lines, confidences


def extract_image_data(image_bytes: bytes) -> dict:
    """Run local multi-pass OCR and return evidence-preserving image metadata."""
    try:
        validate_image(image_bytes)
        if configure_tesseract() is None:
            if os.environ.get("TESSERACT_CMD"):
                raise OCRServiceError(
                    "TESSERACT_CMD is set but does not point to an existing "
                    "Tesseract executable. Correct it or unset it, then "
                    "install Tesseract on PATH."
                )
            raise OCRServiceError(
                "Local Tesseract OCR is unavailable. Set TESSERACT_CMD to "
                "the full path of tesseract.exe, install Tesseract on PATH, "
                "or install it at the standard Windows location."
            )

        with Image.open(BytesIO(image_bytes)) as image:
            exif_orientation = image.getexif().get(274, 1)
            normalized_image = ImageOps.exif_transpose(image).convert("RGB")
            variants, processing = create_preprocessed_variants(normalized_image)
            processing["orientation_corrected"] = exif_orientation not in (None, 1)
            source_size = normalized_image.size
            pass_results = []
            raw_texts = []
            all_confidences = []
            for variant in variants:
                text, lines, confidences = _run_ocr(
                    variant.image,
                    variant=variant,
                    source_size=source_size,
                    config="--psm 6",
                )
                raw_texts.append(text)
                all_confidences.extend(confidences)
                mean_confidence = _mean_confidence(confidences)
                pass_results.append(
                    {
                        "variant": variant,
                        "text": text,
                        "lines": lines,
                        "confidences": confidences,
                        "mean_confidence": mean_confidence,
                        "score": (
                            (mean_confidence or 0)
                            + min(len(lines), 25) * 0.25
                        ),
                    }
                )

            best = max(
                pass_results,
                key=lambda result: result["score"],
                default=None,
            )
            if best is None:
                return {
                    "ocr_text": "",
                    "regions": [],
                    "fields": [],
                    "symbol_detection": detect_food_symbols(normalized_image),
                    "processing": processing,
                    "ocr_quality": {
                        "mean_word_confidence": None,
                        "confidence_basis": "Tesseract word-level TSV confidence; not field truth.",
                    },
                    "ocr_passes": [],
                }

            best_lines = best["lines"]
            best_variant = best["variant"]
            processed_size = (best_variant.image.shape[1], best_variant.image.shape[0])
            regions = _regions_from_lines(
                best_lines,
                processed_size=processed_size,
                source_size=source_size,
                transform=best_variant.source_to_processed,
            )
            region_lines = []
            for region_type, crop, offset in _region_crops(best_variant.image, regions):
                if crop.size == 0:
                    continue
                config = "--psm 6"
                text, lines, confidences = _run_ocr(
                    crop,
                    variant=best_variant,
                    source_size=source_size,
                    config=config,
                    crop_offset=offset,
                )
                raw_texts.append(text)
                region_lines.extend(lines)
                all_confidences.extend(confidences)
                region = next(
                    (item for item in regions if item["region_type"] == region_type),
                    None,
                )
                if region is not None and text.strip():
                    region["extracted_text"] = _merge_ocr_text(
                        region["extracted_text"],
                        text,
                    )
                    region["processing_method"] += f", region_ocr:{region_type}"

            all_lines = [
                line
                for result in pass_results
                for line in result["lines"]
            ] + region_lines
            ocr_text = _merge_ocr_text(
                *raw_texts,
                *[line["text"] for line in region_lines],
            )
            from app.services.label_parser import parse_label_text

            parsed = parse_label_text(ocr_text)
            fields = _field_metadata(parsed, all_lines, regions)
            return {
                "ocr_text": ocr_text,
                "raw_ocr_text": ocr_text,
                "regions": [
                    {key: value for key, value in region.items() if key != "processed_coordinates"}
                    for region in regions
                ],
                "fields": fields,
                "symbol_detection": detect_food_symbols(normalized_image),
                "processing": {
                    **processing,
                    "selected_variant": best_variant.method,
                    "ocr_strategies_run": len(variants),
                    "region_ocr_runs": len(region_lines) > 0,
                    "original_image_unchanged": True,
                },
                "ocr_quality": {
                    "mean_word_confidence": _mean_confidence(all_confidences),
                    "confidence_basis": (
                        "Mean Tesseract word-level TSV confidence across OCR passes; "
                        "not calibrated field correctness or regulatory evidence."
                    ),
                },
                "ocr_passes": [
                    {
                        "processing_method": result["variant"].method,
                        "mean_word_confidence": result["mean_confidence"],
                        "line_count": len(result["lines"]),
                        "text": result["text"],
                    }
                    for result in pass_results
                ],
            }
    except OCRServiceError:
        raise
    except cv2.error as error:
        raise OCRServiceError(
            "OpenCV could not preprocess this image. Try a smaller, clearer label image."
        ) from error
    except TesseractNotFoundError as error:
        raise OCRServiceError(
            "The configured Tesseract executable could not be launched. "
            "Check that TESSERACT_CMD points to an accessible executable."
        ) from error
    except TesseractError as error:
        raise OCRServiceError("Local Tesseract OCR could not process this image.") from error
    except np.linalg.LinAlgError as error:
        raise OCRServiceError(
            "Local image preprocessing could not process this label. Try a clearer image."
        ) from error


def extract_text(image_bytes: bytes) -> str:
    """Compatibility wrapper returning only merged OCR text."""
    return extract_image_data(image_bytes)["ocr_text"]
