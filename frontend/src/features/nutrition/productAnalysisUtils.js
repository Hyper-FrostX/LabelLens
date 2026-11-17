import {
  additionalNutrientFields,
  nutrientFields,
  nutrientUnitFields,
} from "./nutritionUtils.js";

export function buildLabelCorrections(review) {
  return {
    product_name: review.productName,
    basis: review.basis,
    serving_size_text: review.servingSize,
    ingredients_text: review.ingredientsText,
    allergens: review.declaredAllergenText,
    may_contain: review.mayContainText,
    nutrients: {
      ...review.nutrients,
      ...Object.fromEntries(
        Object.entries(review.additionalNutrients ?? {}).map(([name, entry]) => [
          name,
          entry.value,
        ])
      ),
    },
    other_fields: review.otherFields ?? {},
  };
}

export function getMayContainText(value) {
  if (Array.isArray(value)) return value.join(", ");
  return typeof value === "string" ? value : "";
}

function splitDeclarationText(text) {
  const items = getMayContainText(text)
    .split(/[,;\n]+/)
    .map((item) => item.trim())
    .filter(Boolean);
  return items.length ? items : null;
}

export function buildProductAnalysisPayload({
  productName,
  declaredAllergenText = "",
  ingredientsText,
  mayContainText,
  nutrients,
  additionalNutrients = {},
  basis,
  servingSize,
  explanationLevel,
  recommendationGoal = "balanced",
  saveToHistory = false,
  labelText = "",
  labelCorrections = {},
  correctionsConfirmed = false,
  extractionMetadata = null,
  symbolReview = null,
  productCategory = null,
}) {
  const payload = {
    product_name: productName.trim() || null,
    label_text: labelText.trim() || null,
    product_category: productCategory,
    label_corrections: labelCorrections,
    corrections_confirmed: Boolean(correctionsConfirmed),
    extraction_metadata: extractionMetadata,
    symbol_review: symbolReview || null,
    ingredients_text: ingredientsText.trim() || null,
    may_contain_text: mayContainText.trim() || null,
    allergens: splitDeclarationText(declaredAllergenText),
    may_contain: splitDeclarationText(mayContainText),
    basis: basis || null,
    units: Object.fromEntries(
      nutrientFields.map((field) => [field.name, field.unit])
    ),
    serving_size_text: servingSize.trim() || null,
    explanation_level: explanationLevel === "expert" ? "detailed" : "standard",
    recommendation_goal: recommendationGoal,
    save_to_history: Boolean(saveToHistory),
  };

  for (const field of nutrientFields) {
    const rawValue = nutrients?.[field.name]?.trim?.() ?? "";
    if (rawValue === "") {
      payload[field.name] = null;
      payload[nutrientUnitFields[field.name]] = field.unit;
      continue;
    }

    const value = Number(rawValue);
    if (!Number.isFinite(value) || value < 0) {
      throw new Error(`${field.label} must be a non-negative number.`);
    }
    payload[field.name] = value;
    payload[nutrientUnitFields[field.name]] = field.unit;
  }

  payload.additional_nutrients = {};
  for (const field of additionalNutrientFields) {
    const entry = additionalNutrients?.[field.name];
    const rawValue = typeof entry?.value === "string" ? entry.value.trim() : entry?.value;
    if (rawValue === "" || rawValue == null) continue;

    const value = Number(rawValue);
    if (!Number.isFinite(value) || value < 0) {
      throw new Error(`${field.label} must be a non-negative number.`);
    }

    payload.additional_nutrients[field.name] = {
      value,
      unit: entry?.unit || field.unit,
    };
  }

  return payload;
}

export function toLegacyLabelPayload(productPayload) {
  const legacyPayload = {
    basis: productPayload.basis,
    serving_size_text: productPayload.serving_size_text,
    ingredients_text: productPayload.ingredients_text,
  };

  for (const field of nutrientFields) {
    legacyPayload[field.name] = productPayload[field.name];
    legacyPayload[nutrientUnitFields[field.name]] =
      productPayload.units[field.name];
  }

  return legacyPayload;
}

export function getSectionStatus(section) {
  if (section == null) return "Not returned by backend";
  if (typeof section.status === "string" && section.status.trim()) {
    return section.status;
  }
  if (
    typeof section.verification_status === "string" &&
    section.verification_status.trim()
  ) {
    return section.verification_status;
  }
  return "Status not provided";
}

export function getAssistantModeLabel(answer) {
  if (answer?.response_mode === "AI_GENERATED") {
    const provider = typeof answer.provider === "string"
      ? answer.provider
      : "configured provider";
    return `AI-generated explanation · ${provider} · not independently verified`;
  }
  const status = String(answer?.provider_status ?? "fallback")
    .replaceAll("_", " ")
    .toLowerCase();
  return `Deterministic analysis · ${status}`;
}

export function getComplianceStatusLabel(status) {
  const labels = {
    PASS: "Detected",
    POTENTIAL_ISSUE: "Potential issue",
    MISSING_INFORMATION: "Not detected",
    NEEDS_MANUAL_REVIEW: "Needs manual review",
    NOT_APPLICABLE: "Not applicable",
    NOT_EVALUATED: "Not evaluated",
  };
  return labels[status] ?? "Status not provided";
}

export function normalizeProductAnalysisResponse(data) {
  const allergens = data.allergen_analysis;
  const ingredients = data.ingredients;
  return {
    ...data,
    product_overview: data.product_overview ?? data.product ?? null,
    nutrition_analysis: data.nutrition_analysis ?? data.nutrition ?? null,
    ingredient_analysis:
      data.ingredient_analysis ?? ingredients?.analysis ?? null,
    additive_analysis:
      data.additive_analysis ?? ingredients?.additive_analysis ?? null,
    allergen_analysis: allergens
      ? {
          ...allergens,
          declared:
            allergens.declared ?? allergens.declared_allergens ?? null,
          may_contain: allergens.may_contain ?? null,
        }
      : null,
    personalized_suitability:
      data.personalized_suitability ??
      allergens?.personal_suitability ??
      null,
    limitations: data.limitations ?? data.completeness ?? null,
  };
}

export function isRouteUnavailableStatus(status) {
  return status === 404 || status === 405 || status === 501;
}
