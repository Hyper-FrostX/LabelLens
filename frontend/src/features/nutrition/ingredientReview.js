export const MAX_INGREDIENT_TEXT_LENGTH = 10000;

export function validateIngredientText(value) {
  const text = typeof value === "string" ? value.trim() : "";
  if (!text) {
    return { valid: false, error: "Enter an ingredients list to analyze." };
  }
  if (text.length > MAX_INGREDIENT_TEXT_LENGTH) {
    return {
      valid: false,
      error: `Ingredients must be ${MAX_INGREDIENT_TEXT_LENGTH} characters or fewer.`,
    };
  }
  if (!/[\p{L}\p{N}]/u.test(text)) {
    return {
      valid: false,
      error: "Enter ingredient names, not only punctuation.",
    };
  }
  return { valid: true, text };
}

export function mergeScanHistoryPages(current, next) {
  const seen = new Set(current.map((scan) => scan.id));
  const merged = [...current];
  for (const scan of next) {
    if (seen.has(scan.id)) continue;
    seen.add(scan.id);
    merged.push(scan);
  }
  return merged;
}
