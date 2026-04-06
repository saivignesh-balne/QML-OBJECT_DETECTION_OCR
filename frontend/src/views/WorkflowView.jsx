import React from "react";

export default function WorkflowView({ flowSteps, activeStep, setActiveStep }) {
  const step = flowSteps[activeStep] || flowSteps[0];
  const total = flowSteps.length || 1;
  const progressPct = ((activeStep + 1) / total) * 100;

  return (
    <div className="page-grid workflow-layout">
      <section className="workflow-list panel-card">
        <div className="panel-title-row">
          <div>
            <p className="eyebrow">Workflow Navigator</p>
            <h3>Operating sequence</h3>
          </div>
          <span className="chip">{`${activeStep + 1}/${total}`}</span>
        </div>
        <div className="workflow-progress">
          <div className="workflow-progress-bar" style={{ width: `${progressPct}%` }} />
        </div>
        <div className="workflow-step-list">
          {flowSteps.map((item, index) => (
            <button
              key={item.title}
              type="button"
              className={`workflow-step ${activeStep === index ? "active" : ""}`}
              onClick={() => setActiveStep(index)}
            >
              <span className="workflow-index">{String(index + 1).padStart(2, "0")}</span>
              <div>
                <strong>{item.title}</strong>
                <p>{item.text}</p>
              </div>
            </button>
          ))}
        </div>
      </section>

      <section className="workflow-focus panel-card">
        <p className="eyebrow">Current Step</p>
        <h3>{step?.title}</h3>
        <p>{step?.text}</p>
        <div className="workflow-note-grid">
          <div className="workflow-note">
            <span>Current Stage</span>
            <strong>{`${activeStep + 1} of ${total}`}</strong>
          </div>
          <div className="workflow-note">
            <span>Best Practice</span>
            <strong>{activeStep < 2 ? "prepare inputs carefully" : "validate with benchmarks"}</strong>
          </div>
        </div>
        <div className="workflow-actions">
          <button
            className="secondary-btn"
            type="button"
            onClick={() => setActiveStep((current) => Math.max(0, current - 1))}
            disabled={activeStep === 0}
          >
            Previous
          </button>
          <button
            className="primary-btn"
            type="button"
            onClick={() => setActiveStep((current) => Math.min(flowSteps.length - 1, current + 1))}
            disabled={activeStep === flowSteps.length - 1}
          >
            Next Step
          </button>
        </div>
      </section>
    </div>
  );
}
