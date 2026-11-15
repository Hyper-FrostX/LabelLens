import { useState } from "react";

import AppShell from "./components/layout/AppShell";
import AdditiveScanner from "./components/AdditiveScanner";
import KnowledgeBaseExplorer from "./components/KnowledgeBaseExplorer";
import NutritionWorkspace from "./features/nutrition/NutritionWorkspace";
import "./App.css";

const sections = {
  scan: {
    title: "Scan Food",
    eyebrow: "LABEL SCANNING",
    description:
      "Extract a packaged-food label, review every detected value, and explore its nutrition and ingredient signals.",
  },
  ingredients: {
    title: "Ingredient Explorer",
    eyebrow: "INGREDIENT INTELLIGENCE",
    description:
      "Check a label’s ingredient list against a curated catalog of additives, functions, and evidence notes.",
  },
  knowledge: {
    title: "Additives Knowledge Base",
    eyebrow: "CURATED REFERENCE",
    description:
      "Search the catalog by ingredient, additive code, concern level, or functional purpose.",
  },
};

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export default function App() {
  const [activeSection, setActiveSection] = useState("ingredients");
  const section = sections[activeSection];

  return (
    <AppShell
      activeSection={activeSection}
      onNavigate={setActiveSection}
      title={section.title}
      eyebrow={section.eyebrow}
      description={section.description}
    >
      {activeSection === "ingredients" && (
        <AdditiveScanner apiBaseUrl={API_BASE_URL} />
      )}
      {activeSection === "scan" && <NutritionWorkspace />}
      {activeSection === "knowledge" && (
        <KnowledgeBaseExplorer apiBaseUrl={API_BASE_URL} />
      )}
    </AppShell>
  );
}
