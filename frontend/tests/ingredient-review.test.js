import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_INGREDIENT_TEXT_LENGTH,
  mergeScanHistoryPages,
  validateIngredientText,
} from "../src/features/nutrition/ingredientReview.js";

test("validates and trims reviewed ingredient text", () => {
  assert.deepEqual(validateIngredientText("  oats, salt  "), {
    valid: true,
    text: "oats, salt",
  });
});

test("rejects empty, punctuation-only, and oversized ingredient text", () => {
  assert.equal(validateIngredientText("  ").valid, false);
  assert.equal(validateIngredientText(",,, ()").valid, false);
  assert.equal(
    validateIngredientText("a".repeat(MAX_INGREDIENT_TEXT_LENGTH + 1)).valid,
    false,
  );
});

test("merges history pages without duplicate scans", () => {
  const firstPage = [{ id: 1 }, { id: 2 }];
  const result = mergeScanHistoryPages(firstPage, [
    { id: 2 },
    { id: 3 },
    { id: 3 },
  ]);
  assert.deepEqual(result, [{ id: 1 }, { id: 2 }, { id: 3 }]);
});
