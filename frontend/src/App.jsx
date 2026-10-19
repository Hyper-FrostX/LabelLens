import { useState } from "react";
import "./App.css";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const nutrientFields = [
  { name: "sugar_g", label: "Sugar", unit: "g", description: "Total sugars" },
  { name: "sodium_mg", label: "Sodium", unit: "mg", description: "Sodium per amount" },
  {
    name: "saturated_fat_g",
    label: "Saturated fat",
    unit: "g",
    description: "Saturated fat",
  },
];

function formatValue(value) {
  if (value === null || value === undefined) return "Not provided";
  return `${Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 2,
  })}`;
}

function getApiErrorMessage(payload, status) {
  if (Array.isArray(payload?.detail)) {
    return payload.detail
      .map((issue) => {
        const field = issue.loc?.at(-1);
        return field ? `${field}: ${issue.msg}` : issue.msg;
      })
      .join(" ");
  }

  if (typeof payload?.detail === "string") return payload.detail;
  return `The analysis request failed (HTTP ${status}).`;
}

function App() {
  const [values, setValues] = useState({
    sugar_g: "",
    sodium_mg: "",
    saturated_fat_g: "",
  });
  const [basis, setBasis] = useState("per_serving");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  function updateValue(event) {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value }));
  }

  async function submitAnalysis(event) {
    event.preventDefault();
    setError("");
    setResult(null);

    const payload = { basis };
    let hasValue = false;

    for (const field of nutrientFields) {
      const rawValue = values[field.name].trim();
      if (rawValue === "") {
        payload[field.name] = null;
        continue;
      }

      const numberValue = Number(rawValue);
      if (!Number.isFinite(numberValue)) {
        setError(`${field.label} must be a finite number.`);
        return;
      }
      if (numberValue < 0) {
        setError(`${field.label} cannot be negative.`);
        return;
      }

      payload[field.name] = numberValue;
      hasValue = true;
    }

    if (!hasValue) {
      setError("Enter at least one nutrient amount to analyze.");
      return;
    }

    setIsLoading(true);
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
            : `The request failed (HTTP ${response.status}).`
        );
      }

      if (!response.ok) {
        throw new Error(getApiErrorMessage(responseData, response.status));
      }

      setResult(responseData);
    } catch (requestError) {
      setError(
        requestError instanceof TypeError
          ? `Could not connect to the Label Lens API at ${API_BASE_URL}. Check that the backend is running and the API URL is correct.`
          : requestError.message
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Label Lens home">
          <span className="brand-mark" aria-hidden="true">
            LL
          </span>
          <span>Label Lens</span>
        </a>
        <span className="header-tag">Nutrition, made clearer</span>
      </header>

      <section className="intro">
        <p className="eyebrow">A clearer look at your food</p>
        <h1>Know what’s in<br className="desktop-break" /> your serving.</h1>
        <p className="intro-copy">
          Enter the nutrition values from a food label to see how they compare
          with Label Lens’ project reference values.
        </p>
      </section>

      <section className="analysis-layout" aria-label="Nutrition analysis">
        <form className="analysis-card" onSubmit={submitAnalysis} noValidate>
          <div className="card-heading">
            <div>
              <p className="step-label">NUTRITION DETAILS</p>
              <h2>Enter label values</h2>
            </div>
            <span className="optional-label">Values can be left blank</span>
          </div>

          <fieldset className="basis-fieldset">
            <legend>Values are listed</legend>
            <div className="basis-options">
              <label className={basis === "per_serving" ? "selected" : ""}>
                <input
                  type="radio"
                  name="basis"
                  value="per_serving"
                  checked={basis === "per_serving"}
                  onChange={() => setBasis("per_serving")}
                />
                <span>Per serving</span>
              </label>
              <label className={basis === "per_100g" ? "selected" : ""}>
                <input
                  type="radio"
                  name="basis"
                  value="per_100g"
                  checked={basis === "per_100g"}
                  onChange={() => setBasis("per_100g")}
                />
                <span>Per 100 g</span>
              </label>
            </div>
          </fieldset>

          <div className="nutrient-inputs">
            {nutrientFields.map((field) => (
              <label className="input-group" htmlFor={field.name} key={field.name}>
                <span className="input-label">{field.label}</span>
                <span className="input-description">{field.description}</span>
                <span className="number-input">
                  <input
                    id={field.name}
                    name={field.name}
                    type="number"
                    min="0"
                    step="any"
                    inputMode="decimal"
                    placeholder="e.g. 0"
                    value={values[field.name]}
                    onChange={updateValue}
                    aria-label={`${field.label} in ${field.unit}`}
                  />
                  <span>{field.unit}</span>
                </span>
              </label>
            ))}
          </div>

          {error && (
            <p className="form-error" role="alert">
              <span aria-hidden="true">!</span>
              {error}
            </p>
          )}

          <button className="submit-button" type="submit" disabled={isLoading}>
            {isLoading ? (
              <>
                <span className="spinner" aria-hidden="true" />
                Analyzing…
              </>
            ) : (
              <>
                Analyze nutrition
                <span aria-hidden="true">→</span>
              </>
            )}
          </button>
          <p className="form-footnote">
            You can enter one or more values. No label image is uploaded.
          </p>
        </form>

        <aside className="results-card" aria-live="polite">
          {result ? (
            <div className="results-content">
              <p className="step-label">YOUR BREAKDOWN</p>
              <h2>Nutrition snapshot</h2>
              <p className="percentage-context">{result.percentage_context}</p>

              <div className="result-list">
                {nutrientFields.map((field) => {
                  const nutrientKey = field.name.replace(/_g$|_mg$/, "");
                  const resultKey =
                    nutrientKey === "saturated_fat"
                      ? "saturated_fat"
                      : nutrientKey;
                  const nutrient = result.nutrients?.[resultKey];
                  if (!nutrient) return null;

                  return (
                    <div className="result-row" key={field.name}>
                      <div className="result-main">
                        <div>
                          <span className="result-name">{field.label}</span>
                          <span className="result-value">
                            {formatValue(nutrient.value)}{" "}
                            {nutrient.value === null ? "" : field.unit}
                          </span>
                        </div>
                        <span
                          className={`level-badge level-${nutrient.level}`}
                        >
                          {nutrient.level}
                        </span>
                      </div>
                      <div className="percentage-line">
                        <span>Daily-reference contribution</span>
                        <strong>
                          {nutrient.percentage_of_daily_limit === null
                            ? "—"
                            : `${formatValue(
                                nutrient.percentage_of_daily_limit
                              )}%`}
                        </strong>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="sugar-callout">
                <span className="sugar-icon" aria-hidden="true">
                  ✳
                </span>
                <div>
                  <span>Approximate sugar</span>
                  <strong>
                    {result.sugar_teaspoons === null
                      ? "Not provided"
                      : `${formatValue(result.sugar_teaspoons)} tsp`}
                  </strong>
                </div>
              </div>

              <p className="disclaimer">{result.note}</p>
            </div>
          ) : (
            <div className="empty-results">
              <span className="empty-icon" aria-hidden="true">
                <svg viewBox="0 0 48 48" fill="none">
                  <rect
                    x="8"
                    y="7"
                    width="32"
                    height="36"
                    rx="8"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <path
                    d="M17 18h14M17 25h8M17 32h5"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                  <circle cx="33" cy="33" r="7" fill="currentColor" />
                  <path
                    d="m31 33 1.4 1.4L35 31.8"
                    stroke="white"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
              <h2>Your results will appear here</h2>
              <p>
                Add the values shown on your nutrition label and choose whether
                they’re listed per serving or per 100 g.
              </p>
              <span className="basis-hint">
                {basis === "per_serving"
                  ? "Percentages will describe one reported serving."
                  : "Percentages will describe 100 g of the product."}
              </span>
            </div>
          )}
        </aside>
      </section>

      <footer className="page-footer">
        <span>Label Lens</span>
        <span>Informational nutrition references, not a health grade.</span>
      </footer>
    </main>
  );
}

export default App;
