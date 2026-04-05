import React from "react";

export default function WorkflowView({ flowSteps, activeStep, setActiveStep }) {
  const step = flowSteps[activeStep] || flowSteps[0];
  return (
    <div className="page-grid workflow-layout">
      <section className="workflow-list">
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
      </section>

      <section className="workflow-focus">
        <p className="eyebrow">Step by Step</p>
        <h3>{step?.title}</h3>
        <p>{step?.text}</p>
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
