from io import BytesIO
import os
from pathlib import Path
import shutil

from PIL import Image, ImageOps, UnidentifiedImageError
import pytesseract
from pytesseract import TesseractError, TesseractNotFoundError


ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_PIXELS = 25_000_000
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
    """Configure pytesseract using explicit config, PATH, or Windows default."""
    configured_path = os.environ.get("TESSERACT_CMD")
    if configured_path:
        pytesseract.pytesseract.tesseract_cmd = configured_path
        return configured_path

    discovered_path = shutil.which("tesseract")
    if discovered_path:
        pytesseract.pytesseract.tesseract_cmd = discovered_path
        return discovered_path

    if os.name == "nt" and STANDARD_WINDOWS_TESSERACT_PATH.is_file():
        discovered_path = str(STANDARD_WINDOWS_TESSERACT_PATH)
        pytesseract.pytesseract.tesseract_cmd = discovered_path
        return discovered_path

    return None


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
    """OCR an enlarged, contrast-enhanced right half as a supplemental pass."""
    width, height = image.size
    right_region = image.crop((width // 2, 0, width, height))
    green_channel = right_region.getchannel("G")
    enhanced = ImageOps.autocontrast(green_channel)
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


def extract_text(image_bytes: bytes) -> str:
    """Run local Tesseract OCR; no image data is sent to an external service."""
    try:
        if configure_tesseract() is None:
            raise OCRServiceError(
                "Local Tesseract OCR is unavailable. Set TESSERACT_CMD, "
                "install Tesseract on PATH, or install it at the standard "
                "Windows location."
            )

        with Image.open(BytesIO(image_bytes)) as image:
            normalized_image = ImageOps.exif_transpose(image).convert("RGB")
            full_image_text = pytesseract.image_to_string(
                normalized_image,
                config="--psm 6",
            )
            right_region_text = _extract_right_region_text(normalized_image)
            return _merge_ocr_text(full_image_text, right_region_text)
    except OCRServiceError:
        raise
    except TesseractNotFoundError as error:
        raise OCRServiceError(
            "The configured local Tesseract OCR executable could not be found."
        ) from error
    except TesseractError as error:
        raise OCRServiceError("Local Tesseract OCR could not process this image.") from error
