# Phase 9.1 — Product Assistant, Recommendations, and Provenance

## Overview

Phase 9.1 extends the existing Phase 9 product analysis without replacing the
Phase 7 compliance engine, Phase 8 OCR evidence workflow, or deterministic
nutrition analysis. The changes add an optional provider-backed Q&A route,
more explainable recommendation and comparison details, and provenance-aware
catalog import primitives.

## Product Q&A

`POST /analyze/product/ask` accepts the existing question, report context, and
explanation-level fields. It uses a configured Gemini or OpenAI-compatible
chat provider when available and otherwise returns the deterministic answer.
`POST /analyze/product/question` remains deterministic for compatibility.

Provider configuration is read from the server environment:

```text
AI_PROVIDER=none
AI_API_KEY=
AI_MODEL=
AI_BASE_URL=
AI_REQUEST_TIMEOUT_SECONDS=12
```

Set `AI_PROVIDER` to `gemini` or `openai` and provide the corresponding
server-side key to enable a provider. `AI_BASE_URL` is optional and defaults
to the provider's standard API base URL; only set it to a trusted compatible
endpoint. The request timeout is bounded to 1–30 seconds. Credentials are not
stored in source code or returned in API responses.

Before calling a provider, the service builds an allowlisted, size-bounded
context from product identity, nutrition values and normalized indicators,
ingredient/additive matches, allergen observations, profile assessment,
alternatives, compliance observations, OCR confidence, original label text,
and explicitly confirmed corrections. It does not forward arbitrary client
context. Context is capped at 20,000 serialized characters, and the request
schema caps incoming context at 50,000 characters.

The prompt treats label/report values as untrusted data and requires the
assistant to distinguish missing information, label evidence, and verification.
It prohibits invented facts, medical conclusions, safety assurances, and
claims that a format check constitutes official FSSAI verification. Provider
output must be valid JSON with an answer, evidence paths, and missing
information. Evidence paths are resolved only against the supplied context;
invalid paths are omitted. An answer is not semantically verified, so it
remains explicitly labeled AI-generated and not independently verified.

Provider timeouts, rate limits, HTTP/network failures, invalid responses, and
missing configuration return the deterministic answer with a non-sensitive
`provider_status`. Successful responses include `response_mode`,
`provider_status`, provider/model labels, evidence, and missing-information
disclosures. Successful answers are cached in process memory for 60 seconds
with a 128-entry maximum; keys include the question, context, explanation
level, provider/model, and optional authenticated user ID. This is a
short-lived per-process optimization, not persistent history.

The frontend includes a loading/error state, explains the configured-provider
fallback, labels generated answers separately from deterministic answers, and
discloses that the question and report context (including profile assessment)
may be sent to the configured provider. Users should not include personal
information in questions.

## Recommendations and saved comparisons

The existing product-analysis request accepts `recommendation_goal`. Goal
comparison uses normalized catalog rows and the authenticated user's own
saved analysis reports. It requires compatible bases/units and at least two
shared nutrient values; it does not compare unlike mass/volume data or guess
unknown servings.

Recommendation items expose goal-relative improvements and trade-offs,
missing comparison data, profile conflict/review signals, ingredient-list
transparency, and catalog source provenance when present. Ranking is
lexicographic and uses reported data rather than a universal product-quality
score. Balanced comparisons prioritize distinct improvements after review
signals; goal-specific comparisons prioritize improvement for that goal.
Neither recommendations nor `POST /scans/compare` declare a product safe or
select an overall winner. Saved comparisons remain user-scoped and can accept
the selected recommendation goal.

## Catalog provenance and import

The `products` record now stores optional serving-size text, ingredient text,
declared and precautionary allergens, and provider/source metadata:

- Source name and source product ID.
- Source URL and license identifier.
- Source update timestamp.

These nullable columns preserve existing catalog rows. The migration
`e74b02c91f8a` follows `c91f024d7a63` and is reversible. Source name/product
ID is unique when provided.

`ProductImportInput` and `import_product_record` provide an internal validated
import/upsert primitive. Inputs require source identity, source URL, and
license; normalize supported nutrient aliases and units; reject non-finite or
negative amounts, duplicate nutrient/basis pairs, and malformed GTIN
check-digits. An existing source identity updates the same record; a barcode
identity collision or an ambiguous same-name/brand/category match raises a
review conflict rather than silently merging records. Updated nutrient rows
are replaced through the caller's SQLAlchemy session.

This phase does not add a public import endpoint, external catalog provider,
scraper, or scheduled synchronization. The service does not independently
audit provider licenses or the truth of imported label data. Provenance is
exposed by the existing product read schema and accompanies catalog
recommendations when present.

## API changes

| API | Phase 9.1 behavior |
| --- | --- |
| `POST /analyze/product/ask` | Optional configured provider, deterministic fallback, explicit mode/status, evidence paths, optional user-scoped cache. |
| `POST /analyze/product/question` | Existing deterministic Q&A remains available. |
| `POST /analyze/product` | Existing request accepts a recommendation goal and returns explainable alternatives using stored data. |
| `POST /scans/compare` | Accepts a recommendation goal and returns user-scoped normalized comparisons without an overall winner. |
| Product read schema | Adds nullable provenance and imported label fields; no public import route is added. |

## Tests and validation

Validation completed:

- Backend: **337 passed**, including provider configuration, structured context
  allowlisting/bounds, citations, fallback and error cases, cache isolation,
  provenance import validation/upsert/collisions, catalog recommendation
  integration, existing Phase 7/8/9 behavior, and Alembic upgrade/metadata/
  downgrade validation.
- Frontend: **15 passed**.
- Frontend lint: passed.
- Frontend production build: passed.

The backend test run reports one pre-existing Starlette/httpx test-client
deprecation warning.

## Known limitations

- Provider output can still be wrong or misleading despite bounded context,
  prompt constraints, and path validation. It is not authoritative, medical
  advice, or a safety/regulatory determination.
- Provider calls transmit the question and allowlisted report data to the
  configured external provider. Administrators must select a provider and
  endpoint consistent with their privacy requirements.
- The in-memory answer cache is process-local and may retain responses until
  expiry or process restart; there is no persistent chat history.
- Recommendation coverage is limited to products already present in the
  catalog and the current user's own saved reports. No automatic external
  discovery or ingestion is implemented.
- Import collisions are surfaced for review, but no user-facing collision
  resolution UI or import API is included. Source license claims and imported
  values are retained as supplied, not independently verified.
- Frontend coverage uses Node unit/contract tests; no browser component-test
  harness is currently configured.
