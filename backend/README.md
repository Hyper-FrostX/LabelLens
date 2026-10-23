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

## Additive and Ingredient Detection

The additive detector (`app.services.additive_detector`) evaluates ingredients
against a curated scientific knowledge base:
- Categorizes evidence-based concern levels into `high`, `moderate`, and `low` (safe/functional).
- Provides functional purposes, scientific evidence citations, and regulatory status (EFSA, US FDA, WHO/JECFA).
- Avoids calling all additives harmful, recognizing essential roles like mold inhibition and botulism prevention.

### Endpoints
- `GET /health`
- `GET /additives/knowledge-base` (supports `concern_level` and `query` params)
- `POST /analyze/ingredients` (accepts `ingredients` list or `ingredients_text`)
- `POST /analyze/nutrition`
- `POST /extract/label` (includes `additive_analysis` on parsed ingredients)
