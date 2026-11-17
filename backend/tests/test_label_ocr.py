from io import BytesIO

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services import label_ocr


def _empty_tsv():
    return {
        "text": [],
        "conf": [],
        "page_num": [],
        "block_num": [],
        "par_num": [],
        "line_num": [],
        "left": [],
        "top": [],
        "width": [],
        "height": [],
    }


def _tsv_for_text(ocr_text: str):
    words = []
    line_ids = []
    tops = []
    for line_index, line in enumerate(ocr_text.splitlines()):
        for word in line.split():
            words.append(word)
            line_ids.append(line_index + 1)
            tops.append(30 + line_index * 60)
    count = len(words)
    return {
        "text": words,
        "conf": ["90"] * count,
        "page_num": ["1"] * count,
        "block_num": ["1"] * count,
        "par_num": ["1"] * count,
        "line_num": [str(value) for value in line_ids],
        "left": [str(20 + index * 45) for index in range(count)],
        "top": [str(value) for value in tops],
        "width": ["40"] * count,
        "height": ["20"] * count,
    }


def test_configure_tesseract_prefers_environment_variable(monkeypatch):
    configured_path = r"C:\Custom\Tesseract\tesseract.exe"
    monkeypatch.setenv("TESSERACT_CMD", configured_path)
    monkeypatch.setattr(
        label_ocr.shutil,
        "which",
        lambda candidate: configured_path if candidate == configured_path else None,
    )

    result = label_ocr.configure_tesseract()

    assert result == configured_path
    assert label_ocr.pytesseract.pytesseract.tesseract_cmd == configured_path


def test_configure_tesseract_discovers_from_path(monkeypatch):
    path_executable = r"C:\FromPath\tesseract.exe"
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.setattr(label_ocr.shutil, "which", lambda _: path_executable)

    result = label_ocr.configure_tesseract()

    assert result == path_executable
    assert label_ocr.pytesseract.pytesseract.tesseract_cmd == path_executable


def test_configure_tesseract_uses_standard_windows_path(monkeypatch, tmp_path):
    standard_executable = tmp_path / "tesseract.exe"
    standard_executable.touch()
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.setattr(label_ocr.os, "name", "nt")
    monkeypatch.setattr(label_ocr.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        label_ocr,
        "STANDARD_WINDOWS_TESSERACT_PATH",
        standard_executable,
    )

    result = label_ocr.configure_tesseract()

    assert result == str(standard_executable)
    assert label_ocr.pytesseract.pytesseract.tesseract_cmd == result


