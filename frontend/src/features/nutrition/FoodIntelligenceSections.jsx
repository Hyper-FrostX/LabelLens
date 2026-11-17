function displayScore(score) {
  if (!score || score.score == null) return "Insufficient data";
  return `${score.score} / 100`;
}

function ScoreCard({ title, score, expertMode }) {
  if (!score) return null;
  return (
    <article className="food-score-card">
      <div>
        <h4>{title}</h4>
        <strong>{displayScore(score)}</strong>
        <span className="product-status">{score.status.replaceAll("_", " ")}</span>
      </div>
      <p>{score.explanation}</p>
      {expertMode && (
        <details>
          <summary>Method and inputs ({score.version})</summary>
          <dl>
            <dt>Formula</dt>
            <dd>{score.formula}</dd>
            <dt>Inputs</dt>
            <dd><pre>{JSON.stringify(score.inputs, null, 2)}</pre></dd>
            {score.missing_inputs?.length > 0 && (
              <>
                <dt>Missing inputs</dt>
                <dd>{score.missing_inputs.join(", ")}</dd>
              </>
            )}
          </dl>
        </details>
      )}
    </article>
  );
}

export default function FoodIntelligenceSections({ intelligence, expertMode }) {
  if (!intelligence) return null;
  const scores = intelligence.scores?.scores ?? {};
  const nutrition = intelligence.nutrition;
  const suitability = intelligence.personal_suitability;
  const density = nutrition?.nutrient_density_per_100 ?? {};
  const perServing = nutrition?.per_serving ?? {};
  const observations = nutrition?.observations ?? [];

  return (
    <section className="food-intelligence-section" aria-labelledby="food-intelligence-title">
      <div className="product-analysis-section-heading">
        <h3 id="food-intelligence-title">Food intelligence</h3>
        <span className="product-status">
          {intelligence.scores?.version ?? "Scores unavailable"}
        </span>
      </div>
      <p>
        Project-defined indicators from the submitted label. They are not official
        grades, medical advice, or a product safety determination.
      </p>
      <div className="food-score-grid">
        <ScoreCard title="Nutrition quality" score={scores.nutrition_quality} expertMode={expertMode} />
        <ScoreCard title="Protein quality index" score={scores.protein_quality} expertMode={expertMode} />
        <ScoreCard title="Ingredient transparency" score={scores.ingredient_transparency} expertMode={expertMode} />
        <ScoreCard title="Profile alignment" score={scores.personalized_suitability} expertMode={expertMode} />
      </div>

      <section className="food-intelligence-subsection" aria-labelledby="nutrition-density-title">
        <h4 id="nutrition-density-title">Nutrient density and observations</h4>
        {Object.keys(density).length ? (
          <dl className="product-analysis-data">
            {Object.entries(density).map(([name, item]) => (
              <div key={name}>
                <dt>{name.replaceAll("_", " ")}</dt>
                <dd>{item.value} {item.unit} {item.basis?.replaceAll("_", " ")}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p>Comparable per-100 nutrient values were not available.</p>
        )}
        {Object.keys(perServing).length > 0 && (
          <>
            <h4>Per serving</h4>
            <dl className="product-analysis-data">
              {Object.entries(perServing).map(([name, item]) => (
                <div key={name}>
                  <dt>{name.replaceAll("_", " ")}</dt>
                  <dd>{item.value} {item.unit}</dd>
                </div>
              ))}
            </dl>
          </>
        )}
        {observations.length > 0 && (
          <ul className="product-analysis-value-list">
            {observations.map((observation, index) => (
              <li key={`${observation.type}-${index}`}>{observation.message}</li>
            ))}
          </ul>
        )}
        {nutrition?.ratios && Object.keys(nutrition.ratios).length > 0 && (
          <p>
            Derived ratios: {Object.entries(nutrition.ratios)
              .map(([name, value]) => `${name.replaceAll("_", " ")} ${value}`)
              .join("; ")}.
          </p>
        )}
        {expertMode && nutrition && (
          <details>
            <summary>Normalization and limitations ({nutrition.version})</summary>
            <p>Reported basis: {nutrition.reported_basis ?? "not established"}; normalized basis: {nutrition.normalized_basis ?? "not established"}.</p>
            {Object.entries(nutrition.ratio_methods ?? {}).map(([name, method]) => (
              <p key={name}>{name.replaceAll("_", " ")}: {method}.</p>
            ))}
            {nutrition.limitations?.map((limitation) => <p key={limitation}>{limitation}</p>)}
          </details>
        )}
      </section>

      <section className="food-intelligence-subsection" aria-labelledby="profile-suitability-title">
        <h4 id="profile-suitability-title">Personalized suitability</h4>
        <p><strong>Status:</strong> {suitability?.status?.replaceAll("_", " ") ?? "Not evaluated"}</p>
        <p>{suitability?.explanation ?? "No profile assessment was returned."}</p>
        {suitability?.score_meaning && <p>{suitability.score_meaning}</p>}
        {suitability?.assessments?.length > 0 ? (
          <ul className="product-analysis-value-list">
            {suitability.assessments.map((item, index) => (
              <li key={`${item.factor}-${index}`}>
                <strong>{item.factor.replaceAll("_", " ")}</strong>: {item.status.replaceAll("_", " ")} — {item.explanation}
              </li>
            ))}
          </ul>
        ) : (
          <p>No profile preferences were available for evaluation.</p>
        )}
        {suitability?.goal_contributions && Object.keys(suitability.goal_contributions).length > 0 && (
          <p>
            Per-serving contributions to configured daily goals:{" "}
            {Object.entries(suitability.goal_contributions)
              .map(([goal, item]) => `${goal.replaceAll("_", " ")} ${item.percent_of_user_target_per_serving}%`)
              .join("; ")}.
          </p>
        )}
      </section>
    </section>
  );
}
