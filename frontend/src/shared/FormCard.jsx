import React from "react";

export default function FormCard({
  title,
  subtitle,
  fields,
  data,
  onChange,
  onSubmit,
  submitLabel,
  disabled,
  submitDisabled,
  message,
  messageTone = "warning",
}) {
  function normalizeOption(option) {
    if (typeof option === "string") {
      return { value: option, label: option };
    }
    return option;
  }

  return (
    <div className="panel-card">
      <p className="eyebrow">{subtitle}</p>
      <h3>{title}</h3>
      <div className="form-grid">
        {fields.map((field) => (
          <label className="field" key={field.key}>
            <span>{field.label}</span>
            {field.type === "select" ? (
              <select
                value={data[field.key]}
                disabled={disabled}
                onChange={(event) => onChange((current) => ({ ...current, [field.key]: event.target.value }))}
              >
                {field.options.map((option) => {
                  const normalized = normalizeOption(option);
                  return (
                    <option key={normalized.value} value={normalized.value}>
                      {normalized.label}
                    </option>
                  );
                })}
              </select>
            ) : (
              <input
                value={data[field.key]}
                disabled={disabled}
                onChange={(event) => onChange((current) => ({ ...current, [field.key]: event.target.value }))}
              />
            )}
          </label>
        ))}
      </div>
      {message ? <p className={`form-note ${messageTone}`}>{message}</p> : null}
      <button
        className="primary-btn"
        type="button"
        onClick={onSubmit}
        disabled={submitDisabled ?? disabled}
      >
        {submitLabel}
      </button>
    </div>
  );
}
