# LabelLens

LabelLens is a food-label analysis prototype for reviewing packaged-food
ingredients, nutrients, declarations, and label-based suitability signals.
Extracted values require user review. Scores and recommendations are
project-defined informational outputs, not medical advice, official nutrition
grades, or legally certified FSSAI compliance.

## Active modules

1. Food-label scanning with local OCR and optional Gemini Vision candidates
2. Ingredient intelligence, additive references, and allergen declarations
3. Excess-nutrient and nutrition-panel analysis
4. Personalized health profiles and supported suitability rules
5. Transparent, project-defined nutrition scoring
6. Stored-product healthier alternatives when usable data is available
7. Evidence-backed, review-required Indian label declaration checks
8. Food and label explanations with deterministic fallbacks
9. User profiles and private, paginated scan history
10. Ask About This Label, with AI output distinguished from fallback analysis

There is no standalone Product Comparison module or saved-scan comparison
endpoint. Stored-product alternatives remain part of label analysis. Real-food
recognition and nutritional estimation are out of scope for this release.

## Requirements

- Python 3.10 or later
- Node.js supported by the installed Vite release and npm
- Tesseract OCR executable for local image-to-text extraction
- PostgreSQL for persistent accounts, profiles, and saved scans
- Optional Gemini API access for Gemini Vision and AI-generated Q&A

## Configure and run

### Backend

From the repository root in PowerShell:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `backend/.env` locally. Set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL
and `JWT_SECRET_KEY` to a securely generated secret of at least 32 bytes.
Gemini is optional; without a usable provider configuration, deterministic
analysis remains available. Do not copy credentials into frontend variables or
commit `.env`.

Install the Tesseract OCR program separately and ensure `tesseract.exe` is on
`PATH`, or set `TESSERACT_CMD` to its full path. The Python package alone does
not install the OCR executable.

Apply migrations and start the API:

```powershell
python -m alembic upgrade head
python -m uvicorn main:app --reload --port 8000
```

The backend setup, migration, CORS, provider, OCR, and rate-limit details are
documented in [backend/README.md](./backend/README.md). CORS origins are
configured through `CORS_ALLOWED_ORIGINS`; use exact origins you control.

### Frontend

In a second terminal:

```powershell
Set-Location frontend
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm ci
npm run dev
```

Set `VITE_API_BASE_URL` in `frontend/.env` if the API is not at
`http://127.0.0.1:8000`. Only public, non-secret frontend settings belong in
Vite variables.

## Image handling and privacy

Images are validated and processed with local OCR. When Gemini Vision is
enabled on the backend, the image may also be sent to Google's Gemini API to
produce candidate text. The UI discloses this conditional processing; review
extracted content before analysis. Do not upload labels containing personal
information.

The expensive image-extraction and product-Q&A endpoints have configurable
per-client limits. The built-in limiter is process-local, not shared between
workers or replicas. Production deployments with multiple workers should also
use a shared gateway or distributed rate limiter.

## Tests and checks

Run backend checks from `backend`:

```powershell
python -m pytest -q
python -m ruff check .
python -m alembic heads
```

Run frontend checks from `frontend`:

```powershell
npm test
npm run lint
npm run build
```

## Security note

The current environment templates contain placeholders only, and local `.env`
files must remain untracked. A prior historical environment template contained
a credential-shaped value. If it was a real credential, revoke and replace it;
removing a value from the current source tree does not invalidate historical
copies. Remote history has not been rewritten.
