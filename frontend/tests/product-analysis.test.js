import assert from "node:assert/strict";
import test from "node:test";

import {
  buildLabelCorrections,
  buildProductAnalysisPayload,
  getComplianceStatusLabel,
  getAssistantModeLabel,
  getSectionStatus,
  isRouteUnavailableStatus,
  normalizeProductAnalysisResponse,
  toLegacyLabelPayload,
} from "../src/features/nutrition/productAnalysisUtils.js";
import { prepareReviewData } from "../src/features/nutrition/nutritionUtils.js";
import {
  buildProductComparisonRequest,
  formatComparisonBasis,
  getComparisonRows,
} from "../src/features/nutrition/comparisonUtils.js";

const nutrients = {
  sugar_g: "4.5",
  added_sugar_g: "",
  sodium_mg: "80",
  saturated_fat_g: "1",
};

test("builds the product request with separate allergen text and explicit units", () => {
  const payload = buildProductAnalysisPayload({
    productName: "  Oat bar ",
    declaredAllergenText: "",
    ingredientsText: " oats, honey ",
    mayContainText: "peanuts",
    nutrients,
    basis: "per_serving",
    servingSize: "30 g",
    explanationLevel: "beginner",
  });

  assert.deepEqual(payload, {
    product_name: "Oat bar",
    label_text: null,
    product_category: null,
    label_corrections: {},
    corrections_confirmed: false,
    extraction_metadata: null,
    symbol_review: null,
    ingredients_text: "oats, honey",
    may_contain_text: "peanuts",
    allergens: null,
    may_contain: ["peanuts"],
    sugar_g: 4.5,
    sugar_unit: "g",
    added_sugar_g: null,
    added_sugar_unit: "g",
    sodium_mg: 80,
    sodium_unit: "mg",
    saturated_fat_g: 1,
    saturated_fat_unit: "g",
    basis: "per_serving",
    units: {
      sugar_g: "g",
      added_sugar_g: "g",
      sodium_mg: "mg",
      saturated_fat_g: "g",
    },
    serving_size_text: "30 g",
    explanation_level: "standard",
    recommendation_goal: "balanced",
    save_to_history: false,
    additional_nutrients: {},
  });
});

test("serializes additional nutrient values in the product request and rejects invalid ones", () => {
  const payload = buildProductAnalysisPayload({
    productName: "Oat bar",
    ingredientsText: "oats",
    mayContainText: "peanuts",
    nutrients,
    additionalNutrients: {
      total_fat_g: { value: "12.5", unit: "g" },
      protein_g: { value: "6", unit: "g" },
      energy_kcal: { value: "", unit: "kcal" },
    },
    basis: "per_100g",
    servingSize: "100 g",
    explanationLevel: "expert",
  });

  assert.deepEqual(payload.additional_nutrients, {
    total_fat_g: { value: 12.5, unit: "g" },
    protein_g: { value: 6, unit: "g" },
  });

  assert.throws(
    () => buildProductAnalysisPayload({
      productName: "",
      ingredientsText: "",
      mayContainText: "",
      nutrients: { ...nutrients, sodium_mg: "-1" },
      additionalNutrients: { total_fat_g: { value: "-1", unit: "g" } },
      basis: "",
      servingSize: "",
      explanationLevel: "expert",
    }),
    /Sodium must be a non-negative number/
  );
  assert.throws(
    () => buildProductAnalysisPayload({
      productName: "",
      ingredientsText: "",
      mayContainText: "",
      nutrients: { ...nutrients, sodium_mg: "80" },
      additionalNutrients: { total_fat_g: { value: "not-a-number", unit: "g" } },
      basis: "",
      servingSize: "",
      explanationLevel: "expert",
    }),
    /Total fat must be a non-negative number/
  );
});

test("legacy fallback sends only fields accepted by label analysis", () => {
  const payload = buildProductAnalysisPayload({
    productName: "Oat bar",
    ingredientsText: "oats",
    mayContainText: "peanuts",
    nutrients,
    basis: "per_100g",
    servingSize: "",
    explanationLevel: "expert",
    saveToHistory: true,
  });
  assert.equal(payload.save_to_history, true);

  assert.deepEqual(toLegacyLabelPayload(payload), {
    basis: "per_100g",
    serving_size_text: null,
    ingredients_text: "oats",
    sugar_g: 4.5,
    sugar_unit: "g",
    added_sugar_g: null,
    added_sugar_unit: "g",
    sodium_mg: 80,
    sodium_unit: "mg",
    saturated_fat_g: 1,
    saturated_fat_unit: "g",
  });
});

