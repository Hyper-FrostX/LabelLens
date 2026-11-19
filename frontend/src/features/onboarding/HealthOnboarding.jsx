import Button from "../../components/ui/Button";
import HealthPreferencePicker from "./HealthPreferencePicker";

export default function HealthOnboarding({
  healthConditions,
  allergens,
  onHealthConditionsChange,
  onAllergensChange,
  onContinue,
  onSkip,
  requiresSignIn,
  error,
  isSaving,
  editingMode = false,
  onSave,
  onBack,
  notice,
  noticeKind = "success",
}) {
  return (
    <main className="onboarding-page">
      <div className="onboarding-heading">
        <p className="eyebrow">
          {editingMode ? "YOUR PERSONAL PROFILE" : "PERSONALIZE YOUR LABEL REVIEW"}
        </p>
        <h1>
          {editingMode
            ? "Manage your health preferences"
            : "Let&apos;s understand your health needs"}
        </h1>
        <p>
          {editingMode
            ? "Update the health conditions and allergies you want included in your label analysis."
            : "Select any health conditions that are relevant to you. This helps LabelLens identify ingredients and nutrients that may need your attention."}
        </p>
      </div>
      {!editingMode && requiresSignIn && (
        <div className="onboarding-account-prompt" role="status">
          <strong>Sign in to save and use these preferences</strong>
          <span>
            Health and allergy selections are sensitive information. They are
            saved securely to your account, not to this browser.
          </span>
          {error && <span className="form-error" role="alert">{error}</span>}
        </div>
      )}
      <HealthPreferencePicker
        healthConditions={healthConditions}
        allergens={allergens}
        onHealthConditionsChange={onHealthConditionsChange}
        onAllergensChange={onAllergensChange}
      />
      {notice && (
        <p
          className={
            noticeKind === "error"
              ? "preference-notice preference-notice-error"
              : "preference-notice preference-notice-success"
          }
          role={noticeKind === "error" ? "alert" : "status"}
        >
          {notice}
        </p>
      )}
      {editingMode ? (
        <div className="preference-edit-actions">
          <Button
            type="button"
            disabled={isSaving}
            onClick={onSave}
          >
            {isSaving ? "Saving preferences…" : "Save Preferences"}
          </Button>
          <button
            type="button"
            className="back-to-analyzer-button"
            disabled={isSaving}
            onClick={onBack}
          >
            ← Back to Label Analyzer
          </button>
          {!requiresSignIn && (
            <p>
              You are not signed in. Changes apply to this session and are not
              saved to an account.
            </p>
          )}
        </div>
      ) : (
        <div className="onboarding-actions">
          <Button
            type="button"
            disabled={isSaving}
            onClick={onContinue}
          >
            {isSaving ? "Saving preferences…" : "Continue to Label Analyzer"}
          </Button>
          <button
            type="button"
            className="skip-onboarding-button"
            disabled={isSaving}
            onClick={onSkip}
          >
            Skip for now
          </button>
          {requiresSignIn && (
            <p>
              You can also skip and use Label Analyzer without saving personal
              preferences.
            </p>
          )}
        </div>
      )}
    </main>
  );
}
