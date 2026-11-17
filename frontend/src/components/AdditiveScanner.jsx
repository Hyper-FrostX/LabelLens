import { useEffect, useRef, useState } from "react";
import Button from "./ui/Button";
import Icon from "./ui/Icon";
import Spinner from "./ui/Spinner";
import { revokeInactiveImagePreviewUrls } from "./imagePreviewUrls.js";

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
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [scannedImageName, setScannedImageName] = useState("");
  const [scannedPreviewUrl, setScannedPreviewUrl] = useState("");
  const [foodSuggestions, setFoodSuggestions] = useState([]);
  const [dietaryAdvice, setDietaryAdvice] = useState("");
  const [visionProvider, setVisionProvider] = useState("rule_based");
  const fileInputRef = useRef(null);
  const imagePreviewUrlsRef = useRef(new Set());

  useEffect(() => {
    revokeInactiveImagePreviewUrls(
      imagePreviewUrlsRef.current,
      scannedPreviewUrl,
      (url) => URL.revokeObjectURL(url),
    );
  }, [scannedPreviewUrl]);

  useEffect(
    () => () => {
      revokeInactiveImagePreviewUrls(
        imagePreviewUrlsRef.current,
        null,
        (url) => URL.revokeObjectURL(url),
      );
    },
    [],
  );

  async function handleImageUpload(file) {
    if (!file) return;
    setError("");
    setIsUploadingImage(true);
    setScannedImageName(file.name);
    const objectUrl = URL.createObjectURL(file);
    imagePreviewUrlsRef.current.add(objectUrl);
    setScannedPreviewUrl(objectUrl);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${apiBaseUrl}/extract/label`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let msg = `Image analysis failed (HTTP ${response.status})`;
        try {
          const errData = await response.json();
          if (errData?.detail) msg = errData.detail;
        } catch {
          // ignore json parse error
        }
        throw new Error(msg);
      }

      const data = await response.json();
      const text =
        data.ingredients_text ||
        (Array.isArray(data.ingredients) ? data.ingredients.join(", ") : "");
      if (!text.trim()) {
        throw new Error(
          "Could not detect any ingredient text in this image. Please enter ingredients manually or try a clearer photo."
        );
      }

      setIngredientsText(text);
      if (
        Array.isArray(data.food_suggestions) &&
        data.food_suggestions.length > 0
      ) {
        setFoodSuggestions(data.food_suggestions);
      } else {
        setFoodSuggestions([]);
      }
      setDietaryAdvice(data.dietary_advice || "");
      setVisionProvider(data.vision_provider || "rule_based");

      await runScan(text);
    } catch (err) {
      setError(err.message || "Failed to analyze image.");
    } finally {
      setIsUploadingImage(false);
    }
  }

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
        title: "No Catalog Matches",
        subtitle:
          result?.total_ingredients_scanned > 0
            ? "No current catalog entry matched. This does not establish ingredient absence or product safety."
            : "Enter an ingredient list to begin scanning.",
      };
    }

    if (result.counts.review_required > 0) {
      return {
        badgeClass: "verdict-moderate",
        title: `${result.counts.review_required} Entry${result.counts.review_required > 1 ? "s" : ""} Require Review`,
        subtitle: "Legacy health and regulatory claims are withheld until authoritative sources are verified.",
      };
    }

    if (result.counts.informational > 0) {
      return {
        badgeClass: "verdict-low",
        title: "Verified Information Found",
        subtitle: "Verified source facts do not determine exposure or risk from a particular product.",
      };
    }

    return {
      badgeClass: "verdict-moderate",
      title: "No Health Assessment Available",
      subtitle: "Ingredient identity alone cannot establish product safety or risk.",
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

        {/* Gemini Vision Image Upload */}
        <div className="scanner-image-upload-wrap">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
            className="visually-hidden"
            onChange={(e) => handleImageUpload(e.target.files?.[0])}
          />
          <div className="scanner-image-upload-row">
            <div className="scanner-upload-prompt">
              <span aria-hidden="true">📸</span>
              <span>Scan label or package photo (Gemini Vision)</span>
            </div>
            {scannedImageName ? (
              <div className="scanned-image-preview-badge">
                {scannedPreviewUrl && (
                  <img src={scannedPreviewUrl} alt="Scanned label thumbnail" />
                )}
                <span>{scannedImageName}</span>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploadingImage}
                >
                  Change
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="scanner-upload-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingImage}
              >
                {isUploadingImage ? (
                  <>
                    <span className="spinner" aria-hidden="true" />
                    Analyzing image…
                  </>
                ) : (
                  <>
                    Upload package photo
                    <span aria-hidden="true">↑</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>

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
            <Button
              type="submit"
              disabled={isScanning || !ingredientsText.trim()}
            >
              {isScanning ? (
                <>
                  <Spinner />
                  Scanning ingredients…
                </>
              ) : (
                <>
                  Scan for additives
                  <span aria-hidden="true">→</span>
                </>
              )}
            </Button>

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
            <span className="info-icon">
              <Icon name="sparkle" size={17} />
            </span>
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

            <div className="stats-grid">
              <div className="stat-box">
                <span className="stat-label">Scanned</span>
                <strong className="stat-number">{scanResult.total_ingredients_scanned}</strong>
              </div>
              <div className="stat-box stat-review">
                <span className="stat-label">Review Required</span>
                <strong className="stat-number">{scanResult.counts.review_required}</strong>
              </div>
              <div className="stat-box stat-info">
                <span className="stat-label">Verified Information</span>
                <strong className="stat-number">{scanResult.counts.informational}</strong>
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
                    const levelClass =
                      additive.verification_status === "REVIEW_REQUIRED"
                        ? "level-review-required"
                        : "level-informational";
                    const levelLabel =
                      additive.verification_status === "REVIEW_REQUIRED"
                        ? "Review required"
                        : additive.verification_status === "PROVISIONAL"
                        ? "Provisional"
                        : "Verified facts";

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
                            <span className="info-key">Evidence:</span>
                            <span className="info-val evidence-summary">
                              {additive.concern_summary}
                            </span>
                          </div>

                          <div className="additive-info-row">
                            <span className="info-key">Regulatory Reference:</span>
                            <span className="info-val regulatory-val">
                              {additive.regulatory_status}
                            </span>
                          </div>

                          <div className="additive-recommendation">
                            <span>{additive.recommendation}</span>
                          </div>
                        </div>

                        <footer className="additive-card-footer">
                          <span>
                            Source: {additive.evidence_source || "No verified source citation"}
                            {additive.evidence_url ? ` — ${additive.evidence_url}` : ""}
                          </span>
                        </footer>
                      </article>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="no-additives-box">
                <span className="check-mark">
                  <Icon name="check" size={22} />
                </span>
                <h4>No Catalog Matches</h4>
                <p>
                  No current catalog entry matched. This does not establish ingredient absence,
                  product safety, or a complete label review.
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

            {/* Food Suggestions from Gemini Vision */}
            {foodSuggestions?.length > 0 && (
              <div className="food-suggestions-section" style={{ marginTop: "24px", padding: "20px" }}>
                <div className="food-suggestions-header">
                  <div className="food-suggestions-title-group">
                    <span className="suggestion-badge-icon" aria-hidden="true">
                      🌱
                    </span>
                    <div>
                      <p className="step-label">SMART NUTRITION CHOICES</p>
                      <h4
                        style={{
                          margin: 0,
                          fontSize: "1.15rem",
                          fontWeight: 700,
                          color: "#1a3826",
                        }}
                      >
                        Healthy Food Suggestions &amp; Alternatives
                      </h4>
                    </div>
                  </div>
                  <span className="ai-vision-pill">
                    {visionProvider === "gemini"
                      ? "Powered by Gemini Vision"
                      : "LabelLens rule-based suggestions"}
                  </span>
                </div>

                {dietaryAdvice && (
                  <div className="dietary-advice-card">
                    <span className="advice-icon" aria-hidden="true">
                      💡
                    </span>
                    <div className="advice-content">
                      <strong>Personalized Nutrition Advice</strong>
                      <p>{dietaryAdvice}</p>
                    </div>
                  </div>
                )}

                <div className="food-suggestions-grid">
                  {foodSuggestions.map((item, index) => (
                    <article
                      className="food-suggestion-card"
                      key={`${item.name}-${index}`}
                    >
                      <div className="suggestion-card-top">
                        <span className="suggestion-category-tag">
                          {item.category}
                        </span>
                        <span className="suggestion-icon" aria-hidden="true">
                          🥗
                        </span>
                      </div>
                      <h5 className="suggestion-food-name">{item.name}</h5>
                      <p className="suggestion-reason">{item.reason}</p>
                      {item.highlights?.length > 0 && (
                        <div className="suggestion-highlights">
                          {item.highlights.map((h, i) => (
                            <span className="highlight-pill" key={i}>
                              ✓ {h}
                            </span>
                          ))}
                        </div>
                      )}
                    </article>
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