test("reports missing backend statuses and only falls back for unavailable routes", () => {
  assert.equal(getSectionStatus(null), "Not returned by backend");
  assert.equal(getSectionStatus({ items: [] }), "Status not provided");
  assert.equal(getSectionStatus({ status: "not_assessed" }), "not_assessed");
  assert.equal(isRouteUnavailableStatus(404), true);
  assert.equal(isRouteUnavailableStatus(405), true);
  assert.equal(isRouteUnavailableStatus(501), true);
  assert.equal(isRouteUnavailableStatus(422), false);
});

test("labels AI-generated explanations separately from deterministic fallback", () => {
  assert.equal(
    getAssistantModeLabel({
      response_mode: "AI_GENERATED",
      provider: "gemini",
    }),
    "AI-generated explanation · gemini · not independently verified"
  );
  assert.equal(
    getAssistantModeLabel({
      response_mode: "DETERMINISTIC_FALLBACK",
      provider_status: "PROVIDER_RATE_LIMITED",
    }),
    "Deterministic analysis · provider rate limited"
  );
});

test("sends original OCR text and labels compliance states without implying verification", () => {
  const payload = buildProductAnalysisPayload({
    productName: "Oat bar",
    ingredientsText: "oats",
    mayContainText: "",
    nutrients,
    basis: "per_100g",
    servingSize: "",
    explanationLevel: "standard",
    labelText: "Ingredients: oats\nFSSAI License No: 12345678901234",
  });

  assert.equal(payload.label_text, "Ingredients: oats\nFSSAI License No: 12345678901234");
  assert.equal(getComplianceStatusLabel("NEEDS_MANUAL_REVIEW"), "Needs manual review");
  assert.equal(getComplianceStatusLabel("UNKNOWN"), "Status not provided");
  assert.equal(getComplianceStatusLabel("NOT_EVALUATED"), "Not evaluated");
});

test("sends explicitly confirmed review corrections and image evidence to product analysis", () => {
  const extractionMetadata = {
    fields: [{ field_name: "product_name", confidence_state: "LOW_CONFIDENCE" }],
    regions: [{ region_type: "ingredients" }],
    symbol_detection: { vegetarian: { status: "DETECTED" } },
  };
  const payload = buildProductAnalysisPayload({
    productName: "Reviewed oat bar",
    ingredientsText: "oats, honey",
    mayContainText: "",
    nutrients,
    basis: "per_100g",
    servingSize: "",
    explanationLevel: "standard",
    labelText: "Product Name: Oat bar",
    correctionsConfirmed: true,
    labelCorrections: { product_name: "Reviewed oat bar" },
    extractionMetadata,
    symbolReview: "VEGETARIAN",
  });

  assert.equal(payload.corrections_confirmed, true);
  assert.deepEqual(payload.label_corrections, { product_name: "Reviewed oat bar" });
  assert.deepEqual(payload.extraction_metadata, extractionMetadata);
  assert.equal(payload.symbol_review, "VEGETARIAN");
  assert.equal(payload.label_text, "Product Name: Oat bar");
});

test("sends a selected alternatives goal without changing the product-analysis fields", () => {
  const payload = buildProductAnalysisPayload({
    productName: "Oat bar",
    ingredientsText: "oats",
    mayContainText: "",
    nutrients,
    basis: "per_100g",
    servingSize: "",
    explanationLevel: "expert",
    recommendationGoal: "higher_protein",
  });

  assert.equal(payload.recommendation_goal, "higher_protein");
  assert.equal(payload.explanation_level, "detailed");
});

test("validates saved comparison selections and displays only shared server-comparable nutrients", () => {
  assert.deepEqual(buildProductComparisonRequest([4, 9]), {
    scan_ids: [4, 9],
    recommendation_goal: "balanced",
  });
  assert.deepEqual(
    buildProductComparisonRequest([4, 9], "higher_protein"),
    { scan_ids: [4, 9], recommendation_goal: "higher_protein" }
  );
  assert.throws(
    () => buildProductComparisonRequest([4, 9], "universal_winner"),
    /supported product comparison goal/
  );
  assert.throws(() => buildProductComparisonRequest([4, 4]), /unique saved products/);
  assert.throws(() => buildProductComparisonRequest([4]), /2–5/);
  assert.equal(formatComparisonBasis("per_100g"), "per 100g");
  assert.deepEqual(
    getComparisonRows({
      status: "COMPARABLE",
      products: [{ scan_id: 4 }, { scan_id: 9 }],
      nutrient_comparisons: {
        sugar: {
          unit: "g",
          values: [{ scan_id: 4, value: 4 }, { scan_id: 9, value: 2 }],
        },
      },
    }),
    [{
      key: "sugar",
      unit: "g",
      label: "Total sugar",
      values: [{ scan_id: 4, value: 4 }, { scan_id: 9, value: 2 }],
    }]
  );
  assert.deepEqual(
    getComparisonRows({ status: "INSUFFICIENT_DATA", nutrient_comparisons: {} }),
    []
  );
});

