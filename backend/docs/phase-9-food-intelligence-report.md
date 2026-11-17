# Phase 9 — Food Intelligence

## Overview

Phase 9 extends the existing product-analysis route and keeps the Phase 7
compliance report, Phase 8 OCR evidence, and existing nutrition analysis in
place. `POST /analyze/product` still returns the prior report sections and adds
a `food_intelligence` object containing normalized nutrition information,
versioned indicators, and an explicit profile assessment.

The connected flow is:

1. The existing label review flow supplies final values and, for image scans,
   the original OCR and correction metadata.
2. The existing `analyze_label`, ingredient, additive, allergen, and Phase 7
   compliance services run as before.
3. `nutrition_intelligence.py` normalizes supported units and bases without
   mixing mass and volume.
4. `food_scoring.py` creates the versioned project indicators and discloses
   formulas, inputs, and missing values.
5. `personalized_suitability.py` compares the available label evidence with
   the authenticated user's saved profile. The existing personalized-analysis
   response remains available unchanged.
6. Alternatives use stored catalog products and the authenticated user's own
   saved analyses. Saved comparisons are also available through a user-scoped
   endpoint.

## Nutrition normalization and observations

The normalized data is labeled `label-lens-nutrition-intelligence-v1`.
Recognized nutrient units include grams, milligrams, kilocalories, and
kilojoules. Per-serving values are converted to per-100 g or per-100 ml only
when the serving size contains a supported metric mass or volume. Kilojoules
are converted to kilocalories using 4.184 kJ per kcal. Unsupported units,
unknown bases, and missing serving quantities are not guessed.

The response includes reported basis, normalized per-100 nutrient density,
available per-serving amounts, derived protein/calorie and sugar-energy
ratios, missing or unusable values, and observations. It preserves the
existing project-reference assessments; it does not introduce new
regulatory/reference thresholds for nutrition observations. Inconsistent
reported totals (for example, added sugar greater than total sugar) are
surfaced for review.

The protein-per-100-kcal ratio is protein grams per 100 units divided by
energy kilocalories per 100 units, times 100. The sugar-energy percentage uses
an approximate 4 kcal/g conversion factor and is labeled as a derived ratio,
not a measured label field.

## Versioned indicators

All four indicators use `label-lens-food-scores-v1`. A missing required input
returns a null score and an `insufficient_data` status.

### Nutrition quality

Requires total sugar, sodium, and saturated fat on the same per-100 g or
per-100 ml basis:

```text
100
- 40 * min(sugars_g / 20, 1)
- 30 * min(sodium_mg / 1000, 1)
- 30 * min(saturated_fat_g / 10, 1)
```

These are Label Lens project weights/caps, not FSSAI rules, a clinical target,
or an official nutrition grade. Added sugar is reported but is not double
counted in this formula.

### Protein quality index

Requires protein and energy on a compatible per-100 basis. It is calculated
as:

```text
min(protein_g_per_100_kcal / 5, 1) * 100
```

This is a protein-density index only. It does not measure amino-acid profile,
protein digestibility, or overall protein quality.

### Ingredient transparency

Measures only whether these submitted label fields are available: ingredient
list (60 points), declared allergens (20), and precautionary may-contain
declaration (20). The score does not grade safety, accuracy, legality, or
ingredient catalog coverage. Missing declarations are not treated as
violations.

### Personalized suitability

The score is named `profile_alignment_score` in the detailed assessment. It
counts only evaluated `matches` and `potential_conflict` factors; unknown
factors are not scored. A null score is returned when nothing can be
evaluated. This is not a safety, medical, or clinical suitability score.

The separate assessment status can be `SUITABLE_BASED_ON_AVAILABLE_DATA`,
`UNSUITABLE_BASED_ON_USER_PREFERENCES`,
`POTENTIAL_CONFLICT`, `NEEDS_REVIEW`, or
`INSUFFICIENT_INFORMATION`. A possible label/allergen or ingredient match is
not a medical conclusion, and an absent match never establishes absence or
safety. Existing medical-condition rules remain limited to the currently
implemented rules.

## Profile preferences and goals

`GET /profile` and `PUT /profile` now include:

- Supported dietary label preferences: Vegetarian, Vegan, Gluten-free, and
  Dairy-free.
- Ingredient exclusions.
- Informational goals: higher protein/fiber, lower sugar/sodium/saturated fat,
  or lower calories.
- Optional daily calorie and protein targets.
- The existing beginner/expert explanation preference.

