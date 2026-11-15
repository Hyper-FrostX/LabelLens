import { splitIngredientsText } from "../../utils/ingredients";
import Button from "../../components/ui/Button";
import Icon from "../../components/ui/Icon";
import { nutrientFields } from "./nutritionUtils";

export default function LabelReviewForm({
  review,
  isConfirmed,
  isAnalyzing,
  analysisError,
  onUpdateReview,
  onUpdateNutrient,
  onConfirm,
}) {
  const ingredients = splitIngredientsText(review.ingredientsText);

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
            <small>Extracted text · please verify</small>
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
            <small>Extracted text · please verify</small>
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
                ? "Extracted basis · please verify"
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
              <small>Extracted value · please verify</small>
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
            <small>Extracted text · please verify</small>
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
        <summary>Show OCR text for verification</summary>
        <pre>{review.ocrText || "No OCR text was returned."}</pre>
      </details>
    </section>
  );
}
