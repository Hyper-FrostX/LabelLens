# Phase 10.1 — Gemini Integration and Configuration

## Architecture

`POST /analyze/product/ask` continues to use the existing product assistant
service and its bounded, allowlisted product context. When `AI_PROVIDER=gemini`
and a backend API key are configured, it sends a Gemini `generateContent`
request. `POST /analyze/product/question` remains deterministic. Existing
OpenAI-compatible provider support is retained.

Gemini requests use the official default base URL,
`https://generativelanguage.googleapis.com/v1beta`, and the selected model's
`/models/{model}:generateContent` endpoint. Authentication is sent in the
`x-goog-api-key` header, not in the URL or frontend. The request keeps JSON
response mode, system instructions, temperature, output limit, and the
configured bounded timeout.

Provider responses are checked for a usable candidate, non-empty text,
well-formed JSON, valid answer shape, and evidence paths that exist in the
submitted context. Invalid, empty, blocked, or malformed responses fall back
to the existing deterministic Q&A. Provider error bodies, credentials, and
URLs are not included in fallback responses.

## Configuration

The backend now loads `backend/.env` at service import with `python-dotenv`;
the path is anchored to the backend project directory and does not depend on
the current working directory. UTF-8 BOM files are supported, and existing
process environment variables take precedence. Copy the example from the
`backend` directory and replace the placeholder locally:

```powershell
Copy-Item .env.example .env
```

Set the following values:

```text
AI_PROVIDER=gemini
AI_API_KEY=YOUR_NEW_GEMINI_API_KEY
AI_MODEL=gemini-3.5-flash-lite
AI_BASE_URL=
AI_REQUEST_TIMEOUT_SECONDS=12
```

The empty base URL selects Google's official endpoint. The timeout must be
between 1 and 30 seconds. Explicitly configured remote endpoints must use
HTTPS; HTTP is accepted only for loopback development endpoints. `AI_API_KEY`
is read only by the backend and is never placed in frontend configuration.
The existing root `.gitignore` already excludes `.env` and `.env.*` while
allowing `.env.example`.

The current official Gemini model documentation identifies
`gemini-3.5-flash-lite` as a stable model with text output and structured-output
support. The Gemini API's documented `generateContent` method supports the
request endpoint used here:

