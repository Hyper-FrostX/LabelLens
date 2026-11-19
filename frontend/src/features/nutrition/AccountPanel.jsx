import { useEffect, useState } from "react";

import Button from "../../components/ui/Button";
import HealthPreferencePicker from "../onboarding/HealthPreferencePicker";
import { buildHealthProfileUpdate } from "./healthPreferences.js";
import { getApiErrorMessage } from "./nutritionUtils";

async function readResponse(response, action, onAuthExpired) {
  if (response.status === 401) {
    onAuthExpired?.();
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
  isOpen,
  onOpenChange,
  onPreferencesChange,
  onPreferencesLoaded,
  onboardingError,
}) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [profile, setProfile] = useState(null);
  const [draftHealthConditions, setDraftHealthConditions] = useState([]);
  const [draftAllergens, setDraftAllergens] = useState([]);
  const [draftExpertiseLevel, setDraftExpertiseLevel] = useState("beginner");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!accessToken) return undefined;

    let active = true;
    async function loadProfile() {
      try {
        const savedProfile = await readResponse(
          await fetch(`${apiBaseUrl}/profile`, {
            headers: { Authorization: `Bearer ${accessToken}` },
          }),
          "Profile load",
          onAuthExpired
        );
        if (!active) return;
        setProfile(savedProfile);
        setName(savedProfile.name);
        setDraftHealthConditions(savedProfile.health_conditions);
        setDraftAllergens(savedProfile.allergens);
        setDraftExpertiseLevel(savedProfile.expertise_level);
        onPreferencesLoaded?.(savedProfile);
        setError("");
      } catch (requestError) {
        if (active && requestError.status !== 401) {
          setError(
            requestError instanceof TypeError
              ? `Could not connect to the Label Lens API at ${apiBaseUrl}.`
              : requestError.message
          );
        }
      }
    }
    void loadProfile();
    return () => {
      active = false;
    };
  }, [accessToken, apiBaseUrl, onAuthExpired, onPreferencesLoaded]);

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
      onOpenChange(false);
      setNotice("Signed in. Your saved health and allergy preferences are loading.");
    } catch (requestError) {
      setError(
        requestError instanceof TypeError
          ? `Could not connect to the Label Lens API at ${apiBaseUrl}.`
          : requestError.message
      );
    } finally {
      setBusy(false);
    }
  }

  async function saveProfile(event) {
    event.preventDefault();
    if (!accessToken || !profile) return;
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
          body: JSON.stringify(
            buildHealthProfileUpdate(
              { ...profile, name, expertise_level: draftExpertiseLevel },
              draftHealthConditions,
              draftAllergens
            )
          ),
        }),
        "Profile save",
        onAuthExpired
      );
      setProfile(saved);
      setName(saved.name);
      setDraftHealthConditions(saved.health_conditions);
      setDraftAllergens(saved.allergens);
      setDraftExpertiseLevel(saved.expertise_level);
      onPreferencesChange({
        healthConditions: saved.health_conditions,
        allergens: saved.allergens,
        expertiseLevel: saved.expertise_level,
      });
      setNotice(
        "Preferences saved. Unsupported health concerns remain unevaluated."
      );
    } catch (requestError) {
      if (requestError.status !== 401) {
        setError(
          requestError instanceof TypeError
            ? `Could not connect to the Label Lens API at ${apiBaseUrl}.`
            : requestError.message
        );
      }
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    onAuthChange("");
    onOpenChange(false);
    setProfile(null);
    setDraftHealthConditions([]);
    setDraftAllergens([]);
    setDraftExpertiseLevel("beginner");
    setError("");
    setNotice("");
  }

  return (
    <div className="account-control">
      <button
        type="button"
        className="account-trigger"
        aria-expanded={isOpen}
        aria-controls="account-preferences-panel"
        onClick={() => onOpenChange(!isOpen)}
      >
        {accessToken ? "Health preferences" : "Sign in"}
      </button>
      {isOpen && (
        <aside
          className="account-popover"
          id="account-preferences-panel"
          aria-label={accessToken ? "Health and allergy preferences" : "Account sign in"}
        >
          <div className="account-popover-heading">
            <div>
              <p className="eyebrow">{accessToken ? "YOUR ACCOUNT" : "PERSONALIZED ANALYSIS"}</p>
              <h2>{accessToken ? "Health preferences" : "Sign in or create an account"}</h2>
            </div>
            <button
              type="button"
              className="account-close"
              aria-label="Close account panel"
              onClick={() => onOpenChange(false)}
            >
              ×
            </button>
          </div>
          {sessionExpired && (
            <p className="legacy-api-notice" role="status">
              Your session expired. Sign in again to access private preferences.
            </p>
          )}
          {onboardingError && (
            <p className="legacy-api-notice" role="status">
              {onboardingError}
            </p>
          )}
          {accessToken ? (
            profile ? (
              <form className="account-preferences-form" onSubmit={saveProfile}>
                <label className="input-group">
                  <span className="input-label">Profile name</span>
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    required
                    maxLength={160}
                  />
                </label>
                <label className="input-group">
                  <span className="input-label">Explanation detail</span>
                  <select
                    value={draftExpertiseLevel}
                    onChange={(event) =>
                      setDraftExpertiseLevel(event.target.value)
                    }
                  >
                    <option value="beginner">Beginner</option>
                    <option value="expert">Expert</option>
                  </select>
                </label>
                <HealthPreferencePicker
                  compact
                  healthConditions={draftHealthConditions}
                  allergens={draftAllergens}
                  onHealthConditionsChange={setDraftHealthConditions}
                  onAllergensChange={setDraftAllergens}
                />
                <p className="muted-copy">
                  Preferences are stored with your account and used only when
                  you are signed in. Unsupported conditions are not medically
                  evaluated.
                </p>
                <div className="account-actions">
                  <Button type="submit" disabled={busy}>
                    {busy ? "Saving…" : "Save preferences"}
                  </Button>
                  <Button
                    type="button"
                    className="secondary-button"
                    onClick={signOut}
                  >
                    Sign out
                  </Button>
                </div>
              </form>
            ) : (
              <p role="status">Loading your saved preferences…</p>
            )
          ) : (
            <form className="account-content" onSubmit={submitAccount}>
              <div className="account-mode-toggle" role="group" aria-label="Account action">
                <button
                  type="button"
                  aria-pressed={mode === "login"}
                  onClick={() => setMode("login")}
                >
                  Sign in
                </button>
                <button
                  type="button"
                  aria-pressed={mode === "register"}
                  onClick={() => setMode("register")}
                >
                  Create account
                </button>
              </div>
              {mode === "register" && (
                <label className="input-group">
                  <span className="input-label">Name</span>
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    required
                    maxLength={160}
                    autoComplete="name"
                  />
                </label>
              )}
              <label className="input-group">
                <span className="input-label">Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  autoComplete="email"
                />
              </label>
              <label className="input-group">
                <span className="input-label">Password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  minLength={mode === "register" ? 12 : 1}
                  maxLength={128}
                  autoComplete={mode === "register" ? "new-password" : "current-password"}
                />
              </label>
              <p className="muted-copy">
                Health and allergy selections are sensitive information and are
                saved only to your private account.
              </p>
              <Button type="submit" disabled={busy}>
                {busy
                  ? "Please wait…"
                  : mode === "register"
                    ? "Create account"
                    : "Sign in"}
              </Button>
            </form>
          )}
          {notice && <p className="success-message" role="status">{notice}</p>}
          {error && <p className="form-error" role="alert">{error}</p>}
        </aside>
      )}
    </div>
  );
}
