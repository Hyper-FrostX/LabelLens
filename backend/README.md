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
