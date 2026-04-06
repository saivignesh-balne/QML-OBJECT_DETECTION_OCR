import React from "react";
import BenchmarkCard from "../shared/BenchmarkCard.jsx";
import BarChartCard from "../shared/BarChartCard.jsx";
import ScatterPlotCard from "../shared/ScatterPlotCard.jsx";

function formatPercent(value) {
  return Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(2)}%` : "N/A";
}

function findByFamily(rows, family) {
  return (rows || []).find((item) => item.model_family === family) || null;
}

export default function BenchmarksView({ benchmark, recommendation, projectBrief }) {
  const classifiers = benchmark.classifiers || [];
  const detectors = benchmark.detectors || [];
  const overall = benchmark.overall || [];
  const quantumNotes = projectBrief?.quantum_value?.points || [];
  const limitNotes = projectBrief?.quantum_limits?.points || [];
  const decisionNotes = projectBrief?.decision_guidance?.points || [];
  const approachComparison = projectBrief?.approach_comparison;
  const detector = detectors[0] || null;
  const bestOverall = overall[0] || null;
  const bestClassical = findByFamily(classifiers, "classical");
  const bestQuantum = findByFamily(classifiers, "quantum");
  const scatterItems = classifiers.map((item) => ({
    label: item.name,
    x: item.train_time_seconds,
    y: Number(item.accuracy || 0) * 100,
    family: item.model_family,
  }));

  return (
    <div className="page-grid">
      <section className="panel-card benchmark-hero">
        <div>
          <p className="eyebrow">Benchmark Control Board</p>
          <h3>{`${recommendation.detector_backend || "pending"} + ${recommendation.classifier_name} + ${recommendation.ocr_backend}`}</h3>
          <p>
            The benchmark board compares every saved classifier model on the same ROI dataset and surfaces the current
            best stack for the end-to-end pipeline.
          </p>
        </div>
        <div className="benchmark-hero-meta">
          <span className={`family-chip ${recommendation.classifier_family || "neutral"}`}>
            {recommendation.classifier_family || "unknown"}
          </span>
          <span className="chip">{benchmark.generated_at ? "report ready" : "report pending"}</span>
        </div>
      </section>

      <section className="overview-kpi-grid">
        <div className="kpi-panel">
          <span>Best Overall Pipeline</span>
          <strong>{bestOverall ? `${(Number(bestOverall.accuracy || 0) * 100).toFixed(2)}%` : "N/A"}</strong>
          <p>{bestOverall?.classifier_name || "No ranked pipeline yet"}</p>
        </div>
        <div className="kpi-panel">
          <span>Best Classical Model</span>
          <strong>{bestClassical ? formatPercent(bestClassical.accuracy) : "N/A"}</strong>
          <p>{bestClassical?.name || "No classical model yet"}</p>
        </div>
        <div className="kpi-panel">
          <span>Best Quantum Model</span>
          <strong>{bestQuantum ? formatPercent(bestQuantum.accuracy) : "N/A"}</strong>
          <p>{bestQuantum?.name || "No quantum model yet"}</p>
        </div>
        <div className="kpi-panel">
          <span>Detector mAP50-95</span>
          <strong>{detector ? formatPercent(detector.accuracy) : "N/A"}</strong>
          <p>{detector?.name || "Detector benchmark pending"}</p>
        </div>
      </section>

      <section className="card-grid three">
        <BarChartCard
          title="Accuracy by Model"
          subtitle="Held-out classifier accuracy"
          items={benchmark?.charts?.classifier_accuracy_pct || []}
          suffix="%"
          limit={10}
          emptyText="No classifier benchmark data yet."
        />
        <BarChartCard
          title="Macro F1 by Model"
          subtitle="Balanced class quality"
          items={benchmark?.charts?.classifier_macro_f1_pct || []}
          suffix="%"
          limit={10}
          emptyText="No macro F1 data yet."
        />
        <BarChartCard
          title="Training Time by Model"
          subtitle="Cost and practicality"
          items={benchmark?.charts?.classifier_train_time_s || []}
          suffix=" s"
          limit={10}
          emptyText="No training-time data yet."
        />
      </section>

      <section className="card-grid three">
        <BarChartCard
          title="Family Average Accuracy"
          subtitle="High-level family comparison"
          items={benchmark?.charts?.family_avg_accuracy_pct || []}
          suffix="%"
          limit={4}
          emptyText="Family summary appears after benchmarking."
        />
        <BarChartCard
          title="Detector Benchmark"
          subtitle="Localization quality"
          items={benchmark?.charts?.detector_map_pct || []}
          suffix="%"
          limit={4}
          emptyText="Detector chart appears after detector training."
        />
        <ScatterPlotCard
          title="Accuracy vs Training Time"
          subtitle="Research tradeoff map"
          items={scatterItems}
          emptyText="Train ROI models to populate the scatter plot."
        />
      </section>

      <section className="panel-card">
        <p className="eyebrow">All Classifier Models</p>
        <h3>Full comparison table</h3>
        <div className="table-wrap">
          <table className="result-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Family</th>
                <th>Encoding</th>
                <th>Kernel / Ansatz</th>
                <th>Accuracy</th>
                <th>Macro F1</th>
                <th>Train Time</th>
              </tr>
            </thead>
            <tbody>
              {classifiers.map((row) => (
                <tr key={`${row.name}-${row.artifact_path}`}>
                  <td>
                    <strong>{row.name}</strong>
                    <div className="table-subline">{row.summary}</div>
                  </td>
                  <td>
                    <span className={`family-chip ${row.model_family}`}>{row.model_family}</span>
                  </td>
                  <td>{row.encoding}</td>
                  <td>{row.ansatz_name && row.ansatz_name !== "none" ? `${row.kernel_name} / ${row.ansatz_name}` : row.kernel_name}</td>
                  <td>{`${(Number(row.accuracy || 0) * 100).toFixed(2)}%`}</td>
                  <td>{`${(Number(row.macro_f1 || 0) * 100).toFixed(2)}%`}</td>
                  <td>{`${Number(row.train_time_seconds || 0).toFixed(1)} s`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel-card">
        <p className="eyebrow">Overall Pipeline Leaderboard</p>
        <h3>End-to-end ranking view</h3>
        <div className="table-wrap">
          <table className="result-table">
            <thead>
              <tr>
                <th>Pipeline</th>
                <th>Family</th>
                <th>Composite Score</th>
                <th>Macro F1</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {overall.map((row, index) => (
                <tr key={`${row.pipeline}-${index}`}>
                  <td>
                    <strong>{row.pipeline}</strong>
                  </td>
                  <td>
                    <span className={`family-chip ${row.classifier_family || "neutral"}`}>
                      {row.classifier_family || "unknown"}
                    </span>
                  </td>
                  <td>{`${(Number(row.accuracy || 0) * 100).toFixed(2)}%`}</td>
                  <td>{`${(Number(row.macro_f1 || 0) * 100).toFixed(2)}%`}</td>
                  <td>{row.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card-grid two">
        <BenchmarkCard title="Detector Benchmarks" rows={detectors} emptyText="No detector summary files yet." />
        <BenchmarkCard title="OCR Benchmarks" rows={benchmark.ocr} emptyText="OCR benchmark entries are not available yet." />
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

      <section className="card-grid three">
        <div className="panel-card insight-card">
          <p className="eyebrow">Why Quantum Can Matter</p>
          <h3>Research justification</h3>
          <div className="briefing-list">
            {quantumNotes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        </div>
        <div className="panel-card insight-card">
          <p className="eyebrow">Limits and Tradeoffs</p>
          <h3>What to communicate honestly</h3>
          <div className="briefing-list">
            {limitNotes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        </div>
        <div className="panel-card insight-card">
          <p className="eyebrow">Recommended Direction</p>
          <h3>What is better to do next</h3>
          <div className="briefing-list">
            {decisionNotes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
