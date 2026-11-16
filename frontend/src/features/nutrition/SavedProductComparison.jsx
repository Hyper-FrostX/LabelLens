import { useState } from "react";

import Button from "../../components/ui/Button";
import { getApiErrorMessage } from "./nutritionUtils";
import {
  buildProductComparisonRequest,
  formatComparisonBasis,
  getComparisonRows,
} from "./comparisonUtils";

export default function SavedProductComparison({
  apiBaseUrl,
  accessToken,
  selectedIds,
}) {
  const [comparison, setComparison] = useState(null);
  const [recommendationGoal, setRecommendationGoal] = useState("balanced");
  const [error, setError] = useState("");
  const [isComparing, setIsComparing] = useState(false);

  async function compare(event) {
    event.preventDefault();
    setError("");
    setComparison(null);
    setIsComparing(true);
    try {
      const response = await fetch(`${apiBaseUrl}/scans/compare`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(
          buildProductComparisonRequest(selectedIds, recommendationGoal)
        ),
      });
      let payload;
      try {
        payload = await response.json();
      } catch {
        throw new Error(
          response.ok
            ? "The backend returned an unreadable comparison."
            : `Product comparison failed (HTTP ${response.status}).`
        );
      }
      if (!response.ok) {
        throw new Error(getApiErrorMessage(payload, response.status, "Product comparison"));
      }
      setComparison(payload);
    } catch (requestError) {
      setError(
        requestError instanceof TypeError
          ? `Could not connect to the Label Lens API at ${apiBaseUrl}.`
          : requestError.message
      );
    } finally {
      setIsComparing(false);
    }
  }

  return (
    <section className="saved-product-comparison" aria-labelledby="saved-comparison-title">
      <h3 id="saved-comparison-title">Compare saved products</h3>
      <p>Select 2–5 of your saved analyses. Only comparable reported values are shown.</p>
      <label className="input-group">
        <span className="input-label">Comparison goal</span>
        <select
          value={recommendationGoal}
          onChange={(event) => setRecommendationGoal(event.target.value)}
        >
          <option value="balanced">Balanced (no overall winner)</option>
          <option value="lower_sugar">Lower sugar</option>
          <option value="lower_sodium">Lower sodium</option>
          <option value="lower_saturated_fat">Lower saturated fat</option>
          <option value="higher_protein">Higher protein</option>
          <option value="higher_fiber">Higher fibre</option>
          <option value="lower_calories">Lower calories</option>
        </select>
      </label>
      <Button
        type="button"
        disabled={selectedIds.length < 2 || isComparing}
        onClick={compare}
      >
        {isComparing ? "Comparing…" : "Compare selected"}
      </Button>
      {error && <p className="form-error" role="alert">{error}</p>}
      {comparison && (
        <div className="saved-comparison-results" aria-live="polite">
          {comparison.status === "COMPARABLE" ? (
            <>
              <p>
                Normalized comparison basis: {formatComparisonBasis(comparison.comparison_basis)}.
                Values are descriptive; no overall winner is calculated.
              </p>
              <div className="comparison-table-scroll">
                <table>
                  <caption>Comparable label nutrient values</caption>
                  <thead>
                    <tr>
                      <th scope="col">Nutrient</th>
                      {comparison.products.map((product) => (
                        <th scope="col" key={product.scan_id}>
                          {product.product_name}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {getComparisonRows(comparison).map((item) => (
                      <tr key={item.key}>
                        <th scope="row">{item.label}</th>
                        {item.values.map((value) => (
                          <td key={value.scan_id}>
                            {value.value} {item.unit}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p role="status">
              Not enough compatible nutrient data for a like-for-like comparison.
              Product records are shown for transparency.
            </p>
          )}
          <div className="saved-comparison-product-details">
            {comparison.products.map((product) => (
              <article key={product.scan_id}>
                <h4>{product.product_name}</h4>
                <p>
                  Ingredient list: {product.ingredient_transparency?.ingredient_list ?? "not provided"}.
                  Declared allergens: {JSON.stringify(product.allergens?.declared ?? [])}.
                  May contain: {JSON.stringify(product.allergens?.may_contain ?? [])}.
                </p>
                <p>
                  Nutrition Quality: {product.indicators?.nutrition_quality?.score ?? "insufficient data"}.
                  Personal Suitability: {product.indicators?.personal_suitability?.status ?? "not evaluated"}.
                </p>
                {product.advantages?.length > 0 && (
                  <p><strong>Goal advantage:</strong> {product.advantages.map((item) => item.explanation).join(" ")}</p>
                )}
                {product.tradeoffs?.length > 0 && (
                  <p><strong>Goal trade-off:</strong> {product.tradeoffs.map((item) => item.explanation).join(" ")}</p>
                )}
                {product.data_completeness?.missing_nutrients?.length > 0 && (
                  <p>Missing nutrients: {product.data_completeness.missing_nutrients.join(", ")}.</p>
                )}
                <p className="muted-copy">{product.normalization}</p>
              </article>
            ))}
          </div>
          <ul>
            {comparison.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
          </ul>
        </div>
      )}
    </section>
  );
}
