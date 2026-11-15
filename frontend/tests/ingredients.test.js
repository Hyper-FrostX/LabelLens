import assert from "node:assert/strict";
import test from "node:test";

import { splitIngredientsText } from "../src/utils/ingredients.js";

test("splits top-level ingredients and preserves nested groups", () => {
  assert.deepEqual(
    splitIngredientsText("oats, spices (cinnamon, nutmeg), honey"),
    ["oats", "spices (cinnamon, nutmeg)", "honey"]
  );
});

test("supports nested square-bracket and parenthetical groups", () => {
  assert.deepEqual(
    splitIngredientsText("oats, seasoning [spices (pepper, paprika)], salt"),
    ["oats", "seasoning [spices (pepper, paprika)]", "salt"]
  );
});

test("returns no preview items for empty or malformed ingredient text", () => {
  assert.deepEqual(splitIngredientsText("  "), []);
  assert.deepEqual(splitIngredientsText("oats, spices (pepper"), []);
  assert.deepEqual(splitIngredientsText("oats, spices (pepper]"), []);
});
