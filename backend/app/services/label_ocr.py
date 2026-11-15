from io import BytesIO
import os
from pathlib import Path
import shutil

from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
import pytesseract
from pytesseract import TesseractError, TesseractNotFoundError


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


def extract_text(image_bytes: bytes) -> str:
    """Run local Tesseract OCR; no image data is sent to an external service."""
    try:
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
            normalized_image = ImageOps.exif_transpose(image).convert("RGB")
            preprocessed_image = _preprocess_image(normalized_image)
            full_image_text = pytesseract.image_to_string(
                normalized_image,
                config="--psm 6",
            )
            layout_text = pytesseract.image_to_string(
                preprocessed_image,
                config="--psm 11",
            )
            right_region_text = _extract_right_region_text(preprocessed_image)
            return _merge_ocr_text(
                full_image_text,
                layout_text,
                right_region_text,
            )
    except OCRServiceError:
        raise
    except TesseractNotFoundError as error:
        raise OCRServiceError(
            "The configured Tesseract executable could not be launched. "
            "Check that TESSERACT_CMD points to an accessible executable."
        ) from error
    except TesseractError as error:
        raise OCRServiceError("Local Tesseract OCR could not process this image.") from error
