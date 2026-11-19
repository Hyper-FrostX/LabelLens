import Button from "./ui/Button";

const reviewAreas = [
  {
    title: "License number format",
    description:
      "The report can check an extracted FSSAI number's format. It does not verify a license with FSSAI.",
  },
  {
    title: "Label declarations",
    description:
      "The report inspects submitted text for required declaration fields and flags information that needs review.",
  },
  {
    title: "Ingredients and allergens",
    description:
      "Ingredient and allergen matches are based on the submitted label text and available evidence.",
  },
  {
    title: "Nutrition and date markings",
    description:
      "The report identifies nutrition-panel and date-marking observations when readable label text is available.",
  },
];

export default function FssaiGuide({ onAnalyze }) {
  return (
    <main className="fssai-page">
      <section className="fssai-hero">
        <p className="eyebrow">INDIAN FOOD LABEL INFORMATION</p>
        <h1>FSSAI label review</h1>
        <p>
          Learn what LabelLens can inspect on an Indian packaged-food label.
          Findings are informational and require checking against the package
          and current official requirements.
        </p>
        <Button type="button" onClick={onAnalyze}>
          Analyze a food label
        </Button>
      </section>
      <section className="fssai-review-grid" aria-label="FSSAI review areas">
        {reviewAreas.map((area, index) => (
          <article className="fssai-review-card" key={area.title}>
            <span aria-hidden="true">0{index + 1}</span>
            <h2>{area.title}</h2>
            <p>{area.description}</p>
          </article>
        ))}
      </section>
      <aside className="fssai-disclaimer">
        <strong>Important</strong>
        <p>
          LabelLens does not certify legal compliance, confirm an FSSAI license,
          or replace the current regulations, official guidance, or professional
          review. OCR and text matching can miss or misread label information.
        </p>
        <a href="https://www.fssai.gov.in/" target="_blank" rel="noreferrer">
          Visit the official FSSAI website
        </a>
      </aside>
    </main>
  );
}
