import React from "react";
import BenchmarkCard from "../shared/BenchmarkCard.jsx";
import BarChartCard from "../shared/BarChartCard.jsx";

export default function BenchmarksView({ benchmark, recommendation, projectBrief }) {
  const quantumNotes = projectBrief?.quantum_value?.points || [];
  const limitNotes = projectBrief?.quantum_limits?.points || [];
  const decisionNotes = projectBrief?.decision_guidance?.points || [];
  const approachComparison = projectBrief?.approach_comparison;
  const familySummary = benchmark?.family_summary || [];

  return (
    <div className="page-grid">
      <section className="panel-card wide-callout">
        <p className="eyebrow">Recommended Pipeline</p>
        <h3>{`${recommendation.detector_backend || "pending"} + ${recommendation.classifier_name} + ${recommendation.ocr_backend}`}</h3>
        <p>
          The system picks this stack from the current benchmark report when available, otherwise it falls back to the
          best local artifacts.
        </p>
        <p>{`Winning classifier family: ${recommendation.classifier_family || "unknown"}`}</p>
      </section>

      <section className="card-grid three">
        <BarChartCard
          title="Classifier Accuracy"
          subtitle="Top models by held-out accuracy"
          items={benchmark?.charts?.classifier_accuracy_pct || []}
          suffix="%"
          emptyText="No classifier benchmark data yet."
        />
        <BarChartCard
          title="Macro F1"
          subtitle="Balanced quality across classes"
          items={benchmark?.charts?.classifier_macro_f1_pct || []}
          suffix="%"
          emptyText="No macro F1 data yet."
        />
        <BarChartCard
          title="Training Time"
          subtitle="Saved for cost and presentation tradeoffs"
          items={benchmark?.charts?.classifier_train_time_s || []}
          suffix=" s"
          emptyText="No training-time data yet."
        />
      </section>

      <section className="card-grid three">
        {(familySummary || []).map((item) => (
          <div className="panel-card family-card" key={item.family}>
            <p className="eyebrow">Family Summary</p>
            <h3>{item.family}</h3>
            <div className="detail-list compact">
              <div>
                <span>Best Model</span>
                <strong>{item.best_model}</strong>
              </div>
              <div>
                <span>Best Accuracy</span>
                <strong>{`${(item.best_accuracy * 100).toFixed(2)}%`}</strong>
              </div>
              <div>
                <span>Average Accuracy</span>
                <strong>{`${(item.avg_accuracy * 100).toFixed(2)}%`}</strong>
              </div>
              <div>
                <span>Models Count</span>
                <strong>{item.count}</strong>
              </div>
            </div>
          </div>
        ))}
      </section>

      <section className="card-grid three">
        <BenchmarkCard title="Overall Leaderboard" rows={benchmark.overall} emptyText="No overall benchmark entries yet." />
        <BenchmarkCard title="Detector Benchmarks" rows={benchmark.detectors} emptyText="No detector summary files yet." />
        <BenchmarkCard title="Classifier Benchmarks" rows={benchmark.classifiers} emptyText="No classifier summary files yet." />
      </section>

      <section className="card-grid two">
        <div className="panel-card">
          <p className="eyebrow">Why Quantum Can Matter</p>
          <h3>Use this in the presentation</h3>
          <div className="briefing-list">
            {quantumNotes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        </div>
        <div className="panel-card">
          <p className="eyebrow">Limits and Tradeoffs</p>
          <h3>Be transparent about the research story</h3>
          <div className="briefing-list">
            {limitNotes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        </div>
      </section>

      {approachComparison?.rows?.length ? (
        <section className="panel-card">
          <p className="eyebrow">Classical vs Hybrid vs Quantum</p>
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
        <p className="eyebrow">Recommendation Guidance</p>
        <h3>What is better to do</h3>
        <div className="briefing-list">
          {decisionNotes.map((note) => (
            <p key={note}>{note}</p>
          ))}
        </div>
      </section>

      <section className="card-grid one">
        <BenchmarkCard title="OCR Benchmarks" rows={benchmark.ocr} emptyText="OCR benchmark entries are not available yet." fullWidth />
      </section>
    </div>
  );
}