def test_configure_tesseract_rejects_an_invalid_explicit_path(monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD", r"C:\Missing\tesseract.exe")
    monkeypatch.setattr(label_ocr.shutil, "which", lambda _: None)

    assert label_ocr.configure_tesseract() is None


def test_extract_text_reports_missing_tesseract_without_running_ocr(
    monkeypatch, tmp_path
):
    image_bytes = BytesIO()
    Image.new("RGB", (2, 2), color="white").save(image_bytes, format="PNG")
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.setattr(label_ocr.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        label_ocr,
        "STANDARD_WINDOWS_TESSERACT_PATH",
        tmp_path / "missing-tesseract.exe",
    )

    def unexpected_ocr_call(*args, **kwargs):
        pytest.fail("OCR should not run when no executable is discoverable")

    monkeypatch.setattr(
        label_ocr.pytesseract,
        "image_to_string",
        unexpected_ocr_call,
    )

    with pytest.raises(label_ocr.OCRServiceError, match="TESSERACT_CMD"):
        label_ocr.extract_text(image_bytes.getvalue())


def test_extract_text_reports_invalid_configured_tesseract_path(
    monkeypatch, tmp_path
):
    image_bytes = BytesIO()
    Image.new("RGB", (2, 2), color="white").save(image_bytes, format="PNG")
    monkeypatch.setenv("TESSERACT_CMD", str(tmp_path / "missing-tesseract.exe"))
    monkeypatch.setattr(label_ocr.shutil, "which", lambda _: None)

    with pytest.raises(label_ocr.OCRServiceError, match="does not point"):
        label_ocr.extract_text(image_bytes.getvalue())


def test_preprocess_image_resizes_but_bounds_ocr_dimensions():
    small = Image.new("RGB", (100, 200), color="white")
    large = Image.new("RGB", (4000, 2000), color="white")

    assert label_ocr._preprocess_image(small).size == (200, 400)
    assert label_ocr._preprocess_image(large).size == (3200, 1600)


def test_extract_text_applies_exif_orientation_before_ocr(monkeypatch):
    image_bytes = BytesIO()
    image = Image.new("RGB", (300, 100), color="white")
    exif = Image.Exif()
    exif[274] = 6
    image.save(image_bytes, format="JPEG", exif=exif)
    observed_images = []
    monkeypatch.setattr(label_ocr, "configure_tesseract", lambda: "tesseract")
    monkeypatch.setattr(
        label_ocr.pytesseract,
        "image_to_string",
        lambda candidate, config: observed_images.append(candidate.size) or "",
    )
    monkeypatch.setattr(
        label_ocr.pytesseract,
        "image_to_data",
        lambda candidate, **kwargs: _empty_tsv(),
    )

    label_ocr.extract_text(image_bytes.getvalue())

    assert observed_images[0] == (200, 600)


def test_extract_text_uses_multiple_preprocessed_ocr_passes(
    monkeypatch,
):
    image_bytes = BytesIO()
    Image.new("RGB", (1000, 1000), color=(255, 225, 0)).save(
        image_bytes,
        format="PNG",
    )
    observed_images = []

    monkeypatch.setattr(label_ocr, "configure_tesseract", lambda: "tesseract")

    def fake_image_to_string(image, config):
        observed_images.append((image.copy(), config))
        return (
            "Ingredients: oats\nServing Size: 25 g\n"
            "Saturated Fat 0.8 g 4%\nSodium 249 mg 11%\n"
            "Total Sugars 3.4 g 3%\nAdded Sugars 1.5 g 2%\n"
        )

    monkeypatch.setattr(
        label_ocr.pytesseract,
        "image_to_string",
        fake_image_to_string,
    )
    monkeypatch.setattr(
        label_ocr.pytesseract,
        "image_to_data",
        lambda image, **kwargs: _empty_tsv(),
    )

    result = label_ocr.extract_image_data(image_bytes.getvalue())

    assert len(observed_images) >= 2
    assert observed_images[0][0].size == (1200, 1200)
    assert observed_images[0][0].mode in {"RGB", "L"}
    assert observed_images[0][1] == "--psm 6"
    assert result["processing"]["ocr_strategies_run"] >= 2
    assert result["processing"]["original_image_unchanged"] is True
    assert result["ocr_text"].count("Serving Size: 25 g") == 1
    assert "Saturated Fat 0.8 g 4%" in result["ocr_text"]
    assert "Sodium 249 mg 11%" in result["ocr_text"]
    assert "Total Sugars 3.4 g 3%" in result["ocr_text"]


def test_extract_text_with_real_tesseract_when_installed():
    if label_ocr.configure_tesseract() is None:
        pytest.skip("Tesseract executable is not installed")
    try:
        label_ocr.pytesseract.get_tesseract_version()
    except (
        label_ocr.TesseractNotFoundError,
        label_ocr.TesseractError,
        OSError,
    ):
        pytest.skip("Tesseract executable is not responding")

    image = Image.new("RGB", (1400, 600), color="white")
    draw = ImageDraw.Draw(image)
    draw.multiline_text(
        (40, 35),
        "Product Name: Oat Crunch\nPer 100 g\nTotal Sugars 4 g\nSodium 80 mg",
        fill="black",
        font=ImageFont.load_default(size=44),
        spacing=18,
    )
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")

    result = label_ocr.extract_text(image_bytes.getvalue())

    assert "Product Name: Oat Crunch" in result
    assert "Total Sugars 4 g" in result
    assert "Sodium 80 mg" in result


def test_merge_ocr_text_deduplicates_normalized_lines():
    result = label_ocr._merge_ocr_text(
        "Ingredients: oats\nSodium 249 mg",
        "ingredients: oats\nSodium 249 mg\nSugar 3.4 g",
    )

    assert result == (
        "Ingredients: oats\nSodium 249 mg\nSugar 3.4 g"
    )


def test_extract_image_data_returns_regions_confidence_and_source_coordinates(monkeypatch):
    image_bytes = BytesIO()
    Image.new("RGB", (500, 400), color="white").save(image_bytes, format="PNG")
    ocr_text = (
        "Product Name: Oat bar\n"
        "Ingredients: oats, honey\n"
        "Per 100 g\n"
        "Total Sugars 4 g"
    )
    monkeypatch.setattr(label_ocr, "configure_tesseract", lambda: "tesseract")
    monkeypatch.setattr(
        label_ocr.pytesseract,
        "image_to_string",
        lambda image, config: ocr_text,
    )
    monkeypatch.setattr(
        label_ocr.pytesseract,
        "image_to_data",
        lambda image, **kwargs: _tsv_for_text(ocr_text),
    )

    result = label_ocr.extract_image_data(image_bytes.getvalue())

    product_field = next(field for field in result["fields"] if field["field_name"] == "product_name")
    assert result["ocr_text"] == ocr_text
    assert product_field["extracted_value"] == "Oat bar"
    assert product_field["ocr_confidence"] == 90
    assert product_field["confidence_state"] == "HIGH_CONFIDENCE"
    assert product_field["review_status"] == "NEEDS_MANUAL_REVIEW"
    assert product_field["source_region"]["source_coordinates"]["coordinate_space"] == (
        "exif_oriented_original_pixels"
    )
    assert {region["region_type"] for region in result["regions"]} >= {
        "product_name",
        "ingredients",
        "nutrition",
    }
    assert result["processing"]["original_image_unchanged"] is True
    assert result["ocr_quality"]["mean_word_confidence"] == 90


def test_parse_ocr_data_handles_incomplete_tsv_columns():
    variant = label_ocr.create_preprocessed_variants(Image.new("RGB", (200, 200)))[0][0]
    lines, confidences = label_ocr._parse_ocr_data(
        {"text": ["only"], "conf": ["bad"]},
        variant=variant,
        source_size=(200, 200),
    )

    assert lines == []
    assert confidences == []
