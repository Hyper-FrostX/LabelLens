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
  history: {
    title: "Scan History",
    eyebrow: "YOUR SAVED ANALYSES",
    description:
      "Sign in to review previously saved label analyses. Scan history is private to your account.",
  },
  profile: {
    title: "My Health Profile",
    eyebrow: "PERSONALIZED ANALYSIS",
    description:
      "Manage your saved allergens, health conditions, and explanation preference. Unsupported conditions remain unevaluated.",
  },
  alternatives: {
    title: "Stored-product Alternatives",
    eyebrow: "NUTRIENT COMPARISONS",
    description:
      "Compare a reviewed label with actual stored products or your own saved scans. Recommendations require comparable label values.",
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
      {["scan", "history", "profile", "alternatives"].includes(activeSection) && (
        <NutritionWorkspace focusSection={activeSection} />
      )}
      {activeSection === "knowledge" && (
        <KnowledgeBaseExplorer apiBaseUrl={API_BASE_URL} />
      )}
    </AppShell>
  );
}
