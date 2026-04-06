import React from "react";

export default function FutureLabView({ projectBrief, recommendation, benchmark, modelCatalog }) {
  const sections = Object.values(projectBrief || {}).filter((section) => Array.isArray(section?.points));
  const approachComparison = projectBrief?.approach_comparison;

  return (
    <div className="page-grid">
      <section className="panel-card">
        <p className="eyebrow">Research Briefing</p>
        <h3>Presentation-ready notes for review, manager discussion, and project defense</h3>
        <p>
          This page reframes the platform as a QML object-detection research and development project. It helps explain
          why hybrid quantum methods are being tested, where classical methods currently win, and how the comparison
          should be interpreted professionally.
        </p>
      </section>

      <section className="card-grid two">
        {sections.map((section) => (
          <div className="panel-card model-room" key={section.title}>
            <div className="panel-title-row">
              <h4>{section.title}</h4>
              <span className="room-tag">briefing</span>
            </div>
            <div className="briefing-list">
              {section.points.map((point) => (
                <p key={point}>{point}</p>
              ))}
            </div>
          </div>
        ))}
      </section>

      {approachComparison?.rows?.length ? (
        <section className="panel-card">
          <p className="eyebrow">Approach Matrix</p>
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
              ? "The current benchmark winner is quantum-oriented, which means the research track is already providing measurable value on this dataset."
              : "The current benchmark winner is a classical baseline, which is still a strong research outcome because it defines the real bar that quantum methods must beat or complement."}
          </p>
        </div>
        <div className="panel-card">
          <p className="eyebrow">Benchmark Narrative</p>
          <h3>How to present the findings</h3>
          <div className="briefing-list">
            {(benchmark.notes || []).map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        </div>
      </section>

      <section className="panel-card">
        <p className="eyebrow">Model Family Notes</p>
        <h3>How to talk about the compared models</h3>
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
