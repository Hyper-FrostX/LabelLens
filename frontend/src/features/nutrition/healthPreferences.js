export const HEALTH_CONDITION_OPTIONS = [
  {
    value: "Hypertension",
    label: "High Blood Pressure",
    detail: "Highlights supported sodium label signals for review.",
    icon: "♥",
  },
  {
    value: "Diabetes",
    label: "Diabetes / High Blood Sugar",
    detail: "Highlights supported total and added sugar label signals.",
    icon: "◉",
  },
  {
    value: "High Cholesterol",
    label: "High Cholesterol",
    detail: "Saved as a preference; condition-specific rules are not available.",
    icon: "◌",
  },
  {
    value: "Heart Health Concerns",
    label: "Heart Health Concerns",
    detail: "Saved as a preference; no medical inference is made.",
    icon: "♡",
  },
  {
    value: "Kidney Health Concerns",
    label: "Kidney Health Concerns",
    detail: "Saved as a preference; kidney-specific rules are not available.",
    icon: "⌁",
  },
  {
    value: "Obesity / Weight Management",
    label: "Obesity / Weight Management",
    detail: "Saved as a preference; no weight or medical conclusions are made.",
    icon: "↗",
  },
  {
    value: "Thyroid-related Dietary Concerns",
    label: "Thyroid-related Dietary Concerns",
    detail: "Saved as a preference; condition-specific rules are not available.",
    icon: "◇",
  },
];

export const ALLERGEN_OPTIONS = [
  { value: "Dairy", label: "Milk / Dairy", icon: "◉" },
  { value: "Peanuts", label: "Peanuts", icon: "●" },
  { value: "Tree nuts", label: "Tree Nuts", icon: "◈" },
  { value: "Soy", label: "Soy", icon: "◍" },
  { value: "Wheat", label: "Wheat", icon: "〽" },
  { value: "Gluten", label: "Gluten", icon: "▤" },
  { value: "Eggs", label: "Eggs", icon: "◯" },
  { value: "Fish", label: "Fish", icon: "≈" },
  { value: "Shellfish", label: "Shellfish", icon: "⌘" },
  { value: "Sesame", label: "Sesame", icon: "⁙" },
];

export function togglePreference(currentValues, value) {
  return currentValues.includes(value)
    ? currentValues.filter((item) => item !== value)
    : [...currentValues, value];
}

export function buildHealthProfileUpdate(profile, healthConditions, allergens) {
  const knownConditionValues = new Set(
    HEALTH_CONDITION_OPTIONS.map(({ value }) => value)
  );
  const preservedConditions = (profile.health_conditions ?? []).filter(
    (value) => !knownConditionValues.has(value)
  );

  return {
    name: profile.name,
    expertise_level: profile.expertise_level,
    health_conditions: [...new Set([...healthConditions, ...preservedConditions])],
    allergens,
    custom_allergens: profile.custom_allergens ?? [],
    dietary_preferences: profile.dietary_preferences ?? [],
    ingredient_exclusions: profile.ingredient_exclusions ?? [],
    nutrition_goals: profile.nutrition_goals ?? [],
    calorie_goal_kcal: profile.calorie_goal_kcal ?? null,
    protein_goal_g: profile.protein_goal_g ?? null,
  };
}
