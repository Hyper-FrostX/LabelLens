# Backend setup

From this directory, install the Python dependencies with:

```powershell
python -m pip install -r requirements.txt
```

For a fresh local setup, copy `.env.example` only when `.env` does not already
exist, then configure the database and JWT settings:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m alembic upgrade head
python -m uvicorn main:app --reload --port 8000
```

Keep local values in `.env`; do not overwrite an existing local environment
file. The checked-in example contains placeholders only.

## Gemini product Q&A

The backend loads `.env` relative to the backend project directory when its
environment-aware services initialize. Set the example's placeholders locally:

```powershell
Copy-Item .env.example .env
```

Set `AI_PROVIDER=gemini`, `AI_API_KEY` to your Gemini API key,
`AI_MODEL=gemini-3.5-flash-lite`, `AI_BASE_URL=` (blank selects Google's
official Gemini API endpoint), and `AI_REQUEST_TIMEOUT_SECONDS=12`. Explicit
process environment variables take precedence over `.env`. Restart the backend
after changing its environment. Do not put AI credentials in frontend
environment variables; `backend/.env` is ignored by Git.

The `.env.example` also lists the server-side settings for persistence,
authentication, OCR, browser origins, and API request limits. Replace every
placeholder locally; never commit `.env` or put credentials in the example
file. Set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL for persistence and
migrations (SQLite URLs are supported for isolated tests). Set
`JWT_SECRET_KEY` to a securely generated secret of at least 32 bytes.
`TESSERACT_CMD` is optional and points to the local Tesseract executable when
it is not on `PATH`.

Model availability can vary by API key and Google project. Unsupported models,
invalid credentials, quota/rate limits, malformed responses, and network
failures fall back to deterministic Q&A. `POST /analyze/product/ask` uses a
configured provider when available; `POST /analyze/product/question` remains
deterministic.

## API request limits and CORS

`POST /extract/label` and `POST /analyze/product/ask` have independent,
configurable per-client limits. The defaults are 10 label extractions per 60
seconds and 20 product questions per 60 seconds. Configure them with
`EXTRACT_LABEL_RATE_LIMIT_REQUESTS`,
`EXTRACT_LABEL_RATE_LIMIT_WINDOW_SECONDS`,
`PRODUCT_ASK_RATE_LIMIT_REQUESTS`, and
`PRODUCT_ASK_RATE_LIMIT_WINDOW_SECONDS`. A limit response uses HTTP 429 and a
`Retry-After` header. The limiter keys requests by the client address provided
to the ASGI application and operation; it does not log client addresses or
credentials.

These counters are process-local and held in memory. They are not shared across
multiple workers, replicas, or restarts, so they are not a distributed abuse
control. Use a shared gateway or distributed limiter for multi-worker or
production deployments requiring consistent enforcement. When running behind
a reverse proxy, configure trusted proxy handling at the server/infrastructure
layer; the application does not trust arbitrary forwarded-IP headers.

CORS defaults to the four local frontend origins in `.env.example`, with
credentials enabled. Set `CORS_ALLOWED_ORIGINS` to a comma-separated list of
exact origins for deployment and `CORS_ALLOW_CREDENTIALS` to `true` or
`false`. Wildcard origin `*` is rejected when credentials are enabled. Keep
the allowlist limited to origins you control.

The extractor continues to validate the decoded image format and dimensions
and limits uploaded files to 10 MiB. OCR uses the local Tesseract executable.
When Gemini Vision is enabled and configured, the image may also be sent to
Google's Gemini API for candidate extraction; keep that behavior and its
credentials server-side.

Use a key authorized for the Gemini API. Google's current key guidance rejects
unrestricted standard keys; apply a Gemini API restriction or use an
authorized key type.

The label extractor uses Pillow to validate and decode JPEG, PNG, and WebP
images, and `pytesseract` to call a **separately installed local Tesseract OCR
executable**. Installing the Python package does not install the Tesseract
program. On Windows, install the Tesseract OCR engine using a trusted Windows
distribution, ensure `tesseract.exe` is on `PATH`, open a new terminal, and
verify it with `tesseract --version`. Alternatively, set `TESSERACT_CMD` to
the executable's full path. The service also checks the standard Windows
installation location. An invalid configured path is reported as an actionable
OCR service error; it does not substitute sample or mocked text.

Image uploads are limited to 10 MiB and 25 megapixels. OCR is local; uploaded
images are not sent to an external OCR service. OCR word confidence is not
reported as nutrition correctness or overall extraction certainty. Extracted
fields are flagged for user review. Preprocessing applies EXIF orientation,
grayscale conversion, contrast normalization, light median-filter denoising,
and bounded resizing. Tesseract runs full-image, sparse-layout, and right-side
passes to accommodate differing label layouts.

`POST /extract/label` preserves the existing response fields, including
`product_name`, `basis`, `serving_size_text`, `nutrients`,
`ingredients_text`, `ingredients`, `review_required_fields`, and `ocr_text`.
The response also includes source-preserving field objects for product name,
basis, serving size, nutrients, ingredients, allergen and may-contain
declarations, and the FSSAI license number. Each field includes `value`,
`unit`, `source_text`, `confidence`, and `needs_review`; confidence remains
`null` because the parser does not use a calibrated OCR confidence score.
Missing or ambiguous values remain unresolved for manual review. Sodium and
salt, and total and added sugars, are extracted separately without conversion.

## Database persistence

The persistence layer uses SQLAlchemy 2.x, PostgreSQL, Psycopg 3, and Alembic.
Set the `DATABASE_URL` environment variable to a PostgreSQL SQLAlchemy URL
before running migrations or using the database session dependency. The
configuration also accepts SQLite URLs for isolated tests. Credentials belong
in the local environment, not source control; no connection URL or credential
is hardcoded.

From the `backend` directory, install dependencies and apply the schema:

```powershell
python -m pip install -r requirements.txt
$env:DATABASE_URL = "<your PostgreSQL SQLAlchemy URL>"
python -m alembic upgrade head
```

Use `python -m alembic downgrade -1` to reverse the latest migration, and
`python -m alembic revision --autogenerate -m "describe schema change"` to
create a migration after changing models. Review generated migrations before applying them. The migration history creates
the user/profile/health, product/ingredient/nutrient, scan/extracted-label,
and analysis-report tables.

SQLAlchemy models are in `app.models`, connection and session configuration in
`app.database`, Pydantic persistence schemas in `app.schemas`, and user/scan
queries in `app.repositories`. `get_db` provides a request-scoped session
dependency; repositories flush changes but leave transaction commit/rollback
to their caller. Authentication, profile operations, authenticated catalog
lookup, product alternatives, and saved scan history use the database when
configured. Label extraction itself remains stateless; reviewed product
analysis is saved only when requested by an authenticated user.

## Authentication and health profiles

Authentication uses Argon2 password hashes and signed HS256 JWT access tokens.
Set `JWT_SECRET_KEY` to a securely generated value of at least 32 bytes; there
is no default secret. `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` is optional and
defaults to `30`. Account registration and login, plus profile reads and
updates, use the existing persistence database. Keep both database and token
configuration in the local environment, not source control.

For a PowerShell development session, from the `backend` directory:

```powershell
$env:DATABASE_URL = "<your PostgreSQL SQLAlchemy URL>"
$env:JWT_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(48))"
$env:JWT_ACCESS_TOKEN_EXPIRE_MINUTES = "30"
python -m alembic upgrade head
python -m uvicorn main:app --reload
```

The secret-generation command sets a fresh development secret each time it is
run; use a stable secret-management mechanism for deployments so existing
tokens remain verifiable. No schema migration was needed for authentication:
registration creates the existing `HealthProfile` row, while profile updates
use the existing health-condition, allergen, and association models.

Authentication endpoints are `POST /auth/register`, `POST /auth/login`, and
`GET /auth/me`. `GET /profile` and `PUT /profile` require a Bearer access token
and only read or modify the authenticated user's profile. Supported health
conditions and standard allergens are validated against the API schema;
additional allergen names are stored as user-specific custom selections.
`POST /analyze/product` uses the authenticated user's supported profile rules
for suitability and alternatives; general nutrition scoring and ingredient
matching remain separate from personal suitability.

The browser keeps JWTs in memory rather than persistent browser storage. A
reload requires signing in again. Client logout clears local state, but an
already issued stateless JWT remains valid until its configured expiry.

## Personalized label analysis

`POST /analyze/personalized` requires a Bearer access token and accepts either
the flattened reviewed-label fields used by `POST /analyze/label`, or the
source-preserving JSON returned by `POST /extract/label`. It returns
`general_analysis` and `personal_suitability` separately. The former uses the
same nutrient assessment, health-score, and ingredient-analysis functions as
the anonymous `/analyze/label` endpoint. The general score is not combined
with profile matches.

Allergen matching uses explicit phrase boundaries against ingredient entries,
the existing exact-alias ingredient analysis, declared allergens, and
may-contain declarations. Ingredient and declared-allergen matches are
distinguished from precautionary may-contain warnings. Custom allergens use
literal phrase matching only; there is no fuzzy matching. A missing or
unreadable ingredient/declaration field is returned as missing information,
not as evidence of absence or safety.

Condition rules are implemented in `app/services/personalized_analysis.py`.
Diabetes checks total and added sugar separately; hypertension checks sodium;
heart disease checks sodium and saturated fat; kidney disease checks sodium.
The celiac rule looks for explicit gluten-related ingredient/declaration
matches, while the PKU rule looks for explicit aspartame or phenylalanine
text. There are deliberately no condition-specific findings for IBS or gout
until supported rules and evidence are available. Kidney-specific nutrients
not extracted by the current pipeline are identified as missing information.
Rules report label evidence and are not diagnosis, treatment, product safety
determinations, or medical advice.

For nutrient findings, the service reuses the configured comparisons in
`app/services/nutrition.py`: 50 g sugars, 2,000 mg sodium, and 22 g saturated
fat project daily references, with a warning signal beginning at the existing
15% lower-contribution boundary. The source values and contribution bands are
project configuration, not condition-specific or universal medical
thresholds. Update those centralized references/bands and the mappings in
`personalized_analysis.py` to change this behavior; the existing general
scoring formula remains unchanged.

Run the backend tests, including the isolated SQLite authentication/profile
coverage, with:

```powershell
python -m pytest -q
```

## Ingredient knowledge base

The normalized ingredient catalog is modeled in `app.models.catalog` and loaded
by `IngredientKnowledgeRepository`. It stores canonical ingredients, exact
aliases, INS/E-number identifiers, categories, multiple functions, allergen
associations, evidence records, and regulatory references. The detector in
`app.services.ingredient_analysis` performs exact normalized matching; unknown
text remains unknown rather than receiving inferred ingredient properties.

Ingredient, allergen-alias, and ingredient/allergen association records now
carry `VERIFIED`, `PROVISIONAL`, `UNVERIFIED`, or `REVIEW_REQUIRED` status.
Evidence and regulatory references also carry verification flags and review
dates. The detector only surfaces health evidence whose evidence record is
independently marked verified; unknown or unverified records are not presented
as evidence of safety or harm.

The audit in `docs/ingredient-knowledge-audit.md` records all current catalog
and legacy warning entries and the source review performed on 2026-11-15.
Only narrowly scoped peanut-allergy and aspartame assessment statements and
the U.S.-specific BVO regulatory fact were verified during that review.
FSSAI's regulation page returned only a JavaScript shell, the expected
additives compendium URL returned 404, Codex GSFA returned HTTP 403, and
EFSA/eCFR sources were blocked or redirected to access challenges. Accordingly,
no Indian/Codex usage limits or new Indian-market ingredient records were
asserted. Unsupported legacy warning text and recommendations are withdrawn
from API/UI output and marked `REVIEW_REQUIRED`; no exposure or product-risk
conclusion is inferred from an ingredient name.

Apply the current schema and re-run the idempotent seed from the `backend`
directory:

```powershell
python -m alembic upgrade head
python -m app.scripts.seed_ingredient_knowledge
```

After applying migrations, seed or re-run the curated catalog from the backend
directory with:

```powershell
python -m app.scripts.seed_ingredient_knowledge
```

The seed operation is idempotent and updates catalog-owned verification
metadata without replacing user data. `POST /analyze/ingredients` retains its
response keys but replaces the unsupported high/moderate/safe judgments with
verification state, a review-required count, and neutral summaries. When
`DATABASE_URL` is configured, `/analyze/ingredients`, `/analyze/label`, and
`/extract/label` use the persisted catalog; without it, they use the bundled
curated records. Authenticated personalized analysis loads the persisted
catalog and reuses the same matcher.

### Main endpoints
- `GET /health`
- `GET /additives/knowledge-base`
- `POST /analyze/ingredients`
- `POST /analyze/nutrition` and `POST /analyze/label`
- `POST /extract/label`
- `POST /analyze/product` and `POST /analyze/label-compliance`
- `POST /analyze/personalized`
- `POST /analyze/product/ask`
- `GET /scans`, `GET /scans/{scan_id}`

Saved-scan Product Comparison and its `/scans/compare` endpoint are not part of
the active application scope. Stored-product healthier alternatives remain
available as part of product analysis when suitable stored data exists.

## Label analysis

`POST /analyze/label` accepts reviewed nutrient values, their units, the
measurement basis, serving-size text, and the ingredient-list text. The
response contains `health_score`, `excess_nutrients` assessments, and
`ingredient_analysis`.
The existing `POST /analyze/nutrition` endpoint remains available with its
original response shape.

Nutrient contribution bands are configurable in
`app/services/nutrition.py`. The prototype references are 50 g for sugars,
2,000 mg for sodium, and 22 g for saturated fat; values below 15% of a
reference are shown as `Lower contribution`, 15% through 30% as `Moderate`,
and above 30% as `High`. These are Label Lens project references, not
official medical, regulatory, or universal healthy-food thresholds. Total
sugar and added sugar are assessed separately against the sugar reference.
Sodium is not inferred from salt. Assessments retain the label's reported
value and basis. A per-serving metric mass/volume may also include a
calculated equivalent per 100 g or per 100 ml; this is only shown for known,
convertible metric serving sizes and is never substituted for the label
value or used to change its status. Per-serving assessments need an
unambiguous serving size, while missing values, units, or basis are marked
`Unable to assess` rather than treated as zero.

### Experimental Label Lens Health Score

The score is calculated in Python from the same validated label values and
one shared basis. It is available only when at least two of these three
categories can be assessed: sugars, sodium, and saturated fat. Total sugar
is used for the sugars category when it has a valid value and unit; added
sugar is the fallback when total sugar is unavailable or invalid. They are
never both penalized. Sodium and saturated fat are assessed independently.
Per-serving inputs require a positive, unambiguous serving size. Per-100-g
and per-100-ml amounts are used as reported; the score does not combine or
convert bases.

The configurable category weights are 35 points for sugars, 35 for sodium,
and 30 for saturated fat (100 total). For each assessed category, the
penalty is `min(weight, weight * reported_amount / project_daily_reference)`,
using the existing references of 50 g sugars, 2,000 mg sodium, and 22 g
saturated fat. The score is `max(0, round(100 - sum(category_penalties)))`.
Each category penalty is capped at its weight. Missing or invalid categories
are omitted, not treated as zero intake or favorable data; the response
reports the count assessed and returns `Score unavailable` if fewer than
two categories are valid. Explanations include the values, references and
penalties that contributed. Ingredient/additive matches have no effect on
the score.

This deterministic weighted prototype is not a validated measure of
overall health, an official health grade, or a medical assessment. Its
daily-reference comparisons do not account for an individual's needs,
product consumption amount, or other aspects of diet.

The small curated ingredient knowledge base is maintained in
`app/services/ingredient_analysis.py`. It uses exact normalized names and
listed aliases only, expands comma/semicolon-separated nested ingredient
groups, and sends unknown text for review rather than fuzzy matching. The
curated entries include the snack ingredients and INS identifiers covered by
the tests; E-number aliases are used only where explicitly listed. Existing
verified references link to U.S. FDA or Electronic Code of Federal
Regulations sources. New entries without a verified source URL do not claim
an evidence citation; their function descriptions are informational, and
their concern category says no specific concern was identified in this
knowledge base, not that the ingredient is proven safe. Ingredient function
is shown separately from any concern. A cited regulation documents
regulatory food-use status, not scientific proof of harm or universal safety;
allergen references describe hazards in the relevant allergic population.
The knowledge base does not determine ingredient quantity, total exposure,
individual risk, or whether a product is safe. The OCR parser accepts an
explicit `Per Serve`/`Per serving` statement as serving basis, but does not
infer basis from serving size alone; the user must confirm extracted fields.
