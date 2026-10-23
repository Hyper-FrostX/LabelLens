import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];

const nutrientFields = [
  { name: "sugar_g", label: "Total sugar", unit: "g" },
  { name: "added_sugar_g", label: "Added sugar", unit: "g" },
  { name: "sodium_mg", label: "Sodium", unit: "mg" },
  { name: "saturated_fat_g", label: "Saturated fat", unit: "g" },
];

const nutrientUnitFields = {
  sugar_g: "sugar_unit",
  added_sugar_g: "added_sugar_unit",
  sodium_mg: "sodium_unit",
  saturated_fat_g: "saturated_fat_unit",
};

const nutrientLabels = {
  total_sugar: "Total sugar",
  added_sugar: "Added sugar",
  sodium: "Sodium",
  saturated_fat: "Saturated fat",
};

function getApiErrorMessage(payload, status, action = "Label extraction") {
  if (Array.isArray(payload?.detail)) {
    return payload.detail
      .map((issue) => {
        const field = issue.loc?.at(-1);
        return field ? `${field}: ${issue.msg}` : issue.msg;
      })
      .join(" ");
  }

  if (typeof payload?.detail === "string") {
    return payload.detail.slice(0, 500);
  }
  return `${action} failed (HTTP ${status}).`;
}

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "Not found";
  return String(value);
}

function getConcernClass(item) {
  if (item.needs_review) return "concern-review";
  if (String(item.concern_level ?? "").startsWith("Established hazard")) {
    return "concern-established";
  }
  if (item.concern_level === "Context-dependent") return "concern-context";
  return "concern-neutral";
}

function formatBasis(basis) {
  return {
    per_serving: "per serving",
    per_100g: "per 100 g",
    per_100ml: "per 100 ml",
  }[basis] ?? "basis needs review";
}

function isAcceptedImage(file) {
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  return (
    ACCEPTED_TYPES.includes(file.type.toLowerCase()) ||
    (!file.type && ACCEPTED_EXTENSIONS.includes(extension))
  );
}

function prepareReviewData(data) {
  return {
    productName: data.product_name?.value ?? "",
    basis: data.basis ?? "",
    servingSize: data.serving_size_text ?? "",
    nutrients: Object.fromEntries(
      nutrientFields.map(({ name }) => [
        name,
        data.nutrients?.[name]?.value == null
          ? ""
          : String(data.nutrients[name].value),
      ])
    ),
    ingredientsText: data.ingredients_text ?? "",
    ingredients: Array.isArray(data.ingredients) ? data.ingredients : [],
    reviewRequiredFields: Array.isArray(data.review_required_fields)
      ? data.review_required_fields
      : [],
    ocrText: typeof data.ocr_text === "string" ? data.ocr_text : "",
  };
}

