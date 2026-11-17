const comparisonGoals = new Set([
  "balanced",
  "lower_sugar",
  "lower_sodium",
  "lower_saturated_fat",
  "higher_protein",
  "higher_fiber",
  "lower_calories",
]);

export function buildProductComparisonRequest(scanIds, recommendationGoal = "balanced") {
  if (
    !Array.isArray(scanIds)
    || scanIds.length < 2
    || scanIds.length > 5
    || scanIds.some((id) => !Number.isInteger(id) || id < 1)
    || new Set(scanIds).size !== scanIds.length
  ) {
    throw new Error("Select 2–5 unique saved products to compare.");
  }
  if (!comparisonGoals.has(recommendationGoal)) {
    throw new Error("Choose a supported product comparison goal.");
  }
  return {
    scan_ids: [...scanIds],
    recommendation_goal: recommendationGoal,
  };
}

export function getComparisonRows(comparison) {
  if (
    comparison?.status !== "COMPARABLE"
    || !comparison.nutrient_comparisons
    || !Array.isArray(comparison.products)
  ) {
    return [];
  }
  return Object.entries(comparison.nutrient_comparisons).map(([key, item]) => ({
    key,
    unit: item.unit,
    label: {
      energy: "Energy",
      total_fat: "Total fat",
      saturated_fat: "Saturated fat",
      trans_fat: "Trans fat",
      carbohydrates: "Carbohydrates",
      sugar: "Total sugar",
      added_sugar: "Added sugar",
      protein: "Protein",
      fiber: "Fiber",
      sodium: "Sodium",
    }[key] ?? key,
    values: item.values,
  }));
}

export function formatComparisonBasis(basis) {
  return typeof basis === "string"
    ? basis.replaceAll("_", " ")
    : "not established";
}
