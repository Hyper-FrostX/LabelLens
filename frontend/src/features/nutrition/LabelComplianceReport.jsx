import { getComplianceStatusLabel } from "./productAnalysisUtils";

function Status({ value }) {
  const status = value || "NOT_EVALUATED";
  return (
    <span className={`compliance-status compliance-status-${status.toLowerCase()}`} role="status">
      {getComplianceStatusLabel(status)}
    </span>
  );
}

function Evidence({ text }) {
  if (!text) return null;
  return (
    <details className="compliance-evidence">
      <summary>View original OCR evidence</summary>
      <pre>{text}</pre>
    </details>
  );
}

function Finding({
  title,
  status,
  value,
  explanation,
  sourceText,
  originalValue,
  corrected = false,
}) {
  return (
    <li className="compliance-finding">
      <div className="compliance-finding-heading">
        <strong>{title}</strong>
        <Status value={status} />
      </div>
      {value != null && value !== "" && (
        <p className="compliance-value">
          {typeof value === "string" ? value : JSON.stringify(value)}
        </p>
      )}
      {corrected && (
        <p>
          User-confirmed final value. Original extracted value:{" "}
          {originalValue == null || originalValue === ""
            ? "Not detected"
            : typeof originalValue === "string"
              ? originalValue
              : JSON.stringify(originalValue)}
        </p>
      )}
      {explanation && <p>{explanation}</p>}
      <Evidence text={sourceText} />
    </li>
  );
}

function FindingsList({
  items,
  getTitle,
  getStatus,
  getValue,
  getExplanation,
  getSource,
  getOriginalValue,
  isCorrected,
}) {
  if (!items?.length) return <p className="muted-copy">No findings were returned.</p>;
  return (
    <ul className="compliance-findings">
      {items.map((item, index) => (
        <Finding
          key={`${getTitle(item)}-${index}`}
          title={getTitle(item)}
          status={getStatus(item)}
          value={getValue(item)}
          explanation={getExplanation(item)}
          sourceText={getSource(item)}
          originalValue={getOriginalValue?.(item)}
          corrected={isCorrected?.(item)}
        />
      ))}
    </ul>
  );
}

