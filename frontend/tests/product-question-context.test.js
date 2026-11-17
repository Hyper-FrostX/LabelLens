import assert from "node:assert/strict";
import test from "node:test";

import { buildProductQuestionContext } from "../src/features/nutrition/productQuestionContext.js";

test("keeps report evidence while bounding large OCR and analysis context", () => {
  const context = buildProductQuestionContext(
    {
      product_name: "Oat snack",
      basis: "per_100g",
      sugar_g: 8,
      ingredients_text: "oats, salt",
      label_text: "label text ".repeat(2_000),
      extraction_metadata: {
        fields: Array.from({ length: 150 }, (_, index) => ({
          field_name: `field-${index}`,
          confidence_state: "HIGH",
          raw_text: "x".repeat(10_000),
        })),
      },
    },
    {
      product: { name: "Oat snack" },
      nutrition: { health_score: { score: 82, details: "x".repeat(100_000) } },
      ingredients: {
        text: "oats, salt",
        analysis: {
          ingredients: Array.from({ length: 200 }, () => ({
            canonical_name: "Oats",
            explanation: "x".repeat(5_000),
          })),
        },
      },
      food_intelligence: {
        nutrition: {
          normalized_basis: "per_100g",
          nutrient_density_per_100: {
            sugar: { value: 8, unit: "g", basis: "per_100g" },
          },
        },
      },
    }
  );

  assert.ok(JSON.stringify(context).length < 50_000);
  assert.equal(context.product_name, "Oat snack");
  assert.equal(context.product.name, "Oat snack");
  assert.equal(context.sugar_g, 8);
  assert.equal(
    context.food_intelligence.nutrition.nutrient_density_per_100.sugar.value,
    8
  );
  assert.ok(context.extraction_metadata.fields.length <= 20);
});
