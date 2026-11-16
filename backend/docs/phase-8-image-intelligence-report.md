# Phase 8 — Image Intelligence and OCR Reliability

## Architecture and processing pipeline

`POST /extract/label` validates the uploaded bytes with Pillow, then sends the in-memory image to `app.services.label_ocr.extract_image_data`. The uploaded image is not modified or written to disk. The service applies EXIF orientation, creates OpenCV preprocessing copies, runs local Tesseract OCR, parses the resulting text with the existing label parser, and returns structured extraction evidence. The existing text-only `extract_text` entry point remains available as a compatibility wrapper.

The upload contract remains JPEG, PNG, or WebP, with a 10 MiB request limit and a 25-megapixel image limit. The server verifies the decoded image format and dimensions rather than trusting its filename or MIME type. Unsupported formats return 415, corrupt images 400, and oversized uploads 413. OCR and preprocessing failures are surfaced as service errors. Processing and OCR are performed in memory; no upload or correction-history migration was added.

## Image preprocessing

The OpenCV pipeline produces OCR copies while preserving the original image:

- Pillow EXIF transpose normalizes orientation before image processing.
- A large, convex four-corner contour may be perspective-warped when its geometry and output area are plausible.
- Text skew is estimated from image contours and corrected only for angles between 0.35 and 10 degrees.
- OCR copies are resized toward a 1,200-pixel minimum and capped at 3,200 pixels on the longest side.
- Contrast-limited adaptive histogram equalization, illumination normalization, denoising, sharpening, and adaptive thresholding provide alternate OCR variants.

The selected OCR variant and applied processing methods are reported. Perspective and skew detection are heuristic; the pipeline can decline a transform when the detected geometry is not sufficiently reliable.

## Region detection

Tesseract line coordinates and text anchors identify likely product-name, ingredient, nutrition, allergen, FSSAI, date, net-quantity, manufacturer, and consumer-care areas. The service retains the region type, extracted text, OCR confidence where available, processing method, and source rectangle. Coordinates refer to EXIF-oriented original-image pixels. Ingredient, nutrition, and other useful regions receive supplemental crop OCR where a region was identified.

Region discovery is rule- and layout-based. It does not guarantee that every printed area is found, and large or multi-column panels can be grouped imperfectly. The raw merged OCR text and individual OCR-pass text remain available for review.

## OCR engine and confidence limitations

Tesseract is run locally, using `TESSERACT_CMD`, PATH discovery, or the configured Windows default. TSV word confidence is grouped into lines and conservatively associated with parser fields. The exposed `ocr_confidence` is the OCR engine’s score, not a calibrated probability that a field is true. A missing score remains `null`; it is not replaced with an invented number.

Fields expose confidence states (`HIGH_CONFIDENCE`, `MEDIUM_CONFIDENCE`, `LOW_CONFIDENCE`, `NEEDS_MANUAL_REVIEW`, or `NOT_DETECTED`), processing method, source region, and review status. Even high OCR confidence does not verify a printed fact; extracted values remain available for user review. The existing parser continues to retain original OCR source text and apply only its conservative, review-required parsing behavior.

## Vegetarian/non-vegetarian symbol inspection

OpenCV HSV color masks identify green and brown candidate regions. Contour geometry is used to distinguish likely circular vegetarian marks from circular or triangular non-vegetarian marks. Candidate rectangles and geometry evidence are returned separately from OCR text declarations. A strong heuristic match is labeled `DETECTED` with `MEDIUM_CONFIDENCE`; numeric visual confidence is not available. Ambiguous detections require review, and no detection does not prove that the package lacks a symbol.

No dietary classification is inferred from ingredients. The UI lets the user confirm vegetarian, confirm non-vegetarian, reject a visual suggestion, or leave it uncertain. User review is recorded separately from both visual detection and textual declaration.

## API changes

- `POST /extract/label` now returns structured `fields`, `regions`, `symbol_detection`, `processing`, `ocr_quality`, and `ocr_passes`, while retaining the existing parser response and `ocr_text`.
- `POST /analyze/product` and `POST /analyze/label-compliance` accept optional `label_corrections`, `corrections_confirmed`, `extraction_metadata`, and `symbol_review` values.
- Correction and extraction metadata are JSON-validated and size-limited. No new endpoint, table, or migration is required.
- Compliance analysis receives original OCR text and the confirmed corrections. It retains original evidence and reports final corrected values separately. Corrections are ignored unless `corrections_confirmed` is true.
- An FSSAI number correction can pass the 14-digit shape check, but its official verification status remains `NOT_VERIFIED`; no official lookup is performed. Existing legal-compliance disclaimers and rule status semantics are unchanged.

The extraction and compliance endpoints retain their existing unauthenticated behavior. Product analysis continues to use the existing optional-authentication and scan-history behavior.

## Frontend correction workflow

After extraction, the review form shows the original image, editable extracted values, original OCR values, confidence states, grouped fields, detected regions and their coordinates, and symbol suggestions. Users can correct common analysis fields and other detected label declarations, then submit their reviewed values. The OCR text and extraction metadata are not overwritten. Confirmed corrections are included in the product-analysis request, and the same Phase 7 compliance engine uses them only when explicitly confirmed.

## Testing and validation

Backend tests cover image validation, preprocessing and geometry transforms, synthetic vegetarian/non-vegetarian marks, OCR TSV confidence and coordinates, extraction API integration, metadata validation, confirmed and unconfirmed corrections, and Phase 7 evidence limitations. Frontend tests cover payload construction, retained OCR evidence, corrections, confidence metadata, regions, and symbol detection. The existing migration validation tests run as part of the backend suite; Phase 8 adds no migration.

Final validation:

- Backend: `284 passed`; one existing Starlette/httpx deprecation warning.
- Frontend tests: `12 passed`.
- Frontend lint: passed.
- Frontend production build: passed.
- Existing migration validation: included in the passing backend suite; no migration was needed.

Tests use synthetic images and mocked OCR where deterministic output is required; they do not depend on network services.

## Known limitations and future improvements

- Tesseract and its language data must be installed locally; the Python package alone does not provide the executable.
- OCR confidence is engine-provided but not field-calibrated. All values should be checked against the package.
- Region grouping, column reading order, perspective correction, and symbol color/shape detection are heuristics; no trained model is used.
- Shadows, glare, curved packaging, low-resolution print, and overlapping artwork can still prevent accurate reading.
- Symbol candidates must be visually confirmed. The system does not establish regulatory compliance, dietary suitability, official FSSAI license status, or product safety.
- Regulatory requirements, exemptions, and amendments remain subject to the existing evidence-backed Phase 7 rule set and its manual-review limits.