Profile goal comparisons use the v1 project thresholds: lower sugar is at most
5 g per 100 g/ml; lower sodium at most 120 mg per 100 g/ml; lower saturated
fat at most 1.5 g per 100 g/ml; higher protein at least 5 g per serving; higher
fiber at least 3 g per serving; and lower calories at most 200 kcal per
serving. They are project heuristics, not medical or regulatory targets.
Daily calorie/protein values are shown only as descriptive per-serving
contributions; they do not determine whether a product fits a daily goal.

These fields are stored on `health_profiles` using the migration
`c91f024d7a63`. The migration is reversible.

## Alternatives and saved comparisons

The product-analysis request accepts an optional `recommendation_goal`. Goal
comparisons rank only stored catalog products and the authenticated user's own
saved reports with compatible bases, units, and at least two shared nutrient
values. The response exposes improvements, trade-offs, missing data, source
provenance, and ingredient-transparency information where available. When the
request leaves the goal at `balanced`, the first supported saved nutrition
goal may be used. Candidate dietary/allergen conflicts and review needs are
surfaced; no product is called safe or best.

`POST /scans/compare` accepts 2–5 saved scan IDs and requires authentication.
It returns only scans owned by the caller. Shared nutrients are compared only
after normalization to the same per-100 g or per-100 ml basis. The response
does not choose an overall winner. Missing reports return a validation error;
foreign or nonexistent IDs return the same not-found response.

Example request:

```json
{ "scan_ids": [12, 19] }
```

## Product Q&A and explanation levels

`POST /analyze/product/ask` uses an optional server-configured Gemini or
OpenAI-compatible provider, with the deterministic product answer as a
fallback. `POST /analyze/product/question` remains deterministic. Provider
answers return `response_mode`, `provider_status`, validated evidence paths,
and missing-information disclosures. The frontend distinguishes generated
explanations from deterministic answers and discloses that the configured
provider may receive the question and report context.

The provider receives a bounded allowlist of product, nutrition, ingredient,
allergen, compliance, OCR-confidence, correction, and profile-assessment
fields; it does not receive arbitrary client context. Responses are limited to
evidence paths in that context. Provider errors, timeouts, rate limits, invalid
output, or missing configuration use the deterministic answer and expose a
status without returning provider error details or credentials. Successful
answers are cached in process memory for 60 seconds with a 128-entry limit;
authenticated user IDs are included in cache keys. Beginner/expert mode
changes explanation detail, not the underlying analysis.

The provider is optional and disabled by default. Configuration and remaining
limitations are documented in the Phase 9.1 report.

## Frontend integration

The existing scan workflow and design system are reused. Users can choose an
alternative comparison goal, save profile preferences and goals, inspect
nutrition densities and score formulas, see profile factor statuses, and
select saved scans for a normalized comparison. The Q&A shows its fallback
status and an expandable evidence payload. The Beginner/Expert toggle changes
display detail without rescanning.

## Validation

Validation completed after the Phase 9.1 extension:

- Backend: 337 tests passed (including the Alembic upgrade, metadata check,
  and downgrade test).
- Frontend: 15 tests passed.
- Frontend lint: passed.
- Frontend production build: passed.

The backend suite emits one existing Starlette/httpx deprecation warning from
the installed test-client integration.

## Known limitations

- The project score and profile-goal thresholds are intentionally heuristic
  and not regulatory, clinical, or dietitian-authored recommendations.
- OCR and user-provided label text may be incomplete or wrong. Confirmed
  corrections flow into analysis, while the original OCR evidence remains
  preserved by the existing Phase 8 flow.
- Vegetarian/vegan/free-from checks report declaration matches only. They do
  not independently verify the package or infer dietary status from ingredient
  names.
- Ingredient exclusions are text matches; no match is not proof of absence.
- Alternatives are limited to data currently present in the catalog and the
  current user's saved reports.
- Catalog imports retain source/license provenance and flag ambiguous
  same-name or barcode collisions for review. No external catalog discovery,
  scraping, or scheduled synchronization is included; the import service is
  internal and does not expose a public import endpoint.
- Comparisons do not reconcile unrecognized units, unknown serving sizes, or
  mass-vs-volume bases.
- Provider-generated Q&A remains dependent on server configuration and an
  external service; it is not independently verified and falls back
  deterministically when unavailable.
- Frontend tests are Node unit/contract tests; this repository does not
  currently include a browser component-testing harness.
