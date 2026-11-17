export const nutrientFields = [
  { name: "sugar_g", label: "Total sugar", unit: "g" },
  { name: "added_sugar_g", label: "Added sugar", unit: "g" },
  { name: "sodium_mg", label: "Sodium", unit: "mg" },
  { name: "saturated_fat_g", label: "Saturated fat", unit: "g" },
];

export const nutrientUnitFields = {
  sugar_g: "sugar_unit",
  added_sugar_g: "added_sugar_unit",
  sodium_mg: "sodium_unit",
  saturated_fat_g: "saturated_fat_unit",
};

export const additionalNutrientFields = [
  { name: "energy_kcal", label: "Energy", unit: "kcal" },
  { name: "energy_kj", label: "Energy", unit: "kJ" },
  { name: "total_fat_g", label: "Total fat", unit: "g" },
  { name: "trans_fat_g", label: "Trans fat", unit: "g" },
  { name: "carbohydrates_g", label: "Carbohydrates", unit: "g" },
  { name: "protein_g", label: "Protein", unit: "g" },
  { name: "salt_g", label: "Salt", unit: "g" },
];

export const nutrientLabels = {
  total_sugar: "Total sugar",
  added_sugar: "Added sugar",
  sodium: "Sodium",
  saturated_fat: "Saturated fat",
};

export function getApiErrorMessage(payload, status, action = "Label extraction") {
  if (Array.isArray(payload?.detail)) {
    return payload.detail
      .map((issue) => {
        const field = issue.loc?.at(-1);
        return field ? `${field}: ${issue.msg}` : issue.msg;
      })
      .join(" ");
  }

  if (typeof payload?.detail === "string") {
    return payload.detail.slice(0, 500);
  }
  return `${action} failed (HTTP ${status}).`;
}

export function formatValue(value) {
  if (value === null || value === undefined || value === "") return "Not found";
  return String(value);
}

export function getConcernClass(item) {
  if (item.needs_review) return "concern-review";
  if (String(item.concern_level ?? "").startsWith("Established hazard")) {
    return "concern-established";
  }
  if (item.concern_level === "Context-dependent") return "concern-context";
  return "concern-neutral";
}

export function formatBasis(basis) {
  return (
    {
      per_serving: "per serving",
      per_100g: "per 100 g",
      per_100ml: "per 100 ml",
    }[basis] ?? "basis needs review"
  );
}

export function isAcceptedImage(file) {
  const acceptedTypes = ["image/jpeg", "image/png", "image/webp"];
  const acceptedExtensions = [".jpg", ".jpeg", ".png", ".webp"];
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  return (
    acceptedTypes.includes(file.type.toLowerCase()) ||
    (!file.type && acceptedExtensions.includes(extension))
  );
}

function prepareDeclarationText(value) {
  const declared = value?.value ?? value;
  if (Array.isArray(declared)) return declared.join(", ");
  return typeof declared === "string" ? declared : "";
}

export function prepareReviewData(data) {
  const imageFields = Array.isArray(data.fields) ? data.fields : [];
  const complianceFields = data.compliance_report?.mandatory_declarations ?? [];
  const editableFieldNames = new Set([
    "product_name",
    "basis",
    "serving_size_text",
    "ingredients_text",
    "allergens",
    "may_contain",
    ...nutrientFields.map(({ name }) => `nutrients.${name}`),
    ...additionalNutrientFields.map(({ name }) => `nutrients.${name}`),
    "name_of_food",
    "ingredient_list",
    "nutrition_information",
    "allergen_declaration",
    "vegetarian_declaration",
    "date_markings",
  ]);
  const otherFields = Object.fromEntries(
    complianceFields
      .filter((field) => field?.field_name && !editableFieldNames.has(field.field_name))
      .map((field) => [
        field.field_name,
        Array.isArray(field.extracted_value)
          ? field.extracted_value.join(", ")
          : typeof field.extracted_value === "object" && field.extracted_value !== null
            ? JSON.stringify(field.extracted_value)
            : field.extracted_value == null
              ? ""
              : String(field.extracted_value),
      ])
  );
  return {
    productName: data.product_name?.value ?? "",
    basis: data.basis ?? "",
    servingSize: data.serving_size_text ?? "",
    nutrients: Object.fromEntries(
      nutrientFields.map(({ name }) => [
        name,
        data.nutrients?.[name]?.value == null
          ? ""
          : String(data.nutrients[name].value),
      ])
    ),
    additionalNutrients: Object.fromEntries(
      additionalNutrientFields.map(({ name, unit }) => {
        const extracted = data.nutrients?.[name];
        return [
          name,
          {
            value:
              extracted?.value == null ? "" : String(extracted.value),
            unit: extracted?.unit || unit,
          },
        ];
      })
    ),
    ingredientsText: data.ingredients_text ?? "",
    declaredAllergenText: prepareDeclarationText(data.allergens),
    mayContainText: prepareDeclarationText(data.may_contain),
    reviewRequiredFields: Array.isArray(data.review_required_fields)
      ? data.review_required_fields
      : [],
    ocrText: typeof data.ocr_text === "string" ? data.ocr_text : "",
    originalValues: {
      productName: data.product_name?.value ?? "",
      basis: data.basis ?? "",
      servingSize: data.serving_size_text ?? "",
      ingredientsText: data.ingredients_text ?? "",
      declaredAllergenText: prepareDeclarationText(data.allergens),
      mayContainText: prepareDeclarationText(data.may_contain),
      nutrients: Object.fromEntries(
        [...nutrientFields, ...additionalNutrientFields].map(({ name }) => [
          name,
          data.nutrients?.[name]?.value == null
            ? ""
            : String(data.nutrients[name].value),
        ])
      ),
    },
    fields: imageFields,
    regions: Array.isArray(data.regions) ? data.regions : [],
    otherFields,
    originalOtherFields: { ...otherFields },
    symbolDetection: data.symbol_detection ?? null,
    symbolReview: "",
  };
}
