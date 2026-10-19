from io import BytesIO

from PIL import Image
import pytest

from app.services import label_ocr


def test_configure_tesseract_prefers_environment_variable(monkeypatch):
    configured_path = r"C:\Custom\Tesseract\tesseract.exe"
    monkeypatch.setenv("TESSERACT_CMD", configured_path)
    monkeypatch.setattr(
        label_ocr.shutil,
        "which",
        lambda _: r"C:\FromPath\tesseract.exe",
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
    monkeypatch.setattr(label_ocr.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        label_ocr,
        "STANDARD_WINDOWS_TESSERACT_PATH",
        standard_executable,
    )

    result = label_ocr.configure_tesseract()

    assert result == str(standard_executable)
    assert label_ocr.pytesseract.pytesseract.tesseract_cmd == result


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


def test_extract_text_ocr_passes_full_image_and_enhanced_right_region(monkeypatch):
    image_bytes = BytesIO()
    Image.new("RGB", (1000, 1000), color=(255, 225, 0)).save(
        image_bytes,
        format="PNG",
    )
    observed_images = []

    monkeypatch.setattr(label_ocr, "configure_tesseract", lambda: "tesseract")

    def fake_image_to_string(image, config):
        observed_images.append((image.copy(), config))
        if len(observed_images) == 1:
            return "Ingredients: oats\nServing Size: 25 g\n"
        return (
            "Serving Size: 25 g\n"
            "Saturated Fat 0.8 g 4%\n"
            "Sodium 249 mg 11%\n"
            "Total Sugars 3.4 g 3%\n"
            "Added Sugars 1.5 g 2%\n"
        )

    monkeypatch.setattr(
        label_ocr.pytesseract,
        "image_to_string",
        fake_image_to_string,
    )

    result = label_ocr.extract_text(image_bytes.getvalue())

    assert len(observed_images) == 2
    assert observed_images[0][0].size == (1000, 1000)
    assert observed_images[0][0].mode == "RGB"
    assert observed_images[0][1] == "--psm 6"
    assert observed_images[1][0].size == (1000, 2000)
    assert observed_images[1][0].mode == "L"
    assert observed_images[1][1] == "--psm 6"
    assert result.count("Serving Size: 25 g") == 1
    assert "Saturated Fat 0.8 g 4%" in result
    assert "Sodium 249 mg 11%" in result
    assert "Total Sugars 3.4 g 3%" in result


def test_merge_ocr_text_deduplicates_normalized_lines():
    result = label_ocr._merge_ocr_text(
        "Ingredients: oats\nSodium 249 mg",
        "ingredients: oats\nSodium 249 mg\nSugar 3.4 g",
    )

    assert result == (
        "Ingredients: oats\nSodium 249 mg\nSugar 3.4 g"
    )
