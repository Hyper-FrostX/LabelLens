import { useCallback, useEffect, useState } from "react";

import AppShell from "./components/layout/AppShell";
import AdditiveScanner from "./components/AdditiveScanner";
import KnowledgeBaseExplorer from "./components/KnowledgeBaseExplorer";
import NutritionWorkspace from "./features/nutrition/NutritionWorkspace";
import { createAuthSession } from "./features/auth/authSession.js";
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
    eyebrow: "HEALTHIER ALTERNATIVES",
    description:
      "Explore alternatives from actual stored products when comparable label values are available. These are descriptive suggestions, not a universal product ranking.",
  },
};

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export default function App() {
  const [activeSection, setActiveSection] = useState("ingredients");
  const [authSession, setAuthSession] = useState(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const section = sections[activeSection];

  useEffect(() => {
    if (!authSession) return undefined;
    const remaining = authSession.expiresAt - Date.now();
    const timeout = window.setTimeout(() => {
      setAuthSession(null);
      setSessionExpired(true);
    }, Math.max(0, remaining));
    return () => window.clearTimeout(timeout);
  }, [authSession]);

  const updateAuthSession = useCallback((accessToken, expiresIn = 1800) => {
    if (typeof accessToken !== "string" || !accessToken) {
      setAuthSession(null);
      return;
    }
    const session = createAuthSession(accessToken, expiresIn);
    if (!session) {
      setAuthSession(null);
      setSessionExpired(true);
      return;
    }
    setAuthSession(session);
    setSessionExpired(false);
  }, []);

  const expireAuthSession = useCallback(() => {
    setAuthSession(null);
    setSessionExpired(true);
  }, []);

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
        <NutritionWorkspace
          focusSection={activeSection}
          accessToken={authSession?.accessToken ?? ""}
          sessionExpired={sessionExpired}
          onAuthChange={updateAuthSession}
          onAuthExpired={expireAuthSession}
        />
      )}
      {activeSection === "knowledge" && (
        <KnowledgeBaseExplorer apiBaseUrl={API_BASE_URL} />
      )}
    </AppShell>
  );
}
