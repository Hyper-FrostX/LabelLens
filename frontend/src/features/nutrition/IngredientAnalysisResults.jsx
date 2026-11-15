import { getConcernClass } from "./nutritionUtils";

export default function IngredientAnalysisResults({ evidenceConcerns }) {
  return (
    <section
      className="ingredient-analysis"
      aria-labelledby="ingredient-analysis-title"
    >
      <div className="ingredient-analysis-heading">
        <h3 id="ingredient-analysis-title">Ingredient/additive analysis</h3>
        <span className="concern-badge concern-neutral">
          {evidenceConcerns.length} evidence-based{" "}
          {evidenceConcerns.length === 1 ? "concern" : "concerns"}
        </span>
      </div>
      {evidenceConcerns.length > 0 ? (
        <ul className="ingredient-insight-list">
          {evidenceConcerns.map((item, index) => (
            <li
              className="ingredient-insight"
              key={`${item.ingredient}-${index}`}
            >
              <div className="ingredient-insight-heading">
                <strong>{item.matched_name ?? item.ingredient}</strong>
                <span className={`concern-badge ${getConcernClass(item)}`}>
                  {item.concern_level}
                </span>
              </div>
              {item.matched_name && item.matched_name !== item.ingredient && (
                <p className="ingredient-raw-name">
                  Label text: {item.ingredient}
                </p>
              )}
              <p>{item.explanation}</p>
              {item.evidence_source && (
                <p className="evidence-reference">
                  Source:{" "}
                  {item.source_url ? (
                    <a href={item.source_url} target="_blank" rel="noreferrer">
                      {item.evidence_source}
                    </a>
                  ) : (
                    item.evidence_source
                  )}
                </p>
              )}
              {item.evidence_context && (
                <p className="evidence-context">
                  Evidence context: {item.evidence_context}
                </p>
              )}
              {item.needs_review && (
                <p className="review-indicator">
                  Review this ingredient text; the match is uncertain.
                </p>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <>
          <p className="muted-copy">
            No evidence-based ingredient concerns identified from the
            ingredients we could assess.
          </p>
          <p className="evidence-context">
            This does not guarantee that the product is risk-free. Some
            ingredients may be unassessed or have insufficient evidence in
            the current knowledge base.
          </p>
        </>
      )}
    </section>
  );
}
