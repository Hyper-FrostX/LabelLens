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
  { name: "sodium_mg", label: "Sodium", unit: "mg" },
  { name: "saturated_fat_g", label: "Saturated fat", unit: "g" },
];

function getApiErrorMessage(payload, status) {
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
  return `Label extraction failed (HTTP ${status}).`;
}

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "Not found";
  return String(value);
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
    sodium_mg: "",
    saturated_fat_g: "",
  });
  const [analysisBasis, setAnalysisBasis] = useState("per_serving");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const fileInputRef = useRef(null);
  const previewUrlRef = useRef("");

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

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

  function selectImage(file) {
    setUploadError("");
    setExtraction(null);
    setReview(null);
    setIsConfirmed(false);
    setAnalysisResult(null);

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
    setReview((current) => ({ ...current, [field]: value }));
  }

  function updateNutrient(name, value) {
    setIsConfirmed(false);
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
    if (review.basis) setAnalysisBasis(review.basis);
    setIsConfirmed(true);
  }

  async function submitAnalysis(event) {
    event.preventDefault();
    setAnalysisError("");
    setAnalysisResult(null);

    const payload = { basis: analysisBasis };
    let hasValue = false;
    for (const field of nutrientFields) {
      const rawValue = analysisValues[field.name].trim();
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
      hasValue = true;
    }
    if (!hasValue) {
      setAnalysisError("Enter at least one nutrient amount to analyze.");
      return;
    }

    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API_BASE_URL}/analyze/nutrition`, {
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
        throw new Error(getApiErrorMessage(responseData, response.status));
      }
      setAnalysisResult(responseData);
    } catch (error) {
      setAnalysisError(
        error instanceof TypeError
          ? `Could not connect to the Label Lens API at ${API_BASE_URL}. Check that the backend is running and the API URL is correct.`
          : error.message
      );
    } finally {
      setIsAnalyzing(false);
    }
  }

  function updateAnalysisValue(event) {
    const { name, value } = event.target;
    setAnalysisValues((current) => ({ ...current, [name]: value }));
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

            <button className="submit-button confirm-button" type="submit">
              Confirm reviewed values
              <span aria-hidden="true">→</span>
            </button>
            {isConfirmed && (
              <p className="success-message" role="status">
                Review confirmed. The values have been copied to the nutrition
                analysis form below.
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
                ? "Check the confirmed values, then run the existing analysis."
                : "Enter values manually, or upload and confirm a label above."}
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
                  onChange={() => setAnalysisBasis("per_serving")}
                />
                <span>Per serving</span>
              </label>
              <label className={analysisBasis === "per_100g" ? "selected" : ""}>
                <input
                  type="radio"
                  name="analysisBasis"
                  value="per_100g"
                  checked={analysisBasis === "per_100g"}
                  onChange={() => setAnalysisBasis("per_100g")}
                />
                <span>Per 100 g</span>
              </label>
            </div>
          </fieldset>
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
                    onChange={updateAnalysisValue}
                    placeholder="Leave blank if unknown"
                  />
                  <span>{field.unit}</span>
                </span>
              </label>
            ))}
          </div>
          {analysisError && (
            <p className="form-error" role="alert">
              <span aria-hidden="true">!</span>
              {analysisError}
            </p>
          )}
          <button className="submit-button" type="submit" disabled={isAnalyzing}>
            {isAnalyzing ? "Analyzing…" : "Analyze nutrition"}
            {!isAnalyzing && <span aria-hidden="true">→</span>}
          </button>
          {analysisResult && (
            <div className="analysis-result" aria-live="polite">
              <p className="percentage-context">
                {analysisResult.percentage_context}
              </p>
              <div className="result-list">
                {nutrientFields.map((field) => {
                  const resultKey =
                    field.name === "saturated_fat_g"
                      ? "saturated_fat"
                      : field.name.replace(/_g$|_mg$/, "");
                  const nutrient = analysisResult.nutrients?.[resultKey];
                  return nutrient ? (
                    <div className="result-row" key={field.name}>
                      <div className="result-main">
                        <div>
                          <span className="result-name">{field.label}</span>
                          <span className="result-value">
                            {formatValue(nutrient.value)}{" "}
                            {nutrient.value == null ? "" : field.unit}
                          </span>
                        </div>
                        <span className={`level-badge level-${nutrient.level}`}>
                          {nutrient.level}
                        </span>
                      </div>
                      <div className="percentage-line">
                        <span>Daily-reference contribution</span>
                        <strong>
                          {nutrient.percentage_of_daily_limit == null
                            ? "—"
                            : `${nutrient.percentage_of_daily_limit}%`}
                        </strong>
                      </div>
                    </div>
                  ) : null;
                })}
              </div>
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
