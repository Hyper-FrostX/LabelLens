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

export function prepareReviewData(data) {
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
    ingredientsText: data.ingredients_text ?? "",
    reviewRequiredFields: Array.isArray(data.review_required_fields)
      ? data.review_required_fields
      : [],
    ocrText: typeof data.ocr_text === "string" ? data.ocr_text : "",
  };
}