- [Gemini 3.5 Flash-Lite model details](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)
- [Gemini model listing API](https://ai.google.dev/api/models)
- [Gemini generateContent API](https://ai.google.dev/api/generate-content)
- [Gemini API key security guidance](https://ai.google.dev/gemini-api/docs/api-key)

Availability can vary by API key and Google project; an unsupported or
inaccessible model is reported as a non-sensitive provider status and falls
back deterministically.

## API and fallback behavior

`POST /analyze/product/ask` keeps the existing request schema. On successful
Gemini responses, it returns `response_mode=AI_GENERATED` and
`provider_status=AVAILABLE`, with provider/model labels, grounded evidence,
and missing-information disclosures. The frontend labels these answers
“AI-generated” and states that they are not independently verified.

Disabled/unconfigured provider, invalid configuration, authentication failure,
unsupported model, quota/rate limit, timeout, network/unavailable service,
empty answer, and malformed response paths return the existing deterministic
answer with `response_mode=DETERMINISTIC_FALLBACK` and a non-sensitive
`provider_status`. The frontend labels fallback responses as deterministic,
not AI-generated. Loading transitions, legacy-route fallback, HTTP errors,
malformed responses, and network errors are covered by frontend tests.

## Security

- The API key is read from backend process environment or `backend/.env`.
- Gemini authentication uses a request header; the key is not added to URLs.
- No key is hardcoded, logged, returned, or placed in frontend environment
  variables.
- `.env` files remain excluded by the existing root ignore rules.
- Use a Gemini API-authorized key; Google's current guidance rejects
  unrestricted standard keys.
- Mocked tests use fake credentials and fake Gemini responses; no automated
  test contacts Gemini or consumes API credits.
- The provider receives only the bounded, allowlisted product/report context.
  Prompts treat that context as untrusted data and prohibit invented label,
  nutrition, allergen, or regulatory facts.

## Files changed

- `backend/.env.example`
- `backend/README.md`
- `backend/requirements.txt`
- `backend/app/services/product_assistant.py`
- `backend/tests/test_product_assistant.py`
- `frontend/src/features/nutrition/ProductQuestionAnswer.jsx`
- `frontend/src/features/nutrition/productQuestionApi.js`
- `frontend/tests/product-question-api.test.js`
- `backend/docs/phase-10.1-gemini-integration-report.md`

No schema or Alembic migration changes were required.

## Tests and validation

- Backend: **348 passed**, including mocked success, invalid-key/auth failure,
  timeout, rate limit/quota status, network and unavailable-service errors,
  malformed and empty Gemini responses, configuration loading/defaults,
  disabled-provider fallback, API integration, and migration coverage.
- Frontend: **20 passed**, including loading transitions, AI-vs-fallback
  labels, legacy route fallback, HTTP/malformed-response errors, and network
  errors.
- Frontend Oxlint: passed.
- Frontend production build: passed.
- Alembic upgrade/metadata/downgrade validation: **1 passed**.
- Ruff on changed backend implementation and provider tests: passed.
- Repository-wide Ruff check: not clean; it reports 11 unrelated existing
  findings in catalog/scan/user model annotations, test import ordering, and
  unused imports. Those unrelated files were not changed.
- Backend startup with Gemini environment values: passed; `/health` returned
  healthy and configuration resolved to Gemini, `gemini-3.5-flash-lite`, the
  official base URL, and a 12-second timeout. The startup check used a
  placeholder key and did not call Gemini.

One existing Starlette/httpx test-client deprecation warning remains.

## Configuration status fix

The provider configuration tuple now ends with an explicit `configured`
boolean. Its preceding value remains the non-sensitive configuration status
(`None` for a valid provider configuration or a status code for an invalid or
missing configuration). This avoids treating a valid `None` status as
`False` when checking `bool(config[-1])`. The product assistant now uses this
boolean to choose between provider requests and the existing deterministic
fallback.

Regression coverage includes backend-relative dotenv loading from a different
working directory, UTF-8 BOM parsing, process-environment precedence, empty
and missing configuration, valid Gemini configuration, and deterministic
fallback. The required safe probe returned:

```text
Provider: gemini
Model: gemini-3.5-flash-lite
Configured: True
```

Latest validation after this fix: backend **348 passed** (one existing
Starlette/httpx deprecation warning), frontend **20 passed**, frontend lint
passed, frontend production build passed, and Ruff passed for the changed
backend files. No live Gemini API request was made; successful authentication
and product Q&A remain unverified.

## Live API verification

No live Gemini request was made. At implementation time, `backend/.env` was
absent and no `AI_API_KEY` was present in the process environment. The model
was checked against Google's current published model documentation, but
account-specific model listing, credentials, quota, and live inference remain
pending until a valid key is entered locally in `backend/.env`.

During the 21:56 follow-up verification on 2026-11-16, `backend/.env` was
absent and the loaded provider configuration resolved to `AI_PROVIDER=none`.
At 22:03, the file was present; the backend loaded Gemini as the provider,
resolved `gemini-3.5-flash-lite`, the official endpoint, and the 12-second
timeout, and confirmed only that an API key was present without displaying
its value. The backend health endpoint returned healthy.

No Gemini HTTP request was made: this assistant cannot transmit credentials
to Google. Consequently, Gemini authentication, a real model response, and a
live product-grounded Q&A remain unverified. A mocked provider-failure test
run at 22:03 passed: 30 product-assistant/API tests passed, including
deterministic fallback and credential-redaction cases. No credential from the
conversation was written to disk or sent to Google.

## Remaining limitations

- Live connectivity and access to the selected model are not verified until a
  valid local API key is available.
- The selected model is configurable, but access is specific to the Google
  project and key; API-side errors trigger deterministic fallback.
- Provider-generated text can still be incorrect despite bounded context,
  prompt constraints, and evidence-path validation; it is not an authoritative
  compliance or safety decision.