function App() {
  const [selectedImage, setSelectedImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [extraction, setExtraction] = useState(null);
  const [review, setReview] = useState(null);
  const [uploadError, setUploadError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [analysisValues, setAnalysisValues] = useState({
    sugar_g: "",
    added_sugar_g: "",
    sodium_mg: "",
    saturated_fat_g: "",
  });
  const [analysisBasis, setAnalysisBasis] = useState("");
  const [analysisServingSize, setAnalysisServingSize] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState("");
  const [confirmedLabel, setConfirmedLabel] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const evidenceConcerns =
    analysisResult?.ingredient_analysis?.evidence_concerns ?? [];
  const fileInputRef = useRef(null);
  const previewUrlRef = useRef("");
  const resultSectionRef = useRef(null);
  const analysisRequestIdRef = useRef(0);

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

  useEffect(() => {
    if (!analysisResult) return;
    resultSectionRef.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
      block: "start",
    });
  }, [analysisResult]);

  function setImagePreview(file) {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = "";
    }
    setSelectedImage(file);
    if (file) {
      const imageUrl = URL.createObjectURL(file);
      previewUrlRef.current = imageUrl;
      setPreviewUrl(imageUrl);
    } else {
      setPreviewUrl("");
    }
  }

  function invalidateAnalysis() {
    analysisRequestIdRef.current += 1;
    setAnalysisResult(null);
    setAnalysisError("");
    setIsAnalyzing(false);
  }

  function selectImage(file) {
    setUploadError("");
    setExtraction(null);
    setReview(null);
    setIsConfirmed(false);
    invalidateAnalysis();
    setConfirmedLabel(null);

    if (!file) return;
    if (!isAcceptedImage(file)) {
      setImagePreview(null);
      setUploadError("Choose a JPEG, PNG, or WebP image.");
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setImagePreview(null);
      setUploadError("Image must be 10 MiB or smaller.");
      return;
    }

    setImagePreview(file);
  }

  async function extractLabel(event) {
    event.preventDefault();
    if (!selectedImage || isUploading) return;

    setUploadError("");
    setExtraction(null);
    setReview(null);
    setIsConfirmed(false);
    setConfirmedLabel(null);
    invalidateAnalysis();
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedImage);
      const response = await fetch(`${API_BASE_URL}/extract/label`, {
        method: "POST",
        body: formData,
      });

      let responseData;
      try {
        responseData = await response.json();
      } catch {
        throw new Error(
          response.ok
            ? "The backend returned an unreadable response."
            : `Label extraction failed (HTTP ${response.status}).`
        );
      }

      if (!response.ok) {
        throw new Error(getApiErrorMessage(responseData, response.status));
      }
      if (!responseData || typeof responseData !== "object") {
        throw new Error("The backend returned an invalid extraction response.");
      }

      const preparedData = prepareReviewData(responseData);
      setExtraction(responseData);
      setReview(preparedData);
    } catch (error) {
      setUploadError(
        error instanceof TypeError
          ? `Could not connect to the Label Lens API at ${API_BASE_URL}. Check that the backend is running and the API URL is correct.`
          : error.message
      );
    } finally {
      setIsUploading(false);
    }
  }

  function updateReview(field, value) {
    setIsConfirmed(false);
    setConfirmedLabel(null);
    invalidateAnalysis();
    setReview((current) => ({ ...current, [field]: value }));
  }

  function updateNutrient(name, value) {
    setIsConfirmed(false);
    setConfirmedLabel(null);
    invalidateAnalysis();
    setReview((current) => ({
      ...current,
      nutrients: { ...current.nutrients, [name]: value },
    }));
  }

  function confirmReview(event) {
    event.preventDefault();
    const nextValues = { ...review.nutrients };

    for (const field of nutrientFields) {
      if (nextValues[field.name].trim() === "") {
        continue;
      }
      const value = Number(nextValues[field.name]);
      if (!Number.isFinite(value) || value < 0) {
        setUploadError(`${field.label} must be a non-negative number.`);
        setIsConfirmed(false);
        return;
      }
    }

    setUploadError("");
    setAnalysisValues(nextValues);
    setAnalysisBasis(review.basis);
    setAnalysisServingSize(review.servingSize);
    const snapshot = {
      nutrients: nextValues,
      basis: review.basis,
      servingSize: review.servingSize,
      ingredientsText: review.ingredientsText,
    };
    setConfirmedLabel(snapshot);
    setIsConfirmed(true);
    void submitAnalysis(null, snapshot);
  }

  async function submitAnalysis(event, labelSnapshot = null) {
    event?.preventDefault();
    const requestId = ++analysisRequestIdRef.current;
    setAnalysisError("");
    setAnalysisResult(null);
    setIsAnalyzing(false);

    const valuesSnapshot = labelSnapshot ?? confirmedLabel;
    if (extraction && !valuesSnapshot) {
      setAnalysisError(
        "Review and confirm the extracted label details before analyzing them."
      );
      return;
    }

    const valuesToAnalyze = valuesSnapshot?.nutrients ?? analysisValues;
    const payload = {
      basis: (valuesSnapshot?.basis ?? analysisBasis) || null,
      serving_size_text:
        (valuesSnapshot?.servingSize ?? analysisServingSize).trim() || null,
      ingredients_text:
        valuesSnapshot?.ingredientsText.trim() || null,
    };
    for (const field of nutrientFields) {
      const rawValue = valuesToAnalyze[field.name].trim();
      payload[nutrientUnitFields[field.name]] = field.unit;
      if (rawValue === "") {
        payload[field.name] = null;
        continue;
      }
      const value = Number(rawValue);
      if (!Number.isFinite(value) || value < 0) {
        setAnalysisError(`${field.label} must be a non-negative number.`);
        return;
      }
      payload[field.name] = value;
    }

    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API_BASE_URL}/analyze/label`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      let responseData;
      try {
        responseData = await response.json();
      } catch {
        throw new Error(
          response.ok
            ? "The backend returned an unreadable response."
            : `The analysis request failed (HTTP ${response.status}).`
        );
      }
      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(responseData, response.status, "Label analysis")
        );
      }
      if (analysisRequestIdRef.current === requestId) {
        setAnalysisResult(responseData);
      }
    } catch (error) {
      if (analysisRequestIdRef.current === requestId) {
        setAnalysisError(
          error instanceof TypeError
            ? `Could not connect to the Label Lens API at ${API_BASE_URL}. Check that the backend is running and the API URL is correct.`
            : error.message
        );
      }
    } finally {
      if (analysisRequestIdRef.current === requestId) {
        setIsAnalyzing(false);
      }
    }
  }

  function updateAnalysisValue(event) {
    const { name, value } = event.target;
    setAnalysisValues((current) => ({ ...current, [name]: value }));
    invalidateAnalysis();
  }

  function updateAnalysisBasis(value) {
    setAnalysisBasis(value);
    invalidateAnalysis();
  }

  function updateAnalysisServingSize(value) {
    setAnalysisServingSize(value);
    invalidateAnalysis();
  }

  return (
    <main className="app-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Label Lens home">
          <span className="brand-mark" aria-hidden="true">LL</span>
          <span>Label Lens</span>
        </a>
        <span className="header-tag">Nutrition, made clearer</span>
      </header>

      <section className="intro">
        <p className="eyebrow">A clearer look at your food</p>
        <h1>From label photo<br className="desktop-break" /> to understanding.</h1>
        <p className="intro-copy">
          Upload a packaged-food label. Review and correct what Label Lens
          extracts before using the nutrition values.
        </p>
      </section>

      <section className="upload-layout" aria-label="Label image extraction">
        <form className="analysis-card upload-card" onSubmit={extractLabel}>
          <div className="card-heading">
            <div>
              <p className="step-label">STEP 1 · UPLOAD</p>
              <h2>Choose a label image</h2>
            </div>
            <span className="optional-label">JPEG · PNG · WebP</span>
          </div>

          <input
            ref={fileInputRef}
            className="visually-hidden"
            type="file"
            accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
            onChange={(event) => selectImage(event.target.files?.[0])}
          />
          {selectedImage ? (
            <div className="selected-image">
              <img src={previewUrl} alt="Selected nutrition label preview" />
              <div className="selected-image-info">
                <strong>{selectedImage.name}</strong>
                <span>
                  {(selectedImage.size / (1024 * 1024)).toFixed(2)} MiB · Ready
                  to extract
                </span>
                <button
                  className="text-button"
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Replace image
                </button>
              </div>
            </div>
          ) : (
            <button
              className="dropzone"
              type="button"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                selectImage(event.dataTransfer.files?.[0]);
              }}
              aria-label="Choose or drop a label image"
            >
              <span className="upload-icon" aria-hidden="true">
                <svg viewBox="0 0 48 48" fill="none">
                  <path d="M24 31V10m0 0-8 8m8-8 8 8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M11 29v7a3 3 0 0 0 3 3h20a3 3 0 0 0 3-3v-7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
                </svg>
              </span>
              <strong>Drop your label image here</strong>
              <span>or choose a file from your device</span>
              <small>JPEG, PNG or WebP · Up to 10 MiB</small>
            </button>
          )}

          {uploadError && (
            <p className="form-error" role="alert">
              <span aria-hidden="true">!</span>
              {uploadError}
            </p>
          )}

          <button
            className="submit-button"
            type="submit"
            disabled={!selectedImage || isUploading}
          >
            {isUploading ? (
              <>
                <span className="spinner" aria-hidden="true" />
                Reading label…
              </>
            ) : (
              <>
                Extract label details
                <span aria-hidden="true">→</span>
              </>
            )}
          </button>
          <p className="form-footnote">
            Image is processed by your configured Label Lens backend.
          </p>
        </form>

        <aside className="upload-note">
          <span className="note-icon" aria-hidden="true">✳</span>
          <p className="step-label">A NOTE ON EXTRACTION</p>
          <h2>Check every value.</h2>
          <p>
            Text recognition can misread small print, columns, or colors.
            Extracted details are suggestions for your review, not verified
            label data.
          </p>
          <div className="review-legend">
            <span className="review-dot" aria-hidden="true" />
            <span>Every extracted field needs your review</span>
          </div>
        </aside>
      </section>

      {extraction && review && (
        <section className="review-section" aria-labelledby="review-title">
          <div className="section-heading">
            <div>
              <p className="step-label">STEP 2 · REVIEW</p>
              <h2 id="review-title">Review extracted details</h2>
              <p>Correct anything that doesn’t match the package.</p>
            </div>
            <span className="review-status">
              <span aria-hidden="true">!</span> Needs review
            </span>
          </div>

          <form className="review-card" onSubmit={confirmReview}>
            <div className="review-grid">
              <label className="review-field">
                <span>Product name</span>
                <input
                  type="text"
                  value={review.productName}
                  placeholder="Not found on label"
                  onChange={(event) =>
                    updateReview("productName", event.target.value)
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
                    updateReview("servingSize", event.target.value)
                  }
                />
                <small>Extracted text · please verify</small>
              </label>

              <label className="review-field">
                <span>Nutrition values are listed</span>
                <select
                  value={review.basis}
                  onChange={(event) => updateReview("basis", event.target.value)}
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
                        updateNutrient(field.name, event.target.value)
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
                    updateReview("ingredientsText", event.target.value)
                  }
                />
                <small>Extracted text · please verify</small>
              </label>
            </div>

            <div className="ingredients-list">
              <span className="input-label">Recognized ingredient items</span>
              {review.ingredients.length > 0 ? (
                <div className="ingredient-chips">
                  {review.ingredients.map((ingredient, index) => (
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

            <button
              className="submit-button confirm-button"
              type="submit"
              disabled={isAnalyzing}
            >
              {isAnalyzing
                ? "Analyzing label…"
                : analysisError
                  ? "Retry analysis"
                  : "Confirm reviewed values"}
              {!isAnalyzing && <span aria-hidden="true">→</span>}
            </button>
            {isConfirmed && (
              <p className="success-message" role="status">
                {isAnalyzing
                  ? "Review confirmed. Analyzing the reviewed values…"
                  : analysisError
                    ? "Review confirmed. Analysis failed; use the button above to retry."
                    : analysisResult
                      ? "Review confirmed and analysis is complete."
                      : "Review confirmed. Analysis is starting…"}
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
      )}

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
        <form className="analysis-card" onSubmit={submitAnalysis} noValidate>
          <fieldset className="basis-fieldset">
            <legend>Values are listed</legend>
            <div className="basis-options">
              <label className={analysisBasis === "per_serving" ? "selected" : ""}>
                <input
                  type="radio"
                  name="analysisBasis"
                  value="per_serving"
                  checked={analysisBasis === "per_serving"}
                  disabled={Boolean(extraction)}
                  onChange={() => updateAnalysisBasis("per_serving")}
                />
                <span>Per serving</span>
              </label>
              <label className={analysisBasis === "per_100g" ? "selected" : ""}>
                <input
                  type="radio"
                  name="analysisBasis"
                  value="per_100g"
                  checked={analysisBasis === "per_100g"}
                  disabled={Boolean(extraction)}
                  onChange={() => updateAnalysisBasis("per_100g")}
                />
                <span>Per 100 g</span>
              </label>
              <label className={analysisBasis === "per_100ml" ? "selected" : ""}>
                <input
                  type="radio"
                  name="analysisBasis"
                  value="per_100ml"
                  checked={analysisBasis === "per_100ml"}
                  disabled={Boolean(extraction)}
                  onChange={() => updateAnalysisBasis("per_100ml")}
                />
                <span>Per 100 ml</span>
              </label>
              <label className={!analysisBasis ? "selected" : ""}>
                <input
                  type="radio"
                  name="analysisBasis"
                  value=""
                  checked={!analysisBasis}
                  disabled={Boolean(extraction)}
                  onChange={() => updateAnalysisBasis("")}
                />
                <span>Not established</span>
              </label>
            </div>
          </fieldset>
          <label className="input-group serving-size-input" htmlFor="analysis-serving-size">
            <span className="input-label">Serving size (needed for per-serving assessment)</span>
            <input
              id="analysis-serving-size"
              type="text"
              value={analysisServingSize}
              disabled={Boolean(extraction)}
              onChange={(event) => updateAnalysisServingSize(event.target.value)}
              placeholder="For example, 30 g"
            />
          </label>
          <div className="nutrient-inputs">
            {nutrientFields.map((field) => (
              <label className="input-group" htmlFor={`analysis-${field.name}`} key={field.name}>
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
                    onChange={updateAnalysisValue}
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
            <button
              className="submit-button"
              type="submit"
              disabled={isAnalyzing}
            >
              {isAnalyzing ? "Analyzing label…" : "Analyze label"}
              {!isAnalyzing && <span aria-hidden="true">→</span>}
            </button>
          )}
          {analysisResult && (
            <div
              ref={resultSectionRef}
              className="analysis-result"
              aria-live="polite"
              tabIndex="-1"
            >
              <section
                className="health-score-card"
                aria-labelledby="health-score-title"
              >
                <div className="health-score-heading">
                  <div>
                    <p className="step-label">NUTRIENT SUMMARY</p>
                    <h3 id="health-score-title">
                      Experimental Label Lens Health Score
                    </h3>
                  </div>
                  {analysisResult.health_score?.status === "available" ? (
                    <div className="health-score-value">
                      <strong>{analysisResult.health_score.score}</strong>
                      <span>out of 100</span>
                    </div>
                  ) : (
                    <strong className="health-score-unavailable">
                      Score unavailable
                    </strong>
                  )}
                </div>
                {analysisResult.health_score?.status === "available" && (
                  <div
                    className="health-score-progress"
                    role="progressbar"
                    aria-label="Experimental Label Lens Health Score"
                    aria-valuemin="0"
                    aria-valuemax="100"
                    aria-valuenow={analysisResult.health_score.score}
                    aria-valuetext={`${analysisResult.health_score.score} out of 100`}
                  >
                    <span
                      style={{
                        width: `${analysisResult.health_score.score}%`,
                      }}
                    />
                  </div>
                )}
                <p className="score-completeness">
                  {analysisResult.health_score?.data_completeness?.text ??
                    "Nutrient completeness unavailable"}
                </p>
                {analysisResult.health_score?.status === "available" ? (
                  <p className="score-explanation">
                    {analysisResult.health_score.explanation}
                  </p>
                ) : (
                  <p className="score-unavailable-reason" role="status">
                    {analysisResult.health_score?.explanation ??
                      "The backend did not return a health-score assessment."}
                  </p>
                )}
                {analysisResult.health_score?.factors?.length > 0 && (
                  <ul className="score-factor-list">
                    {analysisResult.health_score.factors.map((factor) => (
                      <li key={factor.category}>{factor.explanation}</li>
                    ))}
                  </ul>
                )}
                <p className="health-score-disclaimer">
                  Experimental Label Lens Health Score — not an official
                  health grade or medical assessment. This prototype formula
                  is not a validated measure of overall health. Ingredient
                  flags are separate and do not affect this score.
                </p>
              </section>
              <h3>Excess Nutrient Detection</h3>
              <p className="percentage-context">
                Statuses compare label values with configurable Label Lens
                project references, not official health grades.
              </p>
              <div className="result-list nutrient-assessments">
                {analysisResult.excess_nutrients?.map((nutrient) => (
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
                        className={`level-badge ${nutrient.needs_review ? "level-unknown" : `level-${nutrient.status.toLowerCase().replaceAll(" ", "-")}`}`}
                      >
                        {nutrient.status}
                      </span>
                    </div>
                    {nutrient.equivalent_value != null && (
                      <p className="converted-equivalent">
                        Serving-size equivalent: {nutrient.equivalent_value}{" "}
                        {nutrient.unit} {formatBasis(nutrient.equivalent_basis)}
                        {" "}· calculated, not separately listed on the label
                      </p>
                    )}
                    <p className="assessment-explanation">
                      {nutrient.explanation}
                    </p>
                    {nutrient.threshold_explanation && (
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
                ))}
              </div>
              <section className="ingredient-analysis" aria-labelledby="ingredient-analysis-title">
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
                      <li className="ingredient-insight" key={`${item.ingredient}-${index}`}>
                        <div className="ingredient-insight-heading">
                          <strong>{item.matched_name ?? item.ingredient}</strong>
                          <span className={`concern-badge ${getConcernClass(item)}`}>
                            {item.concern_level}
                          </span>
                        </div>
                        {item.matched_name &&
                          item.matched_name !== item.ingredient && (
                          <p className="ingredient-raw-name">Label text: {item.ingredient}</p>
                        )}
                        <p>{item.explanation}</p>
                        {item.evidence_source && (
                          <p className="evidence-reference">
                            Source:{" "}
                            {item.source_url ? (
                              <a href={item.source_url} target="_blank" rel="noreferrer">
                                {item.evidence_source}
                              </a>
                            ) : item.evidence_source}
                          </p>
                        )}
                        {item.evidence_context && (
                          <p className="evidence-context">
                            Evidence context: {item.evidence_context}
                          </p>
                        )}
                        {item.needs_review && (
                          <p className="review-indicator">Review this ingredient text; the match is uncertain.</p>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <>
                    <p className="muted-copy">
                      No evidence-based ingredient concerns identified from
                      the ingredients we could assess.
                    </p>
                    <p className="evidence-context">
                      This does not guarantee that the product is risk-free.
                      Some ingredients may be unassessed or have insufficient
                      evidence in the current knowledge base.
                    </p>
                  </>
                )}
              </section>
              <p className="disclaimer">{analysisResult.note}</p>
            </div>
          )}
        </form>
      </section>

      <footer className="page-footer">
        <span>Label Lens</span>
        <span>Extracted label data always needs your review.</span>
      </footer>
    </main>
  );
}

export default App;
