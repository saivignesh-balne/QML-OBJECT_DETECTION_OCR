import React from "react";
import ActionCard from "../shared/ActionCard.jsx";

export default function OverviewView({ dashboard, recommendation, benchmark, projectBrief, onJump }) {
  const briefingCards = Object.values(projectBrief || {}).filter((section) => Array.isArray(section?.points));
  const approachComparison = projectBrief?.approach_comparison;
  const topModels = (dashboard.available_models || []).slice(0, 3);

  return (
    <div className="page-grid">
      <section className="hero-panel">
        <div className="hero-main">
          <p className="eyebrow">Presentation-Ready Vision + OCR Lab</p>
          <h3>Compare classical and quantum-ready models, then deploy the strongest pipeline from one UI.</h3>
          <p>
            The workspace now supports saved artifacts, benchmark-driven model selection, OCR visualization, and
            side-by-side comparison of classical baselines with hybrid quantum classifiers.
          </p>
          <div className="hero-actions">
            <button className="primary-btn" type="button" onClick={() => onJump("training")}>
              Train Models
            </button>
            <button className="secondary-btn" type="button" onClick={() => onJump("inference")}>
              Open Inference Lab
            </button>
          </div>
        </div>
        <div className="hero-side">
          <div className="metric-card">
            <span>Detector Weights</span>
            <strong>{dashboard.inventory.detector_weights.length}</strong>
          </div>
          <div className="metric-card">
            <span>Classifier Artifacts</span>
            <strong>{dashboard.inventory.classifier_artifacts.length}</strong>
          </div>
          <div className="metric-card">
            <span>Benchmark Ready</span>
            <strong>{benchmark.has_report ? "Yes" : "No"}</strong>
          </div>
          <div className="metric-card accent">
            <span>Inference</span>
            <strong>{recommendation.ready ? "Unlocked" : "Waiting"}</strong>
          </div>
          <div className="metric-card">
            <span>Saved Models</span>
            <strong>{dashboard.available_models?.length || 0}</strong>
          </div>
        </div>
      </section>

      <section className="card-grid three">
        <ActionCard
          title="Step 1"
          subtitle="Train comparison models"
          text="Train classical baselines and hybrid quantum classifiers from the UI, then reuse the saved artifacts."
          onClick={() => onJump("training")}
        />
        <ActionCard
          title="Step 2"
          subtitle="Benchmark the stack"
          text="Generate a benchmark report so the app can automatically recommend the strongest pipeline."
          onClick={() => onJump("benchmarks")}
        />
        <ActionCard
          title="Step 3"
          subtitle="Run inference"
          text="Upload a cropped image now, or add detector training later for full-scene detection."
          onClick={() => onJump("inference")}
        />
      </section>

      <section className="card-grid two">
        {briefingCards.map((section) => (
          <div className="panel-card briefing-card" key={section.title}>
            <p className="eyebrow">Project Brief</p>
            <h3>{section.title}</h3>
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
          <p className="eyebrow">Presentation Comparison</p>
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

      <section className="panel-card">
        <p className="eyebrow">Current Recommendation</p>
        <h3>{recommendation.classifier_name}</h3>
        <p>
          {`Current classifier family: ${recommendation.classifier_family || "unknown"}. The benchmark board decides whether classical or quantum wins on the current dataset.`}
        </p>
        <p>
          {benchmark.notes?.[0] || "Benchmark notes will appear here after report generation."}
        </p>
      </section>

      <section className="card-grid three">
        {topModels.map((item) => (
          <div className="panel-card" key={item.artifact_path}>
            <p className="eyebrow">Top Saved Model</p>
            <h3>{item.display_name}</h3>
            <p>{item.summary}</p>
            <div className="detail-list compact">
              <div>
                <span>Accuracy</span>
                <strong>{`${(item.accuracy * 100).toFixed(2)}%`}</strong>
              </div>
              <div>
                <span>Family</span>
                <strong>{item.model_family}</strong>
              </div>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
