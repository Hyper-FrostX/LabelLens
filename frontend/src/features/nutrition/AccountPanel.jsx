import { useEffect, useRef, useState } from "react";

import Button from "../../components/ui/Button";
import { getApiErrorMessage } from "./nutritionUtils";
import { mergeScanHistoryPages } from "./ingredientReview.js";
import { fetchScanHistoryPage } from "./scanHistoryApi.js";

const SCAN_HISTORY_PAGE_SIZE = 20;

const HEALTH_CONDITIONS = [
  "Diabetes",
  "Hypertension",
  "Celiac disease",
  "PKU",
  "IBS",
  "Gout",
  "Heart disease",
  "Kidney disease",
];
const ALLERGENS = [
  "Gluten",
  "Dairy",
  "Soy",
  "Tree nuts",
  "Peanuts",
  "Eggs",
  "Fish",
  "Shellfish",
  "Sesame",
];

async function readResponse(response, action, onAuthExpired) {
  if (response.status === 401 && onAuthExpired) {
    onAuthExpired();
    const error = new Error("Your session expired. Sign in again.");
    error.status = 401;
    throw error;
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      response.ok
        ? `The backend returned an unreadable ${action} response.`
        : `${action} failed (HTTP ${response.status}).`
    );
  }
  if (!response.ok) {
    throw new Error(getApiErrorMessage(data, response.status, action));
  }
  return data;
}

