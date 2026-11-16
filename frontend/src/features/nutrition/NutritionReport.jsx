import {
  formatBasis,
  formatValue,
  nutrientLabels,
} from "./nutritionUtils";
import { getSectionStatus } from "./productAnalysisUtils";

export default function NutritionReport({
  analysisResult,
  resultSectionRef,
  expertMode,
}) {
  const nutrition = analysisResult.nutrition_analysis ?? analysisResult;
  const hasExcessNutrients = Array.isArray(nutrition.excess_nutrients);
  return (
    <div
      ref={resultSectionRef}
      className="analysis-result"
      aria-live="polite"
      tabIndex="-1"
    >
      <section className="health-score-card" aria-labelledby="health-score-title">
        <div className="health-score-heading">
          <div>
            <p className="step-label">NUTRIENT SUMMARY</p>
            <h3 id="health-score-title">Experimental Label Lens Health Score</h3>
          </div>
          <span className="product-status" role="status">
            {getSectionStatus(nutrition)}
          </span>
          {nutrition.health_score?.status === "available" ? (
            <div className="health-score-value">
              <strong>{nutrition.health_score.score}</strong>
              <span>out of 100</span>
            </div>
          ) : (
            <strong className="health-score-unavailable">Score unavailable</strong>
          )}
        </div>
        {nutrition.health_score?.status === "available" && (
          <div
            className="health-score-progress"
            role="progressbar"
            aria-label="Experimental Label Lens Health Score"
            aria-valuemin="0"
            aria-valuemax="100"
            aria-valuenow={nutrition.health_score.score}
            aria-valuetext={`${nutrition.health_score.score} out of 100`}
          >
            <span style={{ width: `${nutrition.health_score.score}%` }} />
          </div>
        )}
        <p className="score-completeness">
          {nutrition.health_score?.data_completeness?.text ??
            "Nutrient completeness unavailable"}
        </p>
        {nutrition.health_score?.status === "available" ? (
          <p className="score-explanation">
            {nutrition.health_score.explanation}
          </p>
        ) : (
          <p className="score-unavailable-reason" role="status">
            {nutrition.health_score?.explanation ??
              "The backend did not return a health-score assessment."}
          </p>
        )}
        {expertMode && nutrition.health_score?.factors?.length > 0 && (
          <ul className="score-factor-list">
            {nutrition.health_score.factors.map((factor) => (
              <li key={factor.category}>{factor.explanation}</li>
            ))}
          </ul>
        )}
        <p className="health-score-disclaimer">
          Experimental Label Lens Health Score — not an official health grade
          or medical assessment. This prototype formula is not a validated
          measure of overall health. Ingredient flags are separate and do not
          affect this score.
        </p>
      </section>

      <h3>Excess Nutrient Detection</h3>
      <p className="percentage-context">
        Statuses compare label values with configurable Label Lens project
        references, not official health grades.
      </p>
      <div className="result-list nutrient-assessments">
        {hasExcessNutrients ? nutrition.excess_nutrients.map((nutrient) => (
          <article className="result-row" key={nutrient.nutrient}>
            <div className="result-main">
              <div>
                <span className="result-name">
                  {nutrientLabels[nutrient.nutrient] ?? nutrient.nutrient}
                </span>
                <span className="result-value">
                  {formatValue(nutrient.value)}
                  {nutrient.value == null || !nutrient.unit
                    ? ""
                    : ` ${nutrient.unit}`}
                  {nutrient.basis ? ` · ${formatBasis(nutrient.basis)}` : ""}
                </span>
              </div>
              <span
                className={`level-badge ${nutrient.needs_review || typeof nutrient.status !== "string" ? "level-unknown" : `level-${nutrient.status.toLowerCase().replaceAll(" ", "-")}`}`}
              >
                {nutrient.status ?? "Status not provided"}
              </span>
            </div>
            {nutrient.equivalent_value != null && (
              <p className="converted-equivalent">
                Serving-size equivalent: {nutrient.equivalent_value}{" "}
                {nutrient.unit} {formatBasis(nutrient.equivalent_basis)} ·
                calculated, not separately listed on the label
              </p>
            )}
            <p className="assessment-explanation">{nutrient.explanation}</p>
            {expertMode && nutrient.threshold_explanation && (
              <p className="percentage-context">
                <strong>Project threshold:</strong>{" "}
                {nutrient.threshold_explanation}
              </p>
            )}
            {nutrient.needs_review && (
              <p className="review-indicator">
                Review the label value, unit, serving size, or basis.
              </p>
            )}
          </article>
        )) : (
          <p className="muted-copy">Nutrient assessment details were not returned by the backend.</p>
        )}
      </div>
      {nutrition.note && <p className="disclaimer">{nutrition.note}</p>}
    </div>
  );
}
