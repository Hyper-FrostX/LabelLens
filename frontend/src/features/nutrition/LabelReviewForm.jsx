import { splitIngredientsText } from "../../utils/ingredients";
import Button from "../../components/ui/Button";
import Icon from "../../components/ui/Icon";
import { additionalNutrientFields, nutrientFields } from "./nutritionUtils";

export default function LabelReviewForm({
  review,
  isConfirmed,
  isAnalyzing,
  analysisError,
  onUpdateReview,
  onUpdateOtherField,
  onUpdateSymbolReview,
  onUpdateNutrient,
  onUpdateAdditionalNutrient,
  onConfirm,
  previewUrl,
}) {
  const ingredients = splitIngredientsText(review.ingredientsText);
  const confidenceFields = review.fields ?? [];
  const groupedFields = confidenceFields.reduce((groups, field) => {
    const type = field.field_type || "other";
    groups[type] = [...(groups[type] ?? []), field];
    return groups;
  }, {});
  const confidenceFor = (name) =>
    confidenceFields.find((field) => field.field_name === name);
  const formatOriginal = (value) =>
    value === null || value === undefined || value === "" ? "Not detected" : String(value);
  const confidenceLabel = (field) => {
    if (!field) return "Confidence unavailable";
    const labels = {
      HIGH_CONFIDENCE: "Higher OCR confidence",
      MEDIUM_CONFIDENCE: "Medium OCR confidence",
      LOW_CONFIDENCE: "Low OCR confidence",
      NEEDS_MANUAL_REVIEW: "Needs manual review",
      NOT_DETECTED: "Not detected",
    };
    const score =
      typeof field.ocr_confidence === "number"
        ? ` · Tesseract ${field.ocr_confidence.toFixed(0)} (uncalibrated)`
        : "";
    return `${labels[field.confidence_state] ?? "Needs manual review"}${score}`;
  };
  const fieldLabel = (value) =>
    value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

  return (
    <section className="review-section" aria-labelledby="review-title">
      <div className="section-heading">
        <div>
          <p className="step-label">STEP 2 · REVIEW</p>
          <h2 id="review-title">Review extracted details</h2>
          <p>Correct anything that doesn’t match the package.</p>
        </div>
        <span className={`review-status ${isConfirmed ? "confirmed" : ""}`}>
          {isConfirmed ? <Icon name="check" size={14} /> : <span aria-hidden="true">!</span>}
          {isConfirmed ? "Confirmed" : "Needs review"}
        </span>
      </div>

      <form className="review-card" onSubmit={onConfirm}>
        {previewUrl && (
          <figure className="review-image-preview">
            <img src={previewUrl} alt="Original uploaded food label" />
            <figcaption>Original uploaded image · unchanged by OCR preprocessing</figcaption>
          </figure>
        )}
        <div className="review-grid">
          <label className="review-field">
            <span>Product name</span>
            <input
              type="text"
              value={review.productName}
              placeholder="Not found on label"
              onChange={(event) =>
                onUpdateReview("productName", event.target.value)
              }
            />
            <small>
              Original OCR: {formatOriginal(review.originalValues.productName)} · Final value is the editable text above.
              {" "}{confidenceLabel(confidenceFor("product_name"))}.
            </small>
          </label>

          <label className="review-field">
            <span>Serving size</span>
            <input
              type="text"
              value={review.servingSize}
              placeholder="Not found on label"
              onChange={(event) =>
                onUpdateReview("servingSize", event.target.value)
              }
            />
            <small>
              Original OCR: {formatOriginal(review.originalValues.servingSize)} · Final value is the editable text above.
              {" "}{confidenceLabel(confidenceFor("serving_size_text"))}.
            </small>
          </label>

          <label className="review-field">
            <span>Nutrition values are listed</span>
            <select
              value={review.basis}
              onChange={(event) => onUpdateReview("basis", event.target.value)}
            >
              <option value="">Not established — choose basis</option>
              <option value="per_serving">Per serving</option>
              <option value="per_100g">Per 100 g</option>
              <option value="per_100ml">Per 100 ml</option>
            </select>
            <small>
              {review.basis
                ? `Original OCR: ${formatOriginal(review.originalValues.basis)} · verify the final selection`
                : "The label basis could not be established"}
            </small>
          </label>

          {nutrientFields.map((field) => (
            <label className="review-field" key={field.name}>
              <span>{field.label}</span>
              <span className="review-input-wrap">
                <input
                  type="number"
                  min="0"
                  step="any"
                  inputMode="decimal"
                  value={review.nutrients[field.name]}
                  placeholder="Not found"
                  onChange={(event) =>
                    onUpdateNutrient(field.name, event.target.value)
                  }
                  aria-label={`${field.label} in ${field.unit}`}
                />
                <span>{field.unit}</span>
              </span>
              <small>
                Original OCR: {formatOriginal(review.originalValues.nutrients[field.name])} · Final value is the editable number above.
                {confidenceFor(`nutrients.${field.name}`) && (
                  <> {confidenceLabel(confidenceFor(`nutrients.${field.name}`))}.</>
                )}
              </small>
            </label>
          ))}

          {additionalNutrientFields
            .filter((field) => review.additionalNutrients[field.name]?.value !== "")
            .map((field) => (
              <label className="review-field" key={field.name}>
                <span>{field.label}</span>
                <span className="review-input-wrap">
                  <input
                    type="number"
                    min="0"
                    step="any"
                    inputMode="decimal"
                    value={review.additionalNutrients[field.name].value}
                    onChange={(event) =>
                      onUpdateAdditionalNutrient(field.name, event.target.value)
                    }
                    aria-label={`${field.label} in ${review.additionalNutrients[field.name].unit}`}
                  />
                  <span>{review.additionalNutrients[field.name].unit}</span>
                </span>
                <small>
                  Original OCR: {formatOriginal(review.originalValues.nutrients[field.name])} · Final value is editable; not used in the existing health score.
                  {confidenceFor(`nutrients.${field.name}`) && (
                    <> {confidenceLabel(confidenceFor(`nutrients.${field.name}`))}.</>
                  )}
                </small>
              </label>
            ))}

          <label className="review-field review-field-wide">
            <span>Ingredients text</span>
            <textarea
              rows="4"
              value={review.ingredientsText}
              placeholder="Ingredients not found"
              onChange={(event) =>
                onUpdateReview("ingredientsText", event.target.value)
              }
            />
            <small>
              Original OCR: {formatOriginal(review.originalValues.ingredientsText)} · Final value is the editable text above.
              {" "}{confidenceLabel(confidenceFor("ingredients_text"))}.
            </small>
          </label>

          <label className="review-field review-field-wide">
            <span>Precautionary “may contain” text</span>
            <textarea
              rows="2"
              value={review.mayContainText}
              placeholder="Not found"
              onChange={(event) =>
                onUpdateReview("mayContainText", event.target.value)
              }
            />
            <small>
              Enter only a separate precautionary declaration if present;
              extracted text needs verification. Original OCR: {formatOriginal(review.originalValues.mayContainText)}.
            </small>
          </label>

          <label className="review-field review-field-wide">
            <span>Declared allergen text</span>
            <textarea
              rows="2"
              value={review.declaredAllergenText}
              placeholder="Not found"
              onChange={(event) =>
                onUpdateReview("declaredAllergenText", event.target.value)
              }
            />
            <small>
              Keep declared allergen text separate from precautionary
              “may contain” text. Original OCR: {formatOriginal(review.originalValues.declaredAllergenText)}.
            </small>
          </label>
        </div>

        <div className="ingredients-list">
          <span className="input-label">Recognized ingredient items</span>
          {ingredients.length > 0 ? (
            <div className="ingredient-chips">
              {ingredients.map((ingredient, index) => (
                <span className="ingredient-chip" key={`${ingredient}-${index}`}>
                  {ingredient}
                </span>
              ))}
            </div>
          ) : (
            <p className="muted-copy">No reliably separated items found.</p>
          )}
        </div>

        {Object.keys(review.otherFields ?? {}).length > 0 && (
          <fieldset className="review-other-fields">
            <legend>Other detected label fields</legend>
            <p>These are original OCR suggestions. Confirm or correct each value before submitting.</p>
            {Object.entries(review.otherFields).map(([name, value]) => (
              <label className="review-field" key={name}>
                <span>{fieldLabel(name)}</span>
                <input
                  type="text"
                  value={value}
                  onChange={(event) => onUpdateOtherField(name, event.target.value)}
                />
                <small>
                  Original OCR: {formatOriginal(review.originalOtherFields?.[name])}.
                  {" "}Final value for analysis · original OCR evidence remains in the report.
                </small>
              </label>
            ))}
          </fieldset>
        )}

        <section className="review-symbol-section" aria-labelledby="symbol-review-title">
          <h3 id="symbol-review-title">Vegetarian / non-vegetarian symbol review</h3>
          <p>Visual color-and-shape matches are heuristic suggestions, not symbol verification. Inspect the original image.</p>
          {["vegetarian", "non_vegetarian"].map((kind) => {
            const symbol = review.symbolDetection?.[kind];
            return (
              <p key={kind}>
                {fieldLabel(kind)} symbol: {symbol?.status ?? "NOT_DETECTED"}
                {symbol?.region && ` · image region ${symbol.region.x}, ${symbol.region.y}, ${symbol.region.width} × ${symbol.region.height}`}
              </p>
            );
          })}
          <label className="review-field">
            <span>My visual review</span>
            <select
              value={review.symbolReview}
              onChange={(event) => onUpdateSymbolReview(event.target.value)}
            >
              <option value="">Not reviewed</option>
              <option value="VEGETARIAN">Confirm vegetarian symbol</option>
              <option value="NON_VEGETARIAN">Confirm non-vegetarian symbol</option>
              <option value="REJECTED">Reject visual suggestion</option>
              <option value="NEEDS_MANUAL_REVIEW">Still uncertain</option>
            </select>
          </label>
        </section>

        <details className="review-extraction-details">
          <summary>Structured OCR fields and confidence by label section</summary>
          {Object.entries(groupedFields).map(([type, fields]) => (
            <section key={type}>
              <h4>{fieldLabel(type)}</h4>
              <ul>
                {fields.map((field) => (
                  <li key={field.field_name}>
                    <strong>{fieldLabel(field.field_name)}:</strong>{" "}
                    {field.extracted_value == null
                      ? "Not detected"
                      : typeof field.extracted_value === "string"
                        ? field.extracted_value
                        : JSON.stringify(field.extracted_value)}
                    {" — "}{confidenceLabel(field)}
                    {field.processing_method && ` · ${field.processing_method}`}
                    {field.review_status && ` · ${field.review_status}`}
                  </li>
                ))}
              </ul>
            </section>
          ))}
          {review.regions.length > 0 && (
            <section>
              <h4>Detected source regions (EXIF-oriented original pixels)</h4>
              <ul>
                {review.regions.map((region, index) => (
                  <li key={`${region.region_type}-${index}`}>
                    <strong>{fieldLabel(region.region_type)}</strong>
                    {region.source_coordinates && (
                      <> · {region.source_coordinates.x}, {region.source_coordinates.y}, {region.source_coordinates.width} × {region.source_coordinates.height}</>
                    )}
                    <pre>{region.extracted_text || "No text extracted from this region."}</pre>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </details>

        <div className="review-required">
          <strong>Fields requiring review</strong>
          <span>
            {review.reviewRequiredFields.length
              ? review.reviewRequiredFields.join(", ")
              : "None reported"}
          </span>
        </div>

        <Button
          className="confirm-button"
          type="submit"
          disabled={isAnalyzing}
        >
          {isAnalyzing
            ? "Analyzing label…"
            : analysisError
              ? "Retry analysis"
              : "Confirm reviewed values"}
          {!isAnalyzing && <span aria-hidden="true">→</span>}
        </Button>
        {isConfirmed && (
          <p className="success-message" role="status">
            {isAnalyzing
              ? "Review confirmed. Analyzing the reviewed values…"
              : analysisError
                ? "Review confirmed. Analysis failed; use the button above to retry."
                : "Review confirmed and analysis is complete."}
          </p>
        )}
        {analysisError && (
          <p className="form-error" role="alert">
            <span aria-hidden="true">!</span>
            {analysisError}
          </p>
        )}
      </form>

      <details className="ocr-details">
        <summary>Show original OCR text for verification</summary>
        <pre>{review.ocrText || "No OCR text was returned."}</pre>
      </details>
    </section>
  );
}
