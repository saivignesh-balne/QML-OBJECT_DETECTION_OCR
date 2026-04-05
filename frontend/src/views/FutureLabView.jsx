import React from "react";

export default function FutureLabView({ projectBrief, recommendation, benchmark, modelCatalog }) {
  const sections = Object.values(projectBrief || {}).filter((section) => Array.isArray(section?.points));
  const approachComparison = projectBrief?.approach_comparison;

  return (
    <div className="page-grid">
      <section className="panel-card">
        <p className="eyebrow">Project Brief</p>
        <h3>Presentation notes for the manager review</h3>
        <p>
          This page explains the reasoning behind the system design, when quantum models can help, where they fall short,
          and how the benchmark board should be interpreted.
        </p>
      </section>

      <section className="card-grid two">
        {sections.map((section) => (
          <div className="panel-card model-room" key={section.title}>
            <h4>{section.title}</h4>
            <div className="briefing-list">
              {section.points.map((point) => (
                <p key={point}>{point}</p>
              ))}
            </div>
            <span className="room-tag">briefing</span>
          </div>
        ))}
      </section>

      {approachComparison?.rows?.length ? (
        <section className="panel-card">
          <p className="eyebrow">Approach Comparison</p>
          <h3>{approachComparison.title}</h3>
          <div className="table-wrap">
            <table className="result-table">
              <thead>
                <tr>
                  {approachComparison.columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {approachComparison.rows.map((row) => (
                  <tr key={row.approach}>
                    <td>{row.approach}</td>
                    <td>{row.how}</td>
                    <td>{row.advantages}</td>
                    <td>{row.disadvantages}</td>
                    <td>{row.best_use}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="card-grid two">
        <div className="panel-card">
          <p className="eyebrow">Current Winner</p>
          <h3>{recommendation.classifier_name}</h3>
          <p>{`Classifier family: ${recommendation.classifier_family || "unknown"}`}</p>
          <p>
            {recommendation.classifier_family === "quantum"
              ? "The current benchmark winner is a quantum-ready model, so quantum methods are adding measurable value on this dataset."
              : "The current benchmark winner is a classical baseline, which is a useful finding because it sets the performance bar for the quantum experiments."}
          </p>
        </div>
        <div className="panel-card">
          <p className="eyebrow">Benchmark Narrative</p>
          <h3>How to explain the comparison</h3>
          <div className="briefing-list">
            {(benchmark.notes || []).map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        </div>
      </section>

      <section className="panel-card">
        <p className="eyebrow">Model Notes</p>
        <h3>How to explain the comparison families</h3>
        <div className="catalog-grid">
          {(modelCatalog || []).map((item) => (
            <article className="catalog-card" key={item.model_type}>
              <div className="step-row">
                <strong>{item.display_name}</strong>
                <span className={`family-chip ${item.family}`}>{item.family}</span>
              </div>
              <p>{item.summary}</p>
              <p className="hint-text">{`Strength: ${item.strengths}`}</p>
              <p className="hint-text">{`Limit: ${item.limitations}`}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
