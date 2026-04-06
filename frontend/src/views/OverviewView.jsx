import React from "react";
import ActionCard from "../shared/ActionCard.jsx";
import BarChartCard from "../shared/BarChartCard.jsx";
import ScatterPlotCard from "../shared/ScatterPlotCard.jsx";

function formatPercent(value) {
  return Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(2)}%` : "N/A";
}

function bestByFamily(rows, family) {
  return (rows || []).find((item) => item.model_family === family) || null;
}

export default function OverviewView({ dashboard, recommendation, benchmark, projectBrief, onJump }) {
  const classifiers = benchmark.classifiers || [];
  const detector = benchmark.detectors?.[0] || null;
  const bestClassical = bestByFamily(classifiers, "classical");
  const bestQuantum = bestByFamily(classifiers, "quantum");
  const executiveSummary = projectBrief?.executive_summary?.points || [];
  const problemStatement = projectBrief?.problem_statement?.points || [];
  const quantumValue = projectBrief?.quantum_value?.points || [];
  const quantumLimits = projectBrief?.quantum_limits?.points || [];
  const overviewScatterItems = classifiers.map((item) => ({
    label: item.name,
    x: item.train_time_seconds,
    y: Number(item.accuracy || 0) * 100,
    family: item.model_family,
  }));

  return (
    <div className="page-grid">
      <section className="hero-panel overview-hero">
        <div className="hero-main">
          <p className="eyebrow">Research Dashboard</p>
          <h3>Hybrid quantum vs classical benchmarking for object detection and OCR pipelines</h3>
          <p>
            This workspace is designed as a research control room for QML object-detection experiments. It combines
            training, benchmarking, and inference into one presentation-ready interface so you can explain both the
            technical pipeline and the research findings clearly.
          </p>
          <div className="hero-actions">
            <button className="primary-btn" type="button" onClick={() => onJump("benchmarks")}>
              Review Benchmarks
            </button>
            <button className="secondary-btn" type="button" onClick={() => onJump("inference")}>
              Open Demo Output
            </button>
          </div>
          <div className="hero-note-grid">
            <div className="hero-note-card">
              <span>Production Recommendation</span>
              <strong>{recommendation.classifier_name}</strong>
            </div>
            <div className="hero-note-card">
              <span>Research Best Quantum Entry</span>
              <strong>{bestQuantum?.name || "Not available yet"}</strong>
            </div>
          </div>
        </div>

        <div className="hero-side metric-stack">
          <div className="metric-card accent">
            <span>Benchmark Winner</span>
            <strong>{recommendation.classifier_name}</strong>
            <small>{`${recommendation.classifier_family || "unknown"} family`}</small>
          </div>
          <div className="metric-card">
            <span>Best Classical Accuracy</span>
            <strong>{bestClassical ? formatPercent(bestClassical.accuracy) : "N/A"}</strong>
            <small>{bestClassical?.name || "No model yet"}</small>
          </div>
          <div className="metric-card">
            <span>Best Quantum Accuracy</span>
            <strong>{bestQuantum ? formatPercent(bestQuantum.accuracy) : "N/A"}</strong>
            <small>{bestQuantum?.name || "No model yet"}</small>
          </div>
          <div className="metric-card">
            <span>Detector mAP50-95</span>
            <strong>{detector ? formatPercent(detector.accuracy) : "N/A"}</strong>
            <small>{detector?.name || "Detector pending"}</small>
          </div>
        </div>
      </section>

      <section className="overview-kpi-grid">
        <div className="kpi-panel">
          <span>Total Saved ROI Models</span>
          <strong>{dashboard.available_models?.length || 0}</strong>
          <p>Reusable trained artifacts available for comparison and inference.</p>
        </div>
        <div className="kpi-panel">
          <span>Benchmark Coverage</span>
          <strong>{classifiers.length}</strong>
          <p>Classifier entries currently included in the benchmark report.</p>
        </div>
        <div className="kpi-panel">
          <span>Detector Artifacts</span>
          <strong>{dashboard.inventory?.detector_weights?.length || 0}</strong>
          <p>Saved detector weights available for full-scene object localization.</p>
        </div>
        <div className="kpi-panel">
          <span>Inference Mode</span>
          <strong>{recommendation.mode || "unavailable"}</strong>
          <p>{recommendation.ready ? "Inference is enabled." : "Training or artifacts are still required."}</p>
        </div>
      </section>

      <section className="card-grid three">
        <BarChartCard
          title="Top Accuracy Snapshot"
          subtitle="Best benchmark performers"
          items={benchmark?.charts?.classifier_accuracy_pct || []}
          suffix="%"
          limit={6}
          emptyText="No classifier benchmark data yet."
        />
        <BarChartCard
          title="Family Average Accuracy"
          subtitle="Classical vs quantum"
          items={benchmark?.charts?.family_avg_accuracy_pct || []}
          suffix="%"
          limit={4}
          emptyText="Family comparison appears after benchmarking."
        />
        <BarChartCard
          title="Detector Quality"
          subtitle="Detection benchmark"
          items={benchmark?.charts?.detector_map_pct || []}
          suffix="%"
          limit={4}
          emptyText="Detector chart appears after detector training."
        />
      </section>

      <section className="card-grid two">
        <ScatterPlotCard
          title="Accuracy vs Training Time"
          subtitle="Research tradeoff view"
          items={overviewScatterItems}
          emptyText="Train ROI models to populate the comparison scatter."
        />
        <div className="panel-card insight-card">
          <p className="eyebrow">Executive Research Notes</p>
          <h3>How to explain the project in one minute</h3>
          <div className="briefing-list">
            {executiveSummary.map((point) => (
              <p key={point}>{point}</p>
            ))}
          </div>
        </div>
      </section>

      <section className="card-grid three">
        <ActionCard
          title="Step 1"
          subtitle="Train the experiment suite"
          text="Build detector and ROI classifier artifacts, or reuse the saved models already in the workspace."
          onClick={() => onJump("training")}
        />
        <ActionCard
          title="Step 2"
          subtitle="Read the benchmark board"
          text="Compare classical, hybrid quantum, and variational approaches with graphs, rankings, and research notes."
          onClick={() => onJump("benchmarks")}
        />
        <ActionCard
          title="Step 3"
          subtitle="Run the live demo"
          text="Upload an image, render the final output, and review extracted text with per-model comparison tables."
          onClick={() => onJump("inference")}
        />
      </section>

      <section className="card-grid two">
        <div className="panel-card briefing-card">
          <p className="eyebrow">Problem Context</p>
          <h3>Why this research matters</h3>
          <div className="briefing-list">
            {problemStatement.map((point) => (
              <p key={point}>{point}</p>
            ))}
          </div>
        </div>
        <div className="panel-card briefing-card">
          <p className="eyebrow">Quantum Opportunity</p>
          <h3>Where hybrid QML can add value</h3>
          <div className="briefing-list">
            {quantumValue.map((point) => (
              <p key={point}>{point}</p>
            ))}
          </div>
        </div>
      </section>

      <section className="card-grid two">
        <div className="panel-card briefing-card muted-surface">
          <p className="eyebrow">Current Limits</p>
          <h3>What still constrains quantum use today</h3>
          <div className="briefing-list">
            {quantumLimits.map((point) => (
              <p key={point}>{point}</p>
            ))}
          </div>
        </div>
        <div className="panel-card recommendation-panel">
          <p className="eyebrow">Current Recommendation</p>
          <h3>{recommendation.classifier_name}</h3>
          <p>
            The current recommended stack is selected from measured benchmark results, not from assumptions. That makes
            the recommendation useful for both production decisions and research reporting.
          </p>
          <div className="detail-list">
            <div>
              <span>Classifier Family</span>
              <strong>{recommendation.classifier_family || "unknown"}</strong>
            </div>
            <div>
              <span>Inference Status</span>
              <strong>{recommendation.ready ? "Ready" : "Pending"}</strong>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
