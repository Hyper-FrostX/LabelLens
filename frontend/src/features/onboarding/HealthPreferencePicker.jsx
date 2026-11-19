import {
  ALLERGEN_OPTIONS,
  HEALTH_CONDITION_OPTIONS,
  togglePreference,
} from "../nutrition/healthPreferences.js";

function ChoiceCards({ options, selectedValues, onChange, className }) {
  return (
    <div className={className}>
      {options.map((option) => {
        const selected = selectedValues.includes(option.value);
        return (
          <label
            className={`preference-card ${selected ? "selected" : ""}`}
            key={option.value}
          >
            <input
              type="checkbox"
              checked={selected}
              onChange={() =>
                onChange(togglePreference(selectedValues, option.value))
              }
            />
            <span className="preference-card-icon" aria-hidden="true">
              {option.icon}
            </span>
            <span className="preference-card-copy">
              <strong>{option.label}</strong>
              {option.detail && <small>{option.detail}</small>}
            </span>
            <span className="preference-card-check" aria-hidden="true">
              {selected ? "✓" : ""}
            </span>
          </label>
        );
      })}
    </div>
  );
}

export default function HealthPreferencePicker({
  healthConditions,
  allergens,
  onHealthConditionsChange,
  onAllergensChange,
  compact = false,
}) {
  return (
    <div className={`health-preference-picker ${compact ? "compact" : ""}`}>
      <section
        className="preference-section health-preference-section"
        aria-labelledby="health-preferences-title"
      >
        <div className="preference-section-heading">
          <span className="preference-section-icon" aria-hidden="true">+</span>
          <div>
            <h2 id="health-preferences-title">
              Health conditions
            </h2>
            <p>
              Select any health conditions that are relevant to you. This helps
              LabelLens identify ingredients and nutrients that may need your
              attention.
            </p>
          </div>
        </div>
        <ChoiceCards
          className="health-choice-grid"
          options={HEALTH_CONDITION_OPTIONS}
          selectedValues={healthConditions}
          onChange={onHealthConditionsChange}
        />
      </section>

      <section
        className="preference-section allergy-preference-section"
        aria-labelledby="allergy-preferences-title"
      >
        <div className="preference-section-heading">
          <span className="preference-section-icon allergy-icon" aria-hidden="true">
            !
          </span>
          <div>
            <h2 id="allergy-preferences-title">
              Do you have any food allergies?
            </h2>
            <p>
              Select the ingredients you are allergic to. LabelLens will
              highlight relevant allergens when analyzing food labels.
            </p>
          </div>
        </div>
        <ChoiceCards
          className="allergy-choice-grid"
          options={ALLERGEN_OPTIONS}
          selectedValues={allergens}
          onChange={onAllergensChange}
        />
      </section>
    </div>
  );
}
