# Phase 7: Indian food label inspection

## Scope and interpretation

The compliance report is an OCR-backed label inspection, not a legal opinion,
FSSAI certification, product-safety determination, or overall compliance score.
`legal_compliance_determination` is always `NOT_EVALUATED`. The overall status
describes the automated inspection only. A field marked `MISSING_INFORMATION`
means that the parser did not find evidence in the supplied text; it does not
prove that the package lacks that information or that the field is legally
required for the product.

## Implemented checks

- **FSSAI number:** identifies license/registration number candidates, retains
  their raw OCR spelling and source text, normalizes common OCR digit
  confusions, and reports whether the normalized candidate has the expected
  14-digit shape. A shape match is not a license lookup. The official status
  remains `NOT_VERIFIED`; OCR-corrected, malformed, missing, or multiple
  candidates require manual review. There is no official API integration and
  the application does not scrape the FoSCoS portal.
- **Label declarations:** detects food name, ingredients, nutrition panel,
  allergen text, vegetarian/non-vegetarian text, FSSAI number, net quantity,
  manufacturer/packer/marketer details, consumer-care text, batch/lot, storage
  instructions, manufacturing/packing dates, best-before, and expiry/use-by
  markings. Each finding includes source text, extracted value, nullable
  confidence, status, and explanation.
- **Ingredients and additives:** reuses `parse_label_text`,
  `split_ingredients_text`, the existing ingredient analysis and knowledge
  catalog, and additive identifier patterns. The original ingredient
  declaration, normalized entries, compound entries, additive identifiers,
  and evidence analysis remain separate.
- **Allergens:** reports explicit declarations, precautionary “may contain”
  statements, ingredient-text alias matches, and possible conflicts as
  different evidence types. Text matches are marked as possible OCR-derived
  matches, not confirmed physical presence. No allergen-safety conclusion is
  made.
- **Nutrition:** reports extracted value, unit, basis, source, and validation
  status per supported nutrient, including energy, protein, fat, saturated and
  trans fat, carbohydrates, sugars, added sugars, sodium, salt, and dietary
  fibre/fiber. Duplicate or unresolved values require review. The only
  cross-value checks are added sugars greater than total sugars and saturated
  fat greater than total fat; either is a possible OCR/data inconsistency, not
  a regulatory violation.
- **Dates:** accepts common numeric Indian day-first and ISO dates, month/year,
  and English month-name forms. Ambiguous day/month order, impossible dates,
  two-digit years, conflicting same-type dates, and unparsed date text require
  review. Expiry is flagged as a potential issue only when an exact, parsed
  expiry date is earlier than the analysis date. A passed best-before date is
  not called an expiry. Relative shelf life is not calculated.
- **Vegetarian declaration:** detects textual declarations and references to
  green/red/brown dot wording in OCR text. It never claims to have inspected
  the physical symbol. A textual conflict is flagged for review.

## Rule engine and applicability

`app.services.label_compliance.LABEL_DETECTION_RULES` is the versioned,
configurable detection-rule registry. Each `DetectionRule` defines an
identifier, field, evidence name, applicability condition, source reference,
and optional product-category keywords. `REGULATORY_SOURCES` provides the
issuing authority, publication date, provision, source URL/version,
verification status, and last-reviewed date. Rule outcomes explicitly state
`OCR_FIELD_DETECTION_ONLY`; applicability and category exemptions remain
separate from detection outcomes. The storage-instruction rule demonstrates
category-keyword applicability for refrigerated/frozen products.

Statuses use `PASS`, `POTENTIAL_ISSUE`, `MISSING_INFORMATION`,
`NEEDS_MANUAL_REVIEW`, `NOT_APPLICABLE`, and `NOT_EVALUATED`. A source marked
`VERIFIED` means the cited source/provision was reviewed; it does not mean the
engine has established that the provision applies to a particular product.
Unconfirmed or category-specific regulatory requirements remain
`REVIEW_REQUIRED`.

## Regulatory sources

The report includes the FSSAI *Food Safety and Standards (Labelling and
Display) Regulations, 2020* Gazette and Version VIII compendium (2025-09-09),
the 2022 first amendment, the 2026 first amendment (effective 2027-07-01),
and the 2026 second amendment on milk/milk-product logos (effective
2028-07-01). Allergen reporting references Regulation 5(14), including the
2022 amendment and its exceptions. Source URLs and review metadata are returned
by the API.

The compendium is treated as a consolidated reference, not as proof that no
later amendment exists. General mandatory-field applicability, category
exemptions, date-marking details, net quantity requirements, symbols, and
other category-specific requirements are not encoded as definitive legal
rules. Those checks report what OCR detected and require regulatory review.
Foreign regulatory standards are not used as substitutes for Indian rules.

## API and integration

- `POST /extract/label` retains its existing extraction fields and adds
  `compliance_report`.
- `POST /analyze/label-compliance` accepts
  `{ "label_text": "...", "product_category": "..." }` and returns a validated
  `LabelComplianceReport`.
- `POST /analyze/product` includes `compliance_report` when original OCR is
  supplied in `label_text`. The existing frontend sends this source text with
  the reviewed product-analysis request. When history is saved, the source OCR
  text is retained in the existing scan record; no schema migration is needed.

The report includes the original OCR text, and findings provide expandable
source evidence. The UI distinguishes 14-digit format shape from official
verification and displays source references, review items, and OCR
limitations.

## OCR and verification limitations

The current Tesseract path does not return calibrated field confidence.
Confidence is therefore `null`, not a fabricated percentage. The compliance
engine inspects text only; it does not inspect the label image for vegetarian
symbols, establish that a detected ingredient is physically present, recover
text omitted by OCR, or verify an FSSAI license. Official FoSCoS verification
is unavailable in the application and is explicitly not performed.

## Validation

- Backend: `python -m pytest -q` — **273 passed**.
- Frontend: `npm test` — **9 passed**.
- Frontend lint: `npm run lint` — **passed**.
- Frontend production build: `npm run build` — **passed**.
- No migration was needed; the OCR source is carried through the existing
  extracted-label/history payload.

## Remaining work and unresolved questions

- Add official license verification only if FSSAI provides an approved,
  documented integration; until then the report remains `NOT_VERIFIED`.
- Review category-specific applicability, exemptions, and future-effective
  amendments against authoritative current instruments before converting any
  detection rule into a definitive legal requirement.
- Add image-based symbol recognition only if a suitable local vision pipeline
  becomes available; OCR text is not a substitute.
- Expand the nutrient parser and date-format coverage when additional
  representative label evidence is available, preserving manual review for
  ambiguous OCR.
