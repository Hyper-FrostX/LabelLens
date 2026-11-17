const MAX_CONTEXT_CHARS = 45_000;

function asRecord(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function compactValue(value, options = {}, depth = 0) {
  const {
    maxDepth = 5,
    maxEntries = 16,
    maxItems = 8,
    maxText = 200,
  } = options;
  if (typeof value === "string") return value.slice(0, maxText);
  if (value == null || typeof value === "boolean" || typeof value === "number") {
    return value;
  }
  if (depth >= maxDepth) return "[details omitted]";
  if (Array.isArray(value)) {
    return value
      .slice(0, maxItems)
      .map((item) => compactValue(item, options, depth + 1));
  }
  if (typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .slice(0, maxEntries)
        .map(([key, item]) => [
          key.slice(0, 80),
          compactValue(item, options, depth + 1),
        ])
    );
  }
  return null;
}

function limitText(value, maxLength) {
  return typeof value === "string" ? value.slice(0, maxLength) : value;
}

function buildQuestionContext(input, report, options) {
  const extraction = asRecord(input.extraction_metadata);
  const ingredients = asRecord(report.ingredients);
  const foodIntelligence = asRecord(report.food_intelligence);
  const nutritionIntelligence = asRecord(foodIntelligence.nutrition);
  const allergenAnalysis = asRecord(report.allergen_analysis);
  const compliance = asRecord(report.compliance_report);

  const inputContext = {
    product_name: limitText(input.product_name, 200),
    product_category: limitText(input.product_category, 120),
    basis: input.basis,
    serving_size_text: limitText(input.serving_size_text, 100),
    recommendation_goal: input.recommendation_goal,
    ingredients_text: limitText(input.ingredients_text, 2_000),
    allergens: compactValue(input.allergens, options),
    may_contain: compactValue(input.may_contain, options),
    label_text: limitText(input.label_text, 2_000),
    corrections_confirmed: Boolean(input.corrections_confirmed),
    symbol_review: input.symbol_review,
    label_corrections: compactValue(
      {
        product_name: asRecord(input.label_corrections).product_name,
        ingredients_text: asRecord(input.label_corrections).ingredients_text,
        nutrients: asRecord(input.label_corrections).nutrients,
        symbol_review: asRecord(input.label_corrections).symbol_review,
      },
      options
    ),
    extraction_metadata: {
      fields: Array.isArray(extraction.fields)
        ? extraction.fields.slice(0, 20).map((field) => {
            const entry = asRecord(field);
            return {
              field_name: entry.field_name,
              confidence_state: entry.confidence_state,
              review_status: entry.review_status,
              processing_method: entry.processing_method,
              ocr_confidence: entry.ocr_confidence,
              source_region: compactValue(entry.source_region, options),
            };
          })
        : [],
    },
    additional_nutrients: compactValue(input.additional_nutrients, options),
    sugar_g: input.sugar_g,
    sugar_unit: input.sugar_unit,
    added_sugar_g: input.added_sugar_g,
    added_sugar_unit: input.added_sugar_unit,
    sodium_mg: input.sodium_mg,
    sodium_unit: input.sodium_unit,
    saturated_fat_g: input.saturated_fat_g,
    saturated_fat_unit: input.saturated_fat_unit,
  };
  const reportContext = {
    product: compactValue(report.product, options),
    nutrition: compactValue(report.nutrition, options),
    food_intelligence: {
      nutrition: compactValue(
        {
          reported_basis: nutritionIntelligence.reported_basis,
          normalized_basis: nutritionIntelligence.normalized_basis,
          nutrient_density_per_100:
            nutritionIntelligence.nutrient_density_per_100,
          per_serving: nutritionIntelligence.per_serving,
          observations: nutritionIntelligence.observations,
          missing_or_unusable_fields:
            nutritionIntelligence.missing_or_unusable_fields,
        },
        options
      ),
      scores: compactValue(foodIntelligence.scores, options),
      personal_suitability: compactValue(
        foodIntelligence.personal_suitability,
        options
      ),
    },
    ingredients: {
      text: limitText(ingredients.text, 2_000),
      analysis: compactValue(ingredients.analysis, options),
      additive_analysis: compactValue(ingredients.additive_analysis, options),
      verification_statuses: compactValue(
        ingredients.verification_statuses,
        options
      ),
    },
    allergen_analysis: compactValue(allergenAnalysis, options),
    personalized_suitability: compactValue(
      report.personalized_suitability,
      options
    ),
    alternatives: compactValue(report.alternatives, options),
    completeness: compactValue(report.completeness, options),
    compliance_report: compactValue(
      {
        overall_status: compliance.overall_status,
        legal_compliance_determination:
          compliance.legal_compliance_determination,
        mandatory_declarations: compliance.mandatory_declarations,
        manual_review_requirements: compliance.manual_review_requirements,
        fssai_license_information: compliance.fssai_license_information,
      },
      options
    ),
  };
  return { ...inputContext, ...reportContext };
}

export function buildProductQuestionContext(inputValue, reportValue) {
  const input = asRecord(inputValue);
  const report = asRecord(reportValue);
  const context = buildQuestionContext(input, report);
  if (JSON.stringify(context).length <= MAX_CONTEXT_CHARS) return context;

  const reducedContext = buildQuestionContext(input, report, {
    maxDepth: 3,
    maxEntries: 6,
    maxItems: 3,
    maxText: 120,
  });
  if (JSON.stringify(reducedContext).length <= MAX_CONTEXT_CHARS) {
    return reducedContext;
  }

  return {
    product_name: limitText(input.product_name, 200),
    basis: input.basis,
    ingredients_text: limitText(input.ingredients_text, 500),
    label_text: limitText(input.label_text, 500),
    sugar_g: input.sugar_g,
    added_sugar_g: input.added_sugar_g,
    sodium_mg: input.sodium_mg,
    saturated_fat_g: input.saturated_fat_g,
    product: compactValue(report.product, {
      maxDepth: 1,
      maxEntries: 2,
      maxItems: 0,
      maxText: 100,
    }),
    nutrition: compactValue(report.nutrition, {
      maxDepth: 2,
      maxEntries: 2,
      maxItems: 0,
      maxText: 100,
    }),
    ingredients: {
      text: limitText(asRecord(report.ingredients).text, 500),
    },
  };
}
