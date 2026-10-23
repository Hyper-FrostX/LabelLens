import { useState } from "react";

const PRESETS = [
  {
    title: "Bakery with Dough Conditioners",
    text: "Enriched wheat flour, water, high fructose corn syrup, potassium bromate, calcium propionate, salt, soy lecithin",
    description: "Contains flour improver (potassium bromate), mold inhibitor, and natural lecithin",
  },
  {
    title: "Citrus Soft Drink",
    text: "Carbonated water, high fructose corn syrup, citric acid, brominated vegetable oil (BVO), sodium benzoate, yellow 5",
    description: "Contains BVO stabilizer, sodium benzoate preservative, and yellow 5 azo dye",
  },
  {
    title: "Whitened Confectionery",
    text: "Sugar, corn syrup, titanium dioxide (E171), red 40, citric acid, carnauba wax",
    description: "Features titanium dioxide whitening agent and red 40 food coloring",
  },
  {
    title: "Diet Carbonated Beverage",
    text: "Carbonated water, caramel color IV (E150d), aspartame, acesulfame potassium, phosphoric acid, citric acid",
    description: "Features intense artificial sweeteners and ammoniated caramel color",
  },
  {
    title: "Clean Label Whole Granola",
    text: "Organic rolled oats, wildflower honey, coconut oil, roasted almonds, cinnamon, sea salt",
    description: "Whole food ingredients with no artificial additives or preservatives",
  },
];

