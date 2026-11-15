import { nutrientFields } from "./nutritionUtils";
import Button from "../../components/ui/Button";

export default function NutritionInputForm({
  isConfirmed,
  extraction,
  confirmedLabel,
  analysisBasis,
  analysisServingSize,
  analysisValues,
  analysisError,
  isAnalyzing,
  onSubmit,
  onBasisChange,
  onServingSizeChange,
  onValueChange,
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
