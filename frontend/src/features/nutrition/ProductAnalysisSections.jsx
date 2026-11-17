import { getSectionStatus } from "./productAnalysisUtils";
import LabelComplianceReport from "./LabelComplianceReport";
import FoodIntelligenceSections from "./FoodIntelligenceSections";

function labelFor(key) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function ValueList({ value, expertMode, depth = 0 }) {
  if (value == null || typeof value === "boolean" || typeof value === "number") {
    return <span>{value == null ? "Not provided" : String(value)}</span>;
  }
  if (typeof value === "string") return <span>{value || "Not provided"}</span>;
  if (Array.isArray(value)) {
    if (value.length === 0) return <span>No entries returned.</span>;
    if (value.every((item) => typeof item === "string" || typeof item === "number")) {
      return (
        <ul className="product-analysis-value-list">
          {value.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
        </ul>
      );
    }
    return (
      <ul className="product-analysis-value-list">
        {value.map((item, index) => (
          <li key={index}><ValueList value={item} expertMode={expertMode} depth={depth + 1} /></li>
        ))}
      </ul>
    );
  }
  if (depth >= 3) return <span>Additional detail returned.</span>;

  const entries = Object.entries(value).filter(([key, item]) =>
    item != null && (expertMode || !["evidence_context", "threshold_explanation"].includes(key))
  );
  if (entries.length === 0) return <span>No details returned.</span>;

  return (
    <dl className="product-analysis-data">
      {entries.map(([key, item]) => (
        <div key={key}>
          <dt>{labelFor(key)}</dt>
          <dd><ValueList value={item} expertMode={expertMode} depth={depth + 1} /></dd>
        </div>
      ))}
    </dl>
  );
}

function AnalysisSection({ title, data, expertMode, children }) {
  return (
    <section className="product-analysis-section">
      <div className="product-analysis-section-heading">
        <h3>{title}</h3>
        <span className="product-status" role="status">{getSectionStatus(data)}</span>
      </div>
      {children ?? (
        data == null
          ? <p className="muted-copy">This section was not returned by the backend.</p>
          : <ValueList value={data} expertMode={expertMode} />
      )}
    </section>
  );
}

export default function ProductAnalysisSections({ analysisResult, expertMode }) {
  const allergens = analysisResult.allergen_analysis;
  const limitations = analysisResult.limitations;
  const additionalNutrients = analysisResult.nutrition_analysis?.additional_nutrients ?? {};

  return (
    <div className="product-analysis-sections">
      <FoodIntelligenceSections
        intelligence={analysisResult.food_intelligence}
        expertMode={expertMode}
      />
      <LabelComplianceReport report={analysisResult.compliance_report} />
      <AnalysisSection
        title="Product overview"
        data={analysisResult.product_overview}
        expertMode={expertMode}
      />
      {Object.keys(additionalNutrients).length > 0 && (
        <AnalysisSection
          title="Additional nutrients"
          data={additionalNutrients}
          expertMode={expertMode}
        />
      )}
      <AnalysisSection
        title="Ingredient analysis"
        data={analysisResult.ingredient_analysis}
        expertMode={expertMode}
      />
      <AnalysisSection
        title="Additive analysis"
        data={analysisResult.additive_analysis}
        expertMode={expertMode}
      />
      <AnalysisSection
        title="Declared allergens"
        data={allergens?.declared ?? allergens?.declared_allergens}
        expertMode={expertMode}
      />
      <AnalysisSection
        title="Precautionary “may contain” allergens"
        data={allergens?.may_contain ?? allergens?.may_contain_allergens}
        expertMode={expertMode}
      />
      <AnalysisSection
        title="Personalized suitability"
        data={analysisResult.personalized_suitability}
        expertMode={expertMode}
      />
      <AnalysisSection
        title="Alternatives"
        data={analysisResult.alternatives}
        expertMode={expertMode}
      />
      <AnalysisSection
        title="Limitations"
        data={limitations}
        expertMode={expertMode}
      />
    </div>
  );
}