export default function AdditiveScanner({ apiBaseUrl }) {
  const [ingredientsText, setIngredientsText] = useState("");
  const [scanResult, setScanResult] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState("");

  async function runScan(textToScan) {
    const text = typeof textToScan === "string" ? textToScan : ingredientsText;
    if (!text.trim()) {
      setError("Please enter or paste an ingredients list to scan.");
      return;
    }

    setError("");
    setIsScanning(true);

    try {
      const response = await fetch(`${apiBaseUrl}/analyze/ingredients`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ingredients_text: text }),
      });

      if (!response.ok) {
        let msg = `Request failed (HTTP ${response.status})`;
        try {
          const data = await response.json();
          if (data?.detail) msg = data.detail;
        } catch {
          // ignore json parse error
        }
        throw new Error(msg);
      }

      const result = await response.json();
      setScanResult(result);
    } catch (err) {
      setError(
        err instanceof TypeError
          ? `Could not connect to Label Lens API at ${apiBaseUrl}. Ensure the backend is running.`
          : err.message
      );
    } finally {
      setIsScanning(false);
    }
  }

  function handlePresetSelect(presetText) {
    setIngredientsText(presetText);
    runScan(presetText);
  }

  function getVerdictDetails(result) {
    if (!result || result.total_additives_detected === 0) {
      return {
        badgeClass: "verdict-clean",
        title: "No Flagged Additives Detected",
        subtitle:
          result?.total_ingredients_scanned > 0
            ? "All detected items appear to be whole foods or uncatalogued standard ingredients."
            : "Enter an ingredient list to begin scanning.",
      };
    }

    if (result.counts.high > 0) {
      return {
        badgeClass: "verdict-high",
        title: `${result.counts.high} High-Concern Additive${result.counts.high > 1 ? "s" : ""} Detected`,
        subtitle:
          "Includes additives banned or heavily restricted in major international food jurisdictions due to toxicological evidence.",
      };
    }

    if (result.counts.moderate > 0) {
      return {
        badgeClass: "verdict-moderate",
        title: `${result.counts.moderate} Moderate-Concern Additive${result.counts.moderate > 1 ? "s" : ""} Identified`,
        subtitle:
          "Additives with substantiated sensitivity concerns, pediatric hyperactivity warnings, or acceptable daily intake (ADI) limits.",
      };
    }

    return {
      badgeClass: "verdict-low",
      title: "Safe & Functional Additives Identified",
      subtitle:
        "The identified additives are widely recognized as safe (GRAS / EFSA approved) with established functional benefits and no adverse health flags.",
    };
  }

  const verdict = getVerdictDetails(scanResult);

  return (
    <div className="additive-scanner-layout">
      {/* Left Input Column */}
      <section className="analysis-card scanner-input-card">
        <div className="card-heading">
          <div>
            <p className="step-label">INGREDIENT SCANNER</p>
            <h2>Check for Additives & Ingredients</h2>
          </div>
          <span className="optional-label">Evidence-based analysis</span>
        </div>

        <p className="scanner-instructions">
          Paste the ingredients text from any food or beverage label. Label Lens identifies
          additives from a curated scientific knowledge base, highlights their functional purpose,
          and displays evidence-based concern levels without labeling every additive as harmful.
        </p>

        {/* Quick Presets */}
        <div className="presets-container">
          <span className="presets-label">Try a sample label:</span>
          <div className="preset-chips">
            {PRESETS.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                className="preset-chip"
                title={preset.description}
                onClick={() => handlePresetSelect(preset.text)}
              >
                {preset.title}
              </button>
            ))}
          </div>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            runScan();
          }}
        >
          <label className="input-group" htmlFor="ingredients-input">
            <span className="input-label">Ingredients list</span>
            <span className="input-description">
              Comma-separated ingredients (e.g. &ldquo;wheat flour, water, titanium dioxide (E171), citric acid&rdquo;)
            </span>
            <textarea
              id="ingredients-input"
              className="ingredients-textarea"
              rows={5}
              placeholder="e.g. Enriched flour, water, high fructose corn syrup, potassium bromate, citric acid..."
              value={ingredientsText}
              onChange={(e) => setIngredientsText(e.target.value)}
            />
          </label>

          {error && (
            <p className="form-error" role="alert">
              <span aria-hidden="true">!</span>
              {error}
            </p>
          )}

          <div className="scanner-actions">
            <button
              type="submit"
              className="submit-button"
              disabled={isScanning || !ingredientsText.trim()}
            >
              {isScanning ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  Scanning ingredients…
                </>
              ) : (
                <>
                  Scan for additives
                  <span aria-hidden="true">→</span>
                </>
              )}
            </button>

            {ingredientsText && (
              <button
                type="button"
                className="clear-button"
                onClick={() => {
                  setIngredientsText("");
                  setScanResult(null);
                  setError("");
                }}
              >
                Clear
              </button>
            )}
          </div>
        </form>

        <div className="educational-note-card">
          <div className="educational-note-header">
            <span className="info-icon" aria-hidden="true">💡</span>
            <strong>The Scientific Approach</strong>
          </div>
          <p>
            Food additives serve vital functions: preventing dangerous food spoilage (like botulism),
            stabilizing nutrients, and maintaining texture. We avoid blanket alarmism and categorize
            additives by transparent scientific assessments from EFSA, FDA, and WHO/JECFA.
          </p>
        </div>
      </section>

      {/* Right Results Column */}
      <section className="results-card scanner-results-card" aria-live="polite">
        {scanResult ? (
          <div className="results-content">
            <p className="step-label">EVALUATION SUMMARY</p>
            <div className={`verdict-banner ${verdict.badgeClass}`}>
              <div>
                <span className="verdict-tag">Overall Assessment</span>
                <h3 className="verdict-title">{verdict.title}</h3>
                <p className="verdict-subtitle">{verdict.subtitle}</p>
              </div>
            </div>

            {/* Counts Breakdown Bar */}
            <div className="stats-grid">
              <div className="stat-box">
                <span className="stat-label">Scanned</span>
                <strong className="stat-number">{scanResult.total_ingredients_scanned}</strong>
              </div>
              <div className="stat-box stat-high">
                <span className="stat-label">High Concern</span>
                <strong className="stat-number">{scanResult.counts.high}</strong>
              </div>
              <div className="stat-box stat-moderate">
                <span className="stat-label">Moderate</span>
                <strong className="stat-number">{scanResult.counts.moderate}</strong>
              </div>
              <div className="stat-box stat-low">
                <span className="stat-label">Safe / Functional</span>
                <strong className="stat-number">{scanResult.counts.low}</strong>
              </div>
            </div>

            {/* Identified Additives List */}
            {scanResult.matched_additives.length > 0 ? (
              <div className="matched-additives-section">
                <h4 className="section-subheading">
                  Identified Additives ({scanResult.matched_additives.length})
                </h4>

                <div className="additives-card-list">
                  {scanResult.matched_additives.map((additive) => {
                    const levelClass = `level-${additive.concern_level}`;
                    const levelLabel =
                      additive.concern_level === "high"
                        ? "High Concern"
                        : additive.concern_level === "moderate"
                        ? "Moderate Concern"
                        : "Safe / Low Concern";

                    return (
                      <article className={`additive-detail-card ${levelClass}`} key={additive.id}>
                        <div className="additive-card-header">
                          <div>
                            <div className="additive-name-row">
                              <h5 className="additive-name">{additive.name}</h5>
                              {additive.e_number && (
                                <span className="e-number-pill">{additive.e_number}</span>
                              )}
                            </div>
                            <span className="detected-in-text">
                              Detected in: &ldquo;{additive.detected_in_ingredient}&rdquo;
                            </span>
                          </div>
                          <span className={`concern-badge ${levelClass}`}>
                            {levelLabel}
                          </span>
                        </div>

                        <div className="additive-card-body">
                          <div className="additive-info-row">
                            <span className="info-key">Purpose:</span>
                            <span className="info-val">{additive.purpose}</span>
                          </div>

                          <div className="additive-info-row">
                            <span className="info-key">Scientific Evidence:</span>
                            <span className="info-val evidence-summary">
                              {additive.concern_summary}
                            </span>
                          </div>

                          <div className="additive-info-row">
                            <span className="info-key">Regulatory Status:</span>
                            <span className="info-val regulatory-val">
                              {additive.regulatory_status}
                            </span>
                          </div>

                          <div className="additive-recommendation">
                            <span className="tip-icon" aria-hidden="true">✓</span>
                            <span>{additive.recommendation}</span>
                          </div>
                        </div>

                        <footer className="additive-card-footer">
                          <span>Source: {additive.evidence_source}</span>
                        </footer>
                      </article>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="no-additives-box">
                <span className="check-mark" aria-hidden="true">🌿</span>
                <h4>Clean Label Ingredients</h4>
                <p>
                  No controversial, restricted, or synthetic additives from the curated database were
                  detected in this formulation.
                </p>
              </div>
            )}

            {/* Unmatched / Base Ingredients Tags */}
            {scanResult.unmatched_ingredients.length > 0 && (
              <div className="unmatched-section">
                <span className="unmatched-title">Base & Natural Ingredients:</span>
                <div className="unmatched-tags">
                  {scanResult.unmatched_ingredients.map((item, index) => (
                    <span className="ingredient-tag" key={index}>
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <p className="disclaimer">{scanResult.guidance_note}</p>
          </div>
        ) : (
          <div className="empty-results">
            <span className="empty-icon" aria-hidden="true">
              <svg viewBox="0 0 48 48" fill="none">
                <path
                  d="M18 10h12M24 10v14M16 38h16a4 4 0 0 0 4-4V24L28 14h-8L12 24v10a4 4 0 0 0 4 4z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle cx="21" cy="30" r="1.5" fill="currentColor" />
                <circle cx="27" cy="33" r="1.5" fill="currentColor" />
              </svg>
            </span>
            <h2>Additive scan results will appear here</h2>
            <p>
              Enter or select an ingredients list on the left to scan for additives, analyze their
              purpose, and review evidence-based concern levels.
            </p>
            <div className="scanner-empty-hints">
              <span className="hint-pill">Evidence-based ratings</span>
              <span className="hint-pill">Non-alarmist classifications</span>
              <span className="hint-pill">EFSA & FDA verified</span>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
