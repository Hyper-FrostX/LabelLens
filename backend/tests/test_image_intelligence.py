import cv2
import numpy as np
from PIL import Image

from app.services.image_intelligence import (
    _deskew,
    _perspective_transform,
    create_preprocessed_variants,
    detect_food_symbols,
)


def test_preprocessing_creates_copies_without_mutating_the_uploaded_image():
    image = Image.new("RGB", (800, 500), "white")
    pixels_before = np.asarray(image).copy()

    variants, metadata = create_preprocessed_variants(image)

    assert len(variants) >= 2
    assert all(variant.image.ndim in (2, 3) for variant in variants)
    assert all(max(variant.image.shape[:2]) <= 3200 for variant in variants)
    assert np.array_equal(np.asarray(image), pixels_before)
    assert metadata["original_image_size"] == {"width": 800, "height": 500}
    assert metadata["preprocessing_methods"]


def test_skew_detection_corrects_rotated_text_lines():
    image = np.full((500, 700, 3), 255, dtype=np.uint8)
    for y in range(120, 380, 35):
        cv2.line(image, (80, y), (620, y), (0, 0, 0), 4)
    rotation = cv2.getRotationMatrix2D((350, 250), 4, 1)
    skewed = cv2.warpAffine(image, rotation, (700, 500), borderValue=(255, 255, 255))

    corrected, transform, correction_degrees = _deskew(skewed)

    assert abs(correction_degrees) >= 0.35
    assert abs(correction_degrees) <= 10
    assert corrected.shape[0] >= skewed.shape[0]
    assert corrected.shape[1] >= skewed.shape[1]
    assert transform.shape == (3, 3)


def test_perspective_correction_finds_a_large_label_quadrilateral():
    image = np.full((500, 500, 3), 245, dtype=np.uint8)
    corners = np.array([[60, 40], [440, 70], [420, 460], [40, 430]], dtype=np.int32)
    cv2.fillConvexPoly(image, corners, (255, 255, 255))
    cv2.polylines(image, [corners], True, (10, 10, 10), 8)

    corrected, transform, applied = _perspective_transform(image)

    assert applied is True
    assert corrected.shape[0] >= 200
    assert corrected.shape[1] >= 200
    assert not np.array_equal(transform, np.eye(3, dtype=np.float32))


def test_food_symbol_detection_reports_visual_regions_without_calibrated_confidence():
    image = np.full((500, 600, 3), 245, dtype=np.uint8)
    cv2.circle(image, (100, 100), 42, (0, 170, 35), thickness=-1)
    triangle = np.array([[280, 50], [230, 150], [330, 150]], dtype=np.int32)
    cv2.fillConvexPoly(image, triangle, (135, 75, 35))

    result = detect_food_symbols(Image.fromarray(image))

    assert result["image_inspected"] is True
    assert result["vegetarian"]["status"] == "DETECTED"
    assert result["vegetarian"]["confidence_state"] == "MEDIUM_CONFIDENCE"
    assert result["vegetarian"]["confidence"] is None
    assert result["vegetarian"]["region"]["coordinate_space"] == "exif_oriented_original_pixels"
    assert result["non_vegetarian"]["status"] == "DETECTED"
    assert result["non_vegetarian"]["geometry_evidence"]["shape"] == "triangle"


def test_uncertain_or_absent_food_symbols_are_not_asserted():
    image = Image.new("RGB", (300, 200), (245, 245, 245))

    result = detect_food_symbols(image)

    assert result["vegetarian"]["status"] == "NOT_DETECTED"
    assert result["non_vegetarian"]["status"] == "NOT_DETECTED"
    assert result["vegetarian"]["confidence"] is None
