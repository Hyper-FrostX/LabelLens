import {
  additionalNutrientFields,
  nutrientFields,
} from "./nutritionUtils";
import Button from "../../components/ui/Button";

export default function NutritionInputForm({
  isConfirmed,
  extraction,
  confirmedLabel,
  analysisBasis,
  recommendationGoal,
  analysisServingSize,
  analysisValues,
  analysisAdditionalNutrients,
  analysisProductName,
  analysisIngredientsText,
  analysisMayContainText,
  analysisDeclaredAllergenText,
  saveToHistory,
  accessToken,
  analysisError,
  isAnalyzing,
  onSubmit,
  onBasisChange,
  onRecommendationGoalChange,
  onServingSizeChange,
  onProductNameChange,
  onIngredientsTextChange,
  onMayContainTextChange,
  onDeclaredAllergenTextChange,
  onSaveToHistoryChange,
  onValueChange,
  onAdditionalNutrientChange,
}) {
  return (
    <section className="manual-analysis" aria-label="Nutrition analysis">
      <div className="section-heading">
        <div>
          <p className="step-label">
            {isConfirmed ? "STEP 3 · ANALYZE" : "MANUAL ANALYSIS"}
          </p>
          <h2>Nutrition snapshot</h2>
          <p>
            {isConfirmed
              ? "Your confirmed label values and ingredients are being analyzed."
              : "Enter values manually, or upload, review, and confirm a label above. Confirming reviewed values starts the analysis automatically."}
          </p>
        </div>
      </div>

      <form className="analysis-card" onSubmit={onSubmit} noValidate>
        <fieldset className="basis-fieldset">
          <legend>Values are listed</legend>
          <div className="basis-options">
            {[
              ["per_serving", "Per serving"],
              ["per_100g", "Per 100 g"],
              ["per_100ml", "Per 100 ml"],
              ["", "Not established"],
            ].map(([value, label]) => (
              <label
                className={analysisBasis === value ? "selected" : ""}
                key={value || "unknown"}
              >
                <input
                  type="radio"
                  name="analysisBasis"
                  value={value}
                  checked={analysisBasis === value}
                  disabled={Boolean(extraction)}
                  onChange={() => onBasisChange(value)}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <label className="input-group">
          <span className="input-label">Alternative comparison goal</span>
          <select
            value={recommendationGoal}
            onChange={(event) => onRecommendationGoalChange(event.target.value)}
          >
            <option value="balanced">Balanced comparison</option>
            <option value="lower_sugar">Lower sugar</option>
            <option value="lower_sodium">Lower sodium</option>
            <option value="lower_saturated_fat">Lower saturated fat</option>
            <option value="higher_protein">Higher protein</option>
            <option value="higher_fiber">Higher fiber</option>
            <option value="lower_calories">Lower calories</option>
          </select>
          <span className="muted-copy">Recommendations use only comparable stored product data.</span>
        </label>

        <label className="input-group serving-size-input" htmlFor="analysis-serving-size">
          <span className="input-label">
            Serving size (needed for per-serving assessment)
          </span>
          <input
            id="analysis-serving-size"
            type="text"
            value={analysisServingSize}
            disabled={Boolean(extraction)}
            onChange={(event) => onServingSizeChange(event.target.value)}
            placeholder="For example, 30 g"
          />
        </label>

        <div className="manual-product-fields">
          <label className="input-group" htmlFor="analysis-product-name">
            <span className="input-label">Product name (optional)</span>
            <input
              id="analysis-product-name"
              type="text"
              value={analysisProductName}
              disabled={Boolean(extraction)}
              onChange={(event) => onProductNameChange(event.target.value)}
              placeholder="Not listed"
            />
          </label>
          <label className="input-group" htmlFor="analysis-ingredients-text">
            <span className="input-label">Ingredients text (optional)</span>
            <textarea
              id="analysis-ingredients-text"
              rows="3"
              value={analysisIngredientsText}
              disabled={Boolean(extraction)}
              onChange={(event) => onIngredientsTextChange(event.target.value)}
              placeholder="Paste ingredients as shown on the label"
            />
          </label>
          <label className="input-group" htmlFor="analysis-may-contain-text">
            <span className="input-label">Precautionary “may contain” text (optional)</span>
            <textarea
              id="analysis-may-contain-text"
              rows="2"
              value={analysisMayContainText}
              disabled={Boolean(extraction)}
              onChange={(event) => onMayContainTextChange(event.target.value)}
              placeholder="Enter a separate precautionary declaration"
            />
          </label>
          <label className="input-group" htmlFor="analysis-declared-allergens">
            <span className="input-label">Declared allergen text (optional)</span>
            <textarea
              id="analysis-declared-allergens"
              rows="2"
              value={analysisDeclaredAllergenText}
              disabled={Boolean(extraction)}
              onChange={(event) => onDeclaredAllergenTextChange(event.target.value)}
              placeholder="Enter separate declared allergen text"
            />
          </label>
        </div>

        <div className="nutrient-inputs">
          {nutrientFields.map((field) => (
            <label
              className="input-group"
              htmlFor={`analysis-${field.name}`}
              key={field.name}
            >
              <span className="input-label">{field.label}</span>
              <span className="number-input">
                <input
                  id={`analysis-${field.name}`}
                  name={field.name}
                  type="number"
                  min="0"
                  step="any"
                  inputMode="decimal"
                  value={analysisValues[field.name]}
                  disabled={Boolean(extraction)}
                  onChange={onValueChange}
                  placeholder="Leave blank if unknown"
                />
                <span>{field.unit}</span>
              </span>
            </label>
          ))}
        </div>

        <details className="additional-nutrients-input">
          <summary>Other label nutrients (optional; not included in the health score)</summary>
          <div className="nutrient-inputs">
            {additionalNutrientFields.map((field) => (
              <label
                className="input-group"
                htmlFor={`analysis-${field.name}`}
                key={field.name}
              >
                <span className="input-label">{field.label}</span>
                <span className="number-input">
                  <input
                    id={`analysis-${field.name}`}
                    type="number"
                    min="0"
                    step="any"
                    inputMode="decimal"
                    value={analysisAdditionalNutrients[field.name]?.value ?? ""}
                    disabled={Boolean(extraction)}
                    onChange={(event) =>
                      onAdditionalNutrientChange(field.name, event.target.value)
                    }
                    placeholder="Leave blank if unknown"
                  />
                  <span>{field.unit}</span>
                </span>
              </label>
            ))}
          </div>
        </details>

        <label className="save-history-option">
          <input
            type="checkbox"
            checked={saveToHistory}
            disabled={!accessToken}
            onChange={(event) => onSaveToHistoryChange(event.target.checked)}
          />
          <span>
            Save this reviewed label and analysis to my account history
            {!accessToken && " (sign in first)"}
          </span>
        </label>

        {extraction && !confirmedLabel && (
          <p className="analysis-next-step" role="status">
            Confirm the reviewed label details above to analyze those values automatically.
          </p>
        )}
        {!extraction && (
          <p className="analysis-next-step" role="status">
            Results include excess nutrient assessments and ingredient/additive insights.
          </p>
        )}
        {!extraction && analysisError && (
          <p className="form-error" role="alert">
            <span aria-hidden="true">!</span>
            {analysisError}
          </p>
        )}
        {!extraction && (
          <Button type="submit" disabled={isAnalyzing}>
            {isAnalyzing ? "Analyzing label…" : "Analyze label"}
            {!isAnalyzing && <span aria-hidden="true">→</span>}
          </Button>
        )}
      </form>
    </section>
  );
}