export default function AccountPanel({
  apiBaseUrl,
  accessToken,
  onAuthChange,
  onAuthExpired,
  sessionExpired,
  historyVersion,
  onExpertiseChange,
  defaultOpen = false,
}) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [profile, setProfile] = useState(null);
  const [healthConditions, setHealthConditions] = useState([]);
  const [allergens, setAllergens] = useState([]);
  const [customAllergens, setCustomAllergens] = useState("");
  const [expertiseLevel, setExpertiseLevel] = useState("beginner");
  const [dietaryPreferences, setDietaryPreferences] = useState([]);
  const [ingredientExclusions, setIngredientExclusions] = useState("");
  const [nutritionGoals, setNutritionGoals] = useState([]);
  const [calorieGoal, setCalorieGoal] = useState("");
  const [proteinGoal, setProteinGoal] = useState("");
  const [history, setHistory] = useState([]);
  const [hasMoreHistory, setHasMoreHistory] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isLoadingMoreHistory, setIsLoadingMoreHistory] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const historyLoadLockRef = useRef(false);

  useEffect(() => {
    if (!accessToken) return undefined;

    let active = true;
    async function loadAccount() {
      setIsLoadingHistory(true);
      try {
        const headers = { Authorization: `Bearer ${accessToken}` };
        const [profileResponse, historyPage] = await Promise.all([
          fetch(`${apiBaseUrl}/profile`, { headers }),
          fetchScanHistoryPage({
            apiBaseUrl,
            accessToken,
            offset: 0,
            limit: SCAN_HISTORY_PAGE_SIZE,
            onAuthExpired,
          }),
        ]);
        const savedProfile = await readResponse(
          profileResponse,
          "Profile load",
          onAuthExpired,
        );
        const scans = historyPage.scans;
        if (!active) return;
        setProfile(savedProfile);
        setName(savedProfile.name);
        setExpertiseLevel(savedProfile.expertise_level);
        onExpertiseChange?.(savedProfile.expertise_level);
        setHealthConditions(savedProfile.health_conditions);
        setAllergens(savedProfile.allergens);
        setCustomAllergens(savedProfile.custom_allergens.join(", "));
        setDietaryPreferences(savedProfile.dietary_preferences ?? []);
        setIngredientExclusions((savedProfile.ingredient_exclusions ?? []).join(", "));
        setNutritionGoals(savedProfile.nutrition_goals ?? []);
        setCalorieGoal(savedProfile.calorie_goal_kcal == null ? "" : String(savedProfile.calorie_goal_kcal));
        setProteinGoal(savedProfile.protein_goal_g == null ? "" : String(savedProfile.protein_goal_g));
        setHistory(scans);
        setHasMoreHistory(historyPage.hasMore);
        setError("");
      } catch (requestError) {
        if (active && requestError.status !== 401) setError(requestError.message);
      } finally {
        if (active) setIsLoadingHistory(false);
      }
    }
    void loadAccount();
    return () => {
      active = false;
    };
  }, [accessToken, apiBaseUrl, historyVersion, onExpertiseChange, onAuthExpired]);

  async function loadMoreHistory() {
    if (
      !accessToken ||
      historyLoadLockRef.current ||
      !hasMoreHistory
    ) return;
    historyLoadLockRef.current = true;
    setIsLoadingMoreHistory(true);
    setError("");
    try {
      const nextPage = await fetchScanHistoryPage({
        apiBaseUrl,
        accessToken,
        offset: history.length,
        limit: SCAN_HISTORY_PAGE_SIZE,
        onAuthExpired,
      });
      setHistory((current) => mergeScanHistoryPages(current, nextPage.scans));
      setHasMoreHistory(nextPage.hasMore);
    } catch (requestError) {
      if (requestError.status !== 401) setError(requestError.message);
    } finally {
      historyLoadLockRef.current = false;
      setIsLoadingMoreHistory(false);
    }
  }

  async function submitAccount(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (mode === "register") {
        await readResponse(
          await fetch(`${apiBaseUrl}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password }),
          }),
          "Registration"
        );
      }
      const login = await readResponse(
        await fetch(`${apiBaseUrl}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        }),
        "Sign in"
      );
      setPassword("");
      onAuthChange(login.access_token, login.expires_in);
      setNotice("Signed in. Your profile and saved scan history are being loaded.");
    } catch (requestError) {
      setError(requestError instanceof TypeError
        ? `Could not connect to the Label Lens API at ${apiBaseUrl}.`
        : requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveProfile(event) {
    event.preventDefault();
    if (!accessToken) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const saved = await readResponse(
        await fetch(`${apiBaseUrl}/profile`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            name,
            expertise_level: expertiseLevel,
            health_conditions: healthConditions,
            allergens,
            dietary_preferences: dietaryPreferences,
            ingredient_exclusions: ingredientExclusions
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
            nutrition_goals: nutritionGoals,
            calorie_goal_kcal: calorieGoal === "" ? null : Number(calorieGoal),
            protein_goal_g: proteinGoal === "" ? null : Number(proteinGoal),
            custom_allergens: customAllergens
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
          }),
        }),
        "Profile save",
        onAuthExpired,
      );
      setProfile(saved);
      onExpertiseChange?.(saved.expertise_level);
      setCustomAllergens(saved.custom_allergens.join(", "));
      setDietaryPreferences(saved.dietary_preferences ?? []);
      setIngredientExclusions((saved.ingredient_exclusions ?? []).join(", "));
      setNutritionGoals(saved.nutrition_goals ?? []);
      setNotice("Profile preferences saved. Unsupported medical conditions are still not evaluated.");
    } catch (requestError) {
      if (requestError.status !== 401) {
        setError(requestError instanceof TypeError
          ? `Could not connect to the Label Lens API at ${apiBaseUrl}.`
          : requestError.message);
      }
    } finally {
      setBusy(false);
    }
  }

  function toggleSelection(items, setItems, item) {
    setItems((current) =>
      current.includes(item)
        ? current.filter((value) => value !== item)
        : [...current, item]
    );
  }

  function signOut() {
    onAuthChange("");
    onExpertiseChange?.("beginner");
  }

  return (
    <details className="account-panel" open={defaultOpen}>
      <summary>{accessToken ? "Account, profile & saved scans" : "Sign in for profile analysis and scan history"}</summary>
      {accessToken ? (
        <div className="account-content">
          <form onSubmit={saveProfile}>
            <label className="input-group">
              <span className="input-label">Profile name</span>
              <input value={name} onChange={(event) => setName(event.target.value)} required maxLength={160} />
            </label>
            <label className="input-group">
              <span className="input-label">Explanation detail</span>
              <select value={expertiseLevel} onChange={(event) => setExpertiseLevel(event.target.value)}>
                <option value="beginner">Beginner</option>
                <option value="expert">Expert</option>
              </select>
            </label>
            <fieldset className="account-choice-fieldset">
              <legend>Health conditions (only supported rules are evaluated)</legend>
              {HEALTH_CONDITIONS.map((condition) => (
                <label key={condition}>
                  <input
                    type="checkbox"
                    checked={healthConditions.includes(condition)}
                    onChange={() => toggleSelection(healthConditions, setHealthConditions, condition)}
                  />
                  {condition}
                </label>
              ))}
            </fieldset>
            <fieldset className="account-choice-fieldset">
              <legend>Dietary preferences (label-claim checks only)</legend>
              {["Vegetarian", "Vegan", "Gluten-free", "Dairy-free"].map((preference) => (
                <label key={preference}>
                  <input
                    type="checkbox"
                    checked={dietaryPreferences.includes(preference)}
                    onChange={() => toggleSelection(dietaryPreferences, setDietaryPreferences, preference)}
                  />
                  {preference}
                </label>
              ))}
            </fieldset>
            <label className="input-group">
              <span className="input-label">Ingredient exclusions (comma-separated)</span>
              <input
                value={ingredientExclusions}
                onChange={(event) => setIngredientExclusions(event.target.value)}
                maxLength={2500}
                placeholder="Ingredients you prefer to avoid"
              />
            </label>
            <fieldset className="account-choice-fieldset">
              <legend>Nutrition goals (project thresholds, not medical targets)</legend>
              {[
                ["higher_protein", "Higher protein"],
                ["higher_fiber", "Higher fiber"],
                ["lower_sugar", "Lower sugar"],
                ["lower_sodium", "Lower sodium"],
                ["lower_saturated_fat", "Lower saturated fat"],
                ["lower_calories", "Lower calories"],
              ].map(([value, label]) => (
                <label key={value}>
                  <input
                    type="checkbox"
                    checked={nutritionGoals.includes(value)}
                    onChange={() => toggleSelection(nutritionGoals, setNutritionGoals, value)}
                  />
                  {label}
                </label>
              ))}
            </fieldset>
            <div className="manual-product-fields">
              <label className="input-group">
                <span className="input-label">Daily calorie goal (kcal, optional)</span>
                <input type="number" min="500" max="10000" step="any" value={calorieGoal} onChange={(event) => setCalorieGoal(event.target.value)} />
              </label>
              <label className="input-group">
                <span className="input-label">Daily protein goal (g, optional)</span>
                <input type="number" min="1" max="400" step="any" value={proteinGoal} onChange={(event) => setProteinGoal(event.target.value)} />
              </label>
            </div>
            <fieldset className="account-choice-fieldset">
              <legend>Allergens</legend>
              {ALLERGENS.map((allergen) => (
                <label key={allergen}>
                  <input
                    type="checkbox"
                    checked={allergens.includes(allergen)}
                    onChange={() => toggleSelection(allergens, setAllergens, allergen)}
                  />
                  {allergen}
                </label>
              ))}
            </fieldset>
            <label className="input-group">
              <span className="input-label">Custom allergens (comma-separated)</span>
              <input value={customAllergens} onChange={(event) => setCustomAllergens(event.target.value)} maxLength={2500} />
            </label>
            <div className="account-actions">
              <Button type="submit" disabled={busy}>{busy ? "Saving…" : "Save profile"}</Button>
              <Button type="button" className="secondary-button" onClick={signOut}>Sign out</Button>
            </div>
          </form>
          <div className="scan-history">
            <h3>Saved scan history</h3>
            {isLoadingHistory && history.length === 0 ? (
              <p role="status">Loading saved scans…</p>
            ) : history.length ? (
              <ul>
                {history.map((scan) => {
                  const stored = scan.analysis_reports?.at(-1)?.analysis_data?.input;
                  const label = scan.extracted_label?.extracted_data;
                  const productName = stored?.product_name ?? label?.product_name ?? "Unnamed product";
                  return (
                    <li key={scan.id}>
                      <strong>{productName}</strong>
                      <span>{new Date(scan.created_at).toLocaleString()}</span>
                      <span>{scan.scan_status}</span>
                    </li>
                  );
                })}
              </ul>
            ) : <p>No saved scans yet.</p>}
            {hasMoreHistory && (
              <Button
                type="button"
                className="secondary-button"
                disabled={isLoadingMoreHistory}
                onClick={loadMoreHistory}
              >
                {isLoadingMoreHistory ? "Loading older scans…" : "Load older scans"}
              </Button>
            )}
          </div>
          {profile && <p className="muted-copy">Personalized results use only implemented profile rules and may explicitly report insufficient data.</p>}
        </div>
      ) : (
        <form className="account-content" onSubmit={submitAccount}>
          {sessionExpired && (
            <p className="legacy-api-notice" role="status">
              Your session expired. Sign in again to access your profile and saved scans.
            </p>
          )}
          <div className="account-mode-toggle" role="group" aria-label="Account action">
            <button type="button" aria-pressed={mode === "login"} onClick={() => setMode("login")}>Sign in</button>
            <button type="button" aria-pressed={mode === "register"} onClick={() => setMode("register")}>Create account</button>
          </div>
          {mode === "register" && (
            <label className="input-group">
              <span className="input-label">Name</span>
              <input value={name} onChange={(event) => setName(event.target.value)} required maxLength={160} autoComplete="name" />
            </label>
          )}
          <label className="input-group">
            <span className="input-label">Email</span>
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" />
          </label>
          <label className="input-group">
            <span className="input-label">Password</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={mode === "register" ? 12 : 1} maxLength={128} autoComplete={mode === "register" ? "new-password" : "current-password"} />
          </label>
          <Button type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"}</Button>
        </form>
      )}
      {notice && <p className="success-message" role="status">{notice}</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
    </details>
  );
}
