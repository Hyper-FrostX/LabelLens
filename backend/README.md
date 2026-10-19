# Backend setup

From this directory, install the Python dependencies with:

```powershell
python -m pip install -r requirements.txt
```

The label extractor uses Pillow to validate and decode JPEG, PNG, and WebP
images, and `pytesseract` to call a **separately installed local Tesseract OCR
executable**. Installing the Python package does not install the Tesseract
program. On Windows, install the Tesseract OCR engine using a trusted Windows
distribution, ensure `tesseract.exe` is on `PATH`, open a new terminal, and
verify it with `tesseract --version`.

Image uploads are limited to 10 MiB and 25 megapixels. OCR is local; uploaded
images are not sent to an external OCR service. OCR word confidence is not
reported as nutrition correctness or overall extraction certainty. Extracted
fields are flagged for user review.
