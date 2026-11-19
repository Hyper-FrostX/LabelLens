import { useCallback, useEffect, useRef, useState } from "react";

import AppShell from "./components/layout/AppShell";
import AdditiveScanner from "./components/AdditiveScanner";
import FssaiGuide from "./components/FssaiGuide";
import NutritionWorkspace from "./features/nutrition/NutritionWorkspace";
import AccountPanel from "./features/nutrition/AccountPanel";
import HealthOnboarding from "./features/onboarding/HealthOnboarding";
import { createAuthSession } from "./features/auth/authSession.js";
import { buildHealthProfileUpdate } from "./features/nutrition/healthPreferences.js";
import "./App.css";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

function hasCompletedOnboarding() {
  try {
    return window.localStorage.getItem("labellens-onboarding-complete") === "true";
  } catch {
    return false;
  }
}

async function readProfileResponse(response, onAuthExpired) {
  if (response.status === 401) {
    onAuthExpired?.();
    throw new Error("Your session expired. Sign in again.");
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      response.ok
        ? "The backend returned an unreadable profile response."
        : `Profile request failed (HTTP ${response.status}).`
    );
  }
  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : null;
    throw new Error(detail ?? `Profile request failed (HTTP ${response.status}).`);
  }
  return data;
}

export default function App() {
  const [activeSection, setActiveSection] = useState("analyzer");
  const [showOnboarding, setShowOnboarding] = useState(() => !hasCompletedOnboarding());
  const [requiresSignIn, setRequiresSignIn] = useState(false);
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);
  const [preferencesError, setPreferencesError] = useState("");
  const [onboardingStorageWarning, setOnboardingStorageWarning] = useState("");
  const [preferenceNotice, setPreferenceNotice] = useState("");
  const [preferenceNoticeKind, setPreferenceNoticeKind] = useState("success");
  const onboardingTouchedRef = useRef({
    healthConditions: false,
    allergens: false,
  });
  const [preferences, setPreferences] = useState({
    healthConditions: [],
    allergens: [],
    expertiseLevel: "beginner",
  });
  const [isAccountOpen, setIsAccountOpen] = useState(false);
  const [showIngredientExplorer, setShowIngredientExplorer] = useState(false);
  const [authSession, setAuthSession] = useState(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    if (!authSession) return undefined;
    const remaining = authSession.expiresAt - Date.now();
    const timeout = window.setTimeout(() => {
      setAuthSession(null);
      setSessionExpired(true);
      setPreferences({ healthConditions: [], allergens: [], expertiseLevel: "beginner" });
      onboardingTouchedRef.current = { healthConditions: false, allergens: false };
    }, Math.max(0, remaining));
    return () => window.clearTimeout(timeout);
  }, [authSession]);

  const updateAuthSession = useCallback((accessToken, expiresIn = 1800) => {
    if (typeof accessToken !== "string" || !accessToken) {
      setAuthSession(null);
      setPreferences({ healthConditions: [], allergens: [], expertiseLevel: "beginner" });
      onboardingTouchedRef.current = { healthConditions: false, allergens: false };
      return;
    }
    const session = createAuthSession(accessToken, expiresIn);
    if (!session) {
      setAuthSession(null);
      setSessionExpired(true);
      setPreferences({ healthConditions: [], allergens: [], expertiseLevel: "beginner" });
      onboardingTouchedRef.current = { healthConditions: false, allergens: false };
      return;
    }
    setAuthSession(session);
    setSessionExpired(false);
  }, []);

  const expireAuthSession = useCallback(() => {
    setAuthSession(null);
    setSessionExpired(true);
    setPreferences({ healthConditions: [], allergens: [], expertiseLevel: "beginner" });
    onboardingTouchedRef.current = { healthConditions: false, allergens: false };
  }, []);

  const updatePreferences = useCallback((nextPreferences) => {
    setPreferences((current) => ({ ...current, ...nextPreferences }));
  }, []);

  const onPreferencesLoaded = useCallback((profile) => {
    setPreferences((current) => ({
      ...current,
      ...(!showOnboarding || !onboardingTouchedRef.current.healthConditions
        ? { healthConditions: profile.health_conditions }
        : {}),
      ...(!showOnboarding || !onboardingTouchedRef.current.allergens
        ? { allergens: profile.allergens }
        : {}),
      expertiseLevel: profile.expertise_level,
    }));
  }, [showOnboarding]);

  function changeHealthConditions(healthConditions) {
    onboardingTouchedRef.current.healthConditions = true;
    updatePreferences({ healthConditions });
  }

  function changeAllergens(allergens) {
    onboardingTouchedRef.current.allergens = true;
    updatePreferences({ allergens });
  }

  const finishOnboarding = useCallback(() => {
    try {
      window.localStorage.setItem("labellens-onboarding-complete", "true");
      setOnboardingStorageWarning("");
    } catch {
      setOnboardingStorageWarning(
        "This browser could not save the onboarding status. You can continue, but onboarding may appear again next time."
      );
    }
    setShowOnboarding(false);
    setRequiresSignIn(false);
    setActiveSection("analyzer");
  }, []);

  async function continueFromOnboarding() {
    setPreferencesError("");
    const hasSelections =
      preferences.healthConditions.length > 0 || preferences.allergens.length > 0;
    if (hasSelections && !authSession?.accessToken) {
      setRequiresSignIn(true);
      setIsAccountOpen(true);
      return;
    }
    if (authSession?.accessToken) {
      setIsSavingPreferences(true);
      try {
        const headers = { Authorization: `Bearer ${authSession.accessToken}` };
        const currentProfile = await readProfileResponse(
          await fetch(`${API_BASE_URL}/profile`, { headers }),
          expireAuthSession
        );
        const healthConditions = onboardingTouchedRef.current.healthConditions
          ? preferences.healthConditions
          : currentProfile.health_conditions;
        const allergens = onboardingTouchedRef.current.allergens
          ? preferences.allergens
          : currentProfile.allergens;
        const savedProfile = await readProfileResponse(
          await fetch(`${API_BASE_URL}/profile`, {
            method: "PUT",
            headers: {
              ...headers,
              "Content-Type": "application/json",
            },
            body: JSON.stringify(
              buildHealthProfileUpdate(
                currentProfile,
                healthConditions,
                allergens
              )
            ),
          }),
          expireAuthSession
        );
        updatePreferences({
          healthConditions: savedProfile.health_conditions,
          allergens: savedProfile.allergens,
          expertiseLevel: savedProfile.expertise_level,
        });
      } catch (error) {
        setPreferencesError(
          error instanceof TypeError
            ? `Could not connect to the Label Lens API at ${API_BASE_URL}.`
            : error.message
        );
        setIsSavingPreferences(false);
        return;
      }
      setIsSavingPreferences(false);
    }
    finishOnboarding();
  }

  async function savePreferencesFromNavigation() {
    setPreferenceNotice("");
    setPreferenceNoticeKind("success");
    if (!authSession?.accessToken) {
      setPreferenceNotice(
        "Preferences updated for this session. Sign in to save them to your account."
      );
      setPreferenceNoticeKind("success");
      return;
    }

    setIsSavingPreferences(true);
    try {
      const headers = { Authorization: `Bearer ${authSession.accessToken}` };
      const currentProfile = await readProfileResponse(
        await fetch(`${API_BASE_URL}/profile`, { headers }),
        expireAuthSession
      );
      const savedProfile = await readProfileResponse(
        await fetch(`${API_BASE_URL}/profile`, {
          method: "PUT",
          headers: {
            ...headers,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(
            buildHealthProfileUpdate(
              currentProfile,
              preferences.healthConditions,
              preferences.allergens
            )
          ),
        }),
        expireAuthSession
      );
      updatePreferences({
        healthConditions: savedProfile.health_conditions,
        allergens: savedProfile.allergens,
        expertiseLevel: savedProfile.expertise_level,
      });
      setPreferenceNotice(
        "Preferences saved successfully. Future label analyses will use these selections."
      );
      setPreferenceNoticeKind("success");
    } catch (error) {
      setPreferenceNotice(
        error instanceof TypeError
          ? `Could not connect to the Label Lens API at ${API_BASE_URL}.`
          : error.message
      );
      setPreferenceNoticeKind("error");
    } finally {
      setIsSavingPreferences(false);
    }
  }

  function navigate(section) {
    setPreferenceNotice("");
    setActiveSection(section);
    setShowIngredientExplorer(false);
  }

  const accountPanel = (
    <AccountPanel
      key={authSession?.accessToken ? "authenticated" : "guest"}
      apiBaseUrl={API_BASE_URL}
      accessToken={authSession?.accessToken ?? ""}
      onAuthChange={updateAuthSession}
      onAuthExpired={expireAuthSession}
      sessionExpired={sessionExpired}
      isOpen={isAccountOpen}
      onOpenChange={setIsAccountOpen}
      onPreferencesChange={updatePreferences}
      onPreferencesLoaded={onPreferencesLoaded}
      onboardingError={requiresSignIn ? preferencesError : ""}
    />
  );

  return (
    <AppShell
      activeSection={activeSection}
      onNavigate={navigate}
      headerAction={accountPanel}
      onboarding={showOnboarding}
    >
      {showOnboarding ? (
        <>
          <HealthOnboarding
            healthConditions={preferences.healthConditions}
            allergens={preferences.allergens}
            onHealthConditionsChange={changeHealthConditions}
            onAllergensChange={changeAllergens}
            onContinue={continueFromOnboarding}
            onSkip={finishOnboarding}
            requiresSignIn={requiresSignIn}
            error={preferencesError}
            isSaving={isSavingPreferences}
          />
        </>
      ) : activeSection === "fssai" ? (
        <>
          {onboardingStorageWarning && (
            <p className="legacy-api-notice" role="status">{onboardingStorageWarning}</p>
          )}
          <FssaiGuide onAnalyze={() => navigate("analyzer")} />
        </>
      ) : activeSection === "preferences" ? (
        <HealthOnboarding
          editingMode
          healthConditions={preferences.healthConditions}
          allergens={preferences.allergens}
          onHealthConditionsChange={changeHealthConditions}
          onAllergensChange={changeAllergens}
          onSave={savePreferencesFromNavigation}
          onBack={() => navigate("analyzer")}
          requiresSignIn={Boolean(authSession?.accessToken)}
          error={preferenceNoticeKind === "error" ? preferenceNotice : ""}
          isSaving={isSavingPreferences}
          notice={preferenceNotice}
          noticeKind={preferenceNoticeKind}
        />
      ) : showIngredientExplorer ? (
        <>
          {onboardingStorageWarning && (
            <p className="legacy-api-notice" role="status">{onboardingStorageWarning}</p>
          )}
          <main className="ingredient-explorer-page">
            <button
              type="button"
              className="back-to-analyzer"
              onClick={() => setShowIngredientExplorer(false)}
            >
              ← Back to Label Analyzer
            </button>
            <AdditiveScanner apiBaseUrl={API_BASE_URL} />
          </main>
        </>
      ) : (
        <>
          {onboardingStorageWarning && (
            <p className="legacy-api-notice" role="status">{onboardingStorageWarning}</p>
          )}
          <NutritionWorkspace
            accessToken={authSession?.accessToken ?? ""}
            healthConditions={preferences.healthConditions}
            allergens={preferences.allergens}
            explanationLevel={preferences.expertiseLevel}
            onExplanationLevelChange={(expertiseLevel) =>
              updatePreferences({ expertiseLevel })
            }
            onShowIngredients={() => setShowIngredientExplorer(true)}
            onAuthExpired={expireAuthSession}
          />
        </>
      )}
    </AppShell>
  );
}