export default function LabelComplianceReport({ report }) {
  if (!report) return null;

  const license = report.fssai_license_information ?? {};
  const nutrition = report.nutrition_inspection ?? {};
  const dates = report.date_inspection?.dates ?? [];
  const allergens = report.allergen_inspection ?? {};
  const vegetarian = report.vegetarian_declaration ?? {};
  const imageExtraction = report.image_extraction ?? {};

  return (
    <section className="compliance-report" aria-labelledby="label-compliance-title">
      <header className="compliance-report-header">
        <div>
          <p className="step-label">LABEL INSPECTION</p>
          <h2 id="label-compliance-title">Indian food label inspection</h2>
        </div>
        <Status value={report.overall_status} />
      </header>
      <p className="compliance-disclaimer">
        OCR-based information inspection only. This report does not determine legal
        compliance, certify a product, verify a license, or establish product safety.
      </p>
      <div className="compliance-license">
        <h3>FSSAI license information</h3>
        <dl>
          <div>
            <dt>{license.correction_applied ? "User-confirmed number" : "OCR-extracted number"}</dt>
            <dd>{license.extracted_number ?? "Not detected"}</dd>
          </div>
          <div>
            <dt>Normalized number</dt>
            <dd>{license.normalized_number ?? "Not available"}</dd>
          </div>
          <div>
            <dt>14-digit format</dt>
            <dd>{license.format_valid == null ? "Not evaluated" : license.format_valid ? "Valid-looking format" : "Format not valid"}</dd>
          </div>
          <div>
            <dt>Official status</dt>
            <dd>{license.official_verification_status ?? "NOT_VERIFIED"}</dd>
          </div>
        </dl>
        <p>{license.explanation}</p>
        {license.correction_applied && (
          <p>Original OCR number: {license.original_ocr_number ?? "Not detected"}</p>
        )}
        <Evidence text={license.original_source_text ?? license.source_text} />
      </div>
      <div className="compliance-report-grid">
        <section>
          <h3>Label information detected</h3>
          <FindingsList
            items={report.mandatory_declarations}
            getTitle={(item) => item.field_name?.replaceAll("_", " ") ?? "Label field"}
            getStatus={(item) => item.validation_status}
            getValue={(item) => item.extracted_value}
            getExplanation={(item) => item.explanation}
            getSource={(item) => item.source_text}
            getOriginalValue={(item) => item.original_extracted_value}
            isCorrected={(item) => item.correction_applied}
          />
        </section>
        <section>
          <h3>Ingredient declaration</h3>
          <p>{report.ingredient_inspection?.explanation}</p>
          <p>
            Readable: {report.ingredient_inspection?.readable ? "Yes" : "No / not established"}
          </p>
          <p>
            Normalized items: {report.ingredient_inspection?.normalized_ingredients?.join(", ") || "Not available"}
          </p>
          <p>
            Additive identifiers: {report.ingredient_inspection?.additive_identifiers?.join(", ") || "None detected"}
          </p>
          <Evidence text={report.ingredient_inspection?.original_text} />
        </section>
        <section>
          <h3>Allergen declarations</h3>
          <p>{allergens.explanation}</p>
          <p>
            Explicit declarations: {allergens.explicit_allergen_declarations?.map((item) => item.value).join(", ") || "None detected"}
          </p>
          <p>
            Original OCR allergen declarations: {allergens.original_ocr_explicit_allergen_declarations?.join(", ") || "None detected"}
          </p>
          <p>
            May contain: {allergens.may_contain_declarations?.map((item) => item.value).join(", ") || "None detected"}
          </p>
          <p>
            Original OCR precautionary declarations: {allergens.original_ocr_may_contain_declarations?.join(", ") || "None detected"}
          </p>
          <FindingsList
            items={allergens.ingredient_text_matches}
            getTitle={(item) => `${item.allergen} ingredient-text match`}
            getStatus={() => "NEEDS_MANUAL_REVIEW"}
            getValue={(item) => item.matched_text}
            getExplanation={() => "Possible OCR-derived text match; not confirmed physical presence."}
            getSource={(item) => item.source_text}
          />
          {allergens.potential_conflicts?.map((item, index) => (
            <Finding
              key={`allergen-conflict-${index}`}
              title={item.allergen}
              status={item.classification}
              explanation={item.explanation}
              sourceText={item.ingredient_source_text}
            />
          ))}
        </section>
        <section>
          <h3>Nutrition panel</h3>
          <p>{nutrition.explanation}</p>
          <p>Basis: {nutrition.basis ?? "Not detected"}</p>
          <FindingsList
            items={nutrition.nutrients}
            getTitle={(item) => item.nutrient?.replaceAll("_", " ") ?? "Nutrient"}
            getStatus={(item) => item.classification}
            getValue={(item) => item.value == null ? null : `${item.value} ${item.unit ?? ""} ${item.basis ? `(${item.basis})` : ""}`}
            getExplanation={(item) => item.explanation}
            getSource={(item) => item.source_text}
            getOriginalValue={(item) => item.original_ocr_value}
            isCorrected={(item) => item.correction_applied}
          />
        </section>
        <section>
          <h3>Date and shelf-life markings</h3>
          <p>{report.date_inspection?.explanation}</p>
          <p>Shelf life inferred: No</p>
          <FindingsList
            items={dates}
            getTitle={(item) => item.date_type?.replaceAll("_", " ") ?? "Date"}
            getStatus={(item) => item.classification}
            getValue={(item) => item.normalized_date ?? item.raw_value}
            getExplanation={(item) => item.explanation}
            getSource={(item) => item.source_text}
          />
        </section>
        <section>
          <h3>Vegetarian / non-vegetarian declaration</h3>
          <Status value={vegetarian.status} />
          <p>Textual declaration: {vegetarian.declaration ?? "Not detected"}</p>
          <p>Symbol image inspected: {vegetarian.symbol_image_inspected ? "Yes — heuristic only" : "No"}</p>
          <p>Visual review status: {vegetarian.symbol_verification_status ?? "NOT_EVALUATED"}</p>
          {["vegetarian", "non_vegetarian"].map((kind) => {
            const symbol = vegetarian.image_symbol_detection?.[kind];
            return symbol ? (
              <p key={kind}>
                {kind.replaceAll("_", " ")} symbol: {symbol.status}
                {symbol.confidence_state && ` · ${symbol.confidence_state}`}
                {symbol.explanation && ` · ${symbol.explanation}`}
              </p>
            ) : null;
          })}
          {vegetarian.user_symbol_review && (
            <p>User visual review: {vegetarian.user_symbol_review}</p>
          )}
          <p>{vegetarian.explanation}</p>
          <Evidence text={vegetarian.source_text} />
        </section>
        <section>
          <h3>Potential inconsistencies</h3>
          <FindingsList
            items={report.potential_inconsistencies}
            getTitle={(item) => item.finding ?? item.allergen ?? "Potential inconsistency"}
            getStatus={(item) => item.classification}
            getValue={() => null}
            getExplanation={(item) => item.explanation}
            getSource={(item) => item.source_text}
          />
        </section>
        <section>
          <h3>Manual review</h3>
          <FindingsList
            items={report.manual_review_requirements}
            getTitle={(item) => item.field?.replaceAll("_", " ") ?? "Review item"}
            getStatus={(item) => item.classification}
            getValue={() => null}
            getExplanation={(item) => item.reason}
            getSource={(item) => item.source_text}
          />
        </section>
      </div>
      <details className="compliance-limitations">
        <summary>Image extraction confidence and regions</summary>
        {imageExtraction.processing && (
          <p>
            Selected processing: {imageExtraction.processing.selected_variant ?? "Not provided"}.
            {" "}OCR passes: {imageExtraction.processing.ocr_strategies_run ?? "Not provided"}.
            {" "}Skew correction: {imageExtraction.processing.skew_correction_degrees ?? "Not estimated"}°.
          </p>
        )}
        {imageExtraction.ocr_quality?.confidence_basis && (
          <p>{imageExtraction.ocr_quality.confidence_basis}</p>
        )}
        <ul className="compliance-findings">
          {(imageExtraction.fields ?? []).map((field, index) => (
            <li className="compliance-finding" key={`${field.field_name}-${index}`}>
              <strong>{field.field_name?.replaceAll("_", " ") ?? "Field"}</strong>
              <p>
                Value: {Object.prototype.hasOwnProperty.call(field, "extracted_value")
                  ? field.extracted_value == null
                    ? "Not detected"
                    : String(field.extracted_value)
                  : "Available in the original OCR review"}
                {" · "}{field.confidence_state ?? "NEEDS_MANUAL_REVIEW"}
                {typeof field.ocr_confidence === "number" && ` · Tesseract ${field.ocr_confidence.toFixed(0)} (uncalibrated)`}
              </p>
              {field.source_region && (
                <p>
                  Source region: {field.source_region.region_type} ·{" "}
                  {JSON.stringify(field.source_region.source_coordinates)}
                </p>
              )}
            </li>
          ))}
        </ul>
        <ul className="compliance-findings">
          {(imageExtraction.regions ?? []).map((region, index) => (
            <li className="compliance-finding" key={`${region.region_type}-${index}`}>
              <strong>{region.region_type?.replaceAll("_", " ") ?? "Label region"}</strong>
              <p>Source coordinates: {JSON.stringify(region.source_coordinates)}</p>
              <Evidence text={region.extracted_text} />
            </li>
          ))}
        </ul>
      </details>
      {report.corrections_applied && (
        <details className="compliance-limitations">
          <summary>User-confirmed values used for analysis</summary>
          <p>Original OCR text and extraction evidence remain unchanged and are shown separately.</p>
          <pre>{JSON.stringify(report.user_corrections?.values ?? {}, null, 2)}</pre>
        </details>
      )}
      <details className="compliance-regulatory">
        <summary>Regulatory rules and source references</summary>
        <ul className="compliance-findings">
          {(report.regulatory_rules ?? []).map((rule) => (
            <li className="compliance-finding" key={rule.rule_id}>
              <div className="compliance-finding-heading">
                <strong>{rule.rule_name}</strong>
                <Status value={rule.result_classification} />
              </div>
              <p>{rule.explanation}</p>
              <p>Applicability: {rule.applicability_status} — {rule.applicability_condition}</p>
              <Evidence text={rule.evidence} />
            </li>
          ))}
        </ul>
        <ul className="compliance-source-list">
          {(report.regulatory_sources ?? []).map((source) => (
            <li key={source.id}>
              <a href={source.source_url} target="_blank" rel="noreferrer">
                {source.title}
              </a>
              <span>{source.issuing_authority} · {source.source_version} · {source.verification_status}</span>
              <span>Reviewed {source.last_reviewed_date ?? "date not recorded"}</span>
            </li>
          ))}
        </ul>
      </details>
      <details className="compliance-limitations">
        <summary>OCR limitations</summary>
        <ul>
          {(report.ocr_limitations ?? []).map((limitation) => <li key={limitation}>{limitation}</li>)}
        </ul>
      </details>
    </section>
  );
}
