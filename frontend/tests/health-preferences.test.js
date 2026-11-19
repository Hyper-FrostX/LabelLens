import assert from "node:assert/strict";
import test from "node:test";

import {
  ALLERGEN_OPTIONS,
  HEALTH_CONDITION_OPTIONS,
  buildHealthProfileUpdate,
  togglePreference,
} from "../src/features/nutrition/healthPreferences.js";

test("exposes all requested optional health and allergy choices", () => {
  assert.equal(HEALTH_CONDITION_OPTIONS.length, 7);
  assert.equal(ALLERGEN_OPTIONS.length, 10);
  assert.ok(ALLERGEN_OPTIONS.some(({ value }) => value === "Wheat"));
  assert.ok(ALLERGEN_OPTIONS.some(({ value }) => value === "Gluten"));
});

test("toggles independent selections without mutating the current list", () => {
  const selected = ["Diabetes"];
  assert.deepEqual(togglePreference(selected, "Hypertension"), [
    "Diabetes",
    "Hypertension",
  ]);
  assert.deepEqual(togglePreference(selected, "Diabetes"), []);
  assert.deepEqual(selected, ["Diabetes"]);
});

test("builds a profile update that preserves other profile settings and legacy conditions", () => {
  const payload = buildHealthProfileUpdate(
    {
      name: "LabelLens user",
      expertise_level: "expert",
      health_conditions: ["Diabetes", "Heart disease"],
      allergens: ["Wheat"],
      dietary_preferences: ["Vegetarian"],
      ingredient_exclusions: ["gelatin"],
      nutrition_goals: ["lower_sugar"],
      custom_allergens: ["Mustard"],
      calorie_goal_kcal: 2100,
      protein_goal_g: 80,
    },
    ["Hypertension"],
    ["Wheat", "Dairy"]
  );

  assert.deepEqual(payload.health_conditions, ["Hypertension", "Heart disease"]);
  assert.deepEqual(payload.allergens, ["Wheat", "Dairy"]);
  assert.deepEqual(payload.dietary_preferences, ["Vegetarian"]);
  assert.deepEqual(payload.ingredient_exclusions, ["gelatin"]);
  assert.deepEqual(payload.nutrition_goals, ["lower_sugar"]);
  assert.deepEqual(payload.custom_allergens, ["Mustard"]);
  assert.equal(payload.calorie_goal_kcal, 2100);
  assert.equal(payload.protein_goal_g, 80);
});

test("guest preference saving is described as session-only", () => {
  assert.match(
    "Preferences updated for this session. Sign in to save them to your account.",
    /for this session/
  );
  assert.doesNotMatch(
    "Preferences updated for this session. Sign in to save them to your account.",
    /saved to your account/
  );
});