test("builds a complete correction record from the explicitly reviewed form values", () => {
  const corrections = buildLabelCorrections({
    productName: "Reviewed bar",
    basis: "per_100g",
    servingSize: "30 g",
    ingredientsText: "oats, honey",
    declaredAllergenText: "milk",
    mayContainText: "peanuts",
    nutrients: { sugar_g: "8", sodium_mg: "" },
    additionalNutrients: {
      protein_g: { value: "6", unit: "g" },
    },
    otherFields: { fssai_license_number: "12345678901234" },
  });

  assert.deepEqual(corrections, {
    product_name: "Reviewed bar",
    basis: "per_100g",
    serving_size_text: "30 g",
    ingredients_text: "oats, honey",
    allergens: "milk",
    may_contain: "peanuts",
    nutrients: { sugar_g: "8", sodium_mg: "", protein_g: "6" },
    other_fields: { fssai_license_number: "12345678901234" },
  });
});

test("prepares editable final fields while retaining original OCR, regions, confidence, and symbols", () => {
  const review = prepareReviewData({
    product_name: { value: "Oat bar" },
    basis: "per_100g",
    serving_size_text: "30 g",
    nutrients: { sugar_g: { value: 4, unit: "g" } },
    ingredients_text: "oats, honey",
    allergens: { value: ["milk"] },
    may_contain: { value: ["peanuts"] },
    ocr_text: "Product Name: Oat bar",
    fields: [
      {
        field_name: "product_name",
        field_type: "product_name",
        extracted_value: "Oat bar",
        confidence_state: "LOW_CONFIDENCE",
      },
    ],
    regions: [{ region_type: "ingredients", extracted_text: "oats, honey" }],
    symbol_detection: { vegetarian: { status: "DETECTED" } },
    compliance_report: {
      mandatory_declarations: [
        { field_name: "fssai_license_number", extracted_value: "12345678901234" },
        { field_name: "name_of_food", extracted_value: "Oat bar" },
      ],
    },
  });

  assert.equal(review.originalValues.productName, "Oat bar");
  assert.equal(review.originalValues.nutrients.sugar_g, "4");
  assert.deepEqual(review.fields[0], {
    field_name: "product_name",
    field_type: "product_name",
    extracted_value: "Oat bar",
    confidence_state: "LOW_CONFIDENCE",
  });
  assert.equal(review.regions[0].region_type, "ingredients");
  assert.deepEqual(review.otherFields, { fssai_license_number: "12345678901234" });
  assert.equal(review.symbolDetection.vegetarian.status, "DETECTED");
});

test("normalizes the returned product-analysis sections without inventing fields", () => {
  const complianceReport = {
    overall_status: "NEEDS_MANUAL_REVIEW",
    legal_compliance_determination: "NOT_EVALUATED",
  };
  const result = normalizeProductAnalysisResponse({
    product: { name: "Oat bar" },
    nutrition: { health_score: { status: "unavailable" }, excess_nutrients: [] },
    ingredients: {
      analysis: { ingredients: [], evidence_concerns: [] },
      additive_analysis: { matched_additives: [] },
    },
    allergen_analysis: {
      declared_allergens: { status: "provided", label_text: ["milk"] },
      may_contain: { status: "not_provided", label_text: [] },
      personal_suitability: { status: "NOT_EVALUATED" },
    },
    alternatives: { status: "NOT_AVAILABLE" },
    completeness: { status: "partial", limitations: ["No profile used."] },
    compliance_report: complianceReport,
  });

  assert.deepEqual(result.product_overview, { name: "Oat bar" });
  assert.equal(result.nutrition_analysis.health_score.status, "unavailable");
  assert.deepEqual(result.ingredient_analysis, {
    ingredients: [],
    evidence_concerns: [],
  });
  assert.deepEqual(result.additive_analysis, { matched_additives: [] });
  assert.equal(result.allergen_analysis.declared.status, "provided");
  assert.equal(result.allergen_analysis.may_contain.status, "not_provided");
  assert.equal(result.personalized_suitability.status, "NOT_EVALUATED");
  assert.equal(result.limitations.status, "partial");
  assert.equal(result.compliance_report, complianceReport);
  assert.equal(result.product_name, undefined);
});
