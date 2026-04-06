import React, { useEffect, useRef, useState } from "react";
import { fetchJson } from "./api.js";
import OverviewView from "./views/OverviewView.jsx";
import WorkflowView from "./views/WorkflowView.jsx";
import TrainingView from "./views/TrainingView.jsx";
import BenchmarksView from "./views/BenchmarksView.jsx";
import InferenceView from "./views/InferenceView.jsx";
import FutureLabView from "./views/FutureLabView.jsx";

const NAV_ITEMS = [
  { id: "overview", label: "Overview", short: "01", description: "Research dashboard and executive snapshot" },
  { id: "workflow", label: "Workflow", short: "02", description: "Step-by-step operating flow" },
  { id: "training", label: "Training", short: "03", description: "Detector and ROI model training control" },
  { id: "benchmarks", label: "Benchmarks", short: "04", description: "Classical, quantum, and hybrid comparison" },
  { id: "inference", label: "Inference Lab", short: "05", description: "Upload, detect, classify, and extract text" },
  { id: "future", label: "Research Brief", short: "06", description: "Presentation-ready project notes" },
];

function formatPercent(value) {
  return Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(2)}%` : "N/A";
}

function formatDateTime(value) {
  if (!value) return "Not generated yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function App() {
  const [dashboard, setDashboard] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [activeView, setActiveView] = useState("overview");
  const [activeStep, setActiveStep] = useState(0);
  const [notice, setNotice] = useState(null);
  const [busyAction, setBusyAction] = useState("");
  const [uploadFile, setUploadFile] = useState(null);
  const [detectorForm, setDetectorForm] = useState({
    dataset_yaml: "",
    model: "yolov8n.pt",
    epochs: "50",
    imgsz: "960",
    batch: "8",
    project: "runs",
    name: "qml_ocr_detector",
    device: "cpu",
    summary_path: "artifacts/qml_ocr_detector.summary.json",
    reuse_existing: "true",
  });
  const [classifierForm, setClassifierForm] = useState({
    dataset_dir: "",
    artifact_path: "artifacts/hybrid_qml_classifier.pkl",
    model_type: "qsvc",
    encoding: "angle",
    n_qubits: "6",
    test_size: "0.2",
    device: "cpu",
    summary_path: "artifacts/hybrid_qml_classifier.summary.json",
    reuse_existing: "true",
  });
  const [suiteForm, setSuiteForm] = useState({
    dataset_dir: "",
    artifacts_dir: "artifacts",
    profile: "core",
    test_size: "0.2",
    device: "cpu",
    reuse_existing: "true",
  });
  const [inferenceForm, setInferenceForm] = useState({
    mode: "recommended",
    classifier_artifact: "",
  });

  const previousTraining = useRef(false);

  async function loadDashboard() {
    const data = await fetchJson("/api/dashboard");
    setDashboard(data);
    if (data.path_hints) {
      setDetectorForm((current) => ({
        ...current,
        dataset_yaml: current.dataset_yaml || data.path_hints.detector_dataset_yaml,
        model: data.path_hints.detector_base_model || current.model,
        project: data.path_hints.detector_project || current.project,
        name: data.path_hints.detector_name || current.name,
      }));
      setClassifierForm((current) => ({
        ...current,
        dataset_dir: current.dataset_dir || data.path_hints.classifier_dataset_dir,
        artifact_path: data.path_hints.classifier_artifact_path || current.artifact_path,
        summary_path: data.path_hints.classifier_summary_path || current.summary_path,
      }));
      setSuiteForm((current) => ({
        ...current,
        dataset_dir: current.dataset_dir || data.path_hints.classifier_dataset_dir,
        artifacts_dir: data.path_hints.classifier_suite_artifacts_dir || current.artifacts_dir,
      }));
      setInferenceForm((current) => ({
        ...current,
        classifier_artifact:
          current.classifier_artifact ||
          data.recommendation?.classifier_artifact ||
          data.available_models?.[0]?.artifact_path ||
          "",
      }));
    }
  }

  useEffect(() => {
    loadDashboard().catch((error) => setNotice({ tone: "error", text: error.message }));
  }, []);

  useEffect(() => {
    const timer = window.setInterval(async () => {
      try {
        const status = await fetchJson("/api/status");
        setDashboard((current) => {
          if (!current) return current;
          return { ...current, training_status: status };
        });
        if (previousTraining.current && !status.training) {
          loadDashboard().catch(() => {});
        }
        previousTraining.current = Boolean(status.training);
      } catch (error) {
        console.error(error);
      }
    }, 2500);
    return () => window.clearInterval(timer);
  }, []);

  async function postJson(url, payload, successTargetView) {
    setBusyAction(successTargetView);
    try {
      const result = await fetchJson(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setNotice({ tone: "success", text: result.message });
      await loadDashboard();
      return true;
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
      return false;
    } finally {
      setBusyAction("");
    }
  }

  async function runAnalysis() {
    if (!uploadFile) {
      setNotice({ tone: "error", text: "Choose an image first." });
      return;
    }
    setBusyAction("analysis");
    try {
      const formData = new FormData();
      formData.append("image", uploadFile);
      formData.append("inference_mode", inferenceForm.mode);
      formData.append("classifier_artifact", inferenceForm.classifier_artifact || "");
      const result = await fetchJson("/api/analyze", {
        method: "POST",
        body: formData,
      });
      setAnalysis(result.analysis);
      setActiveView("inference");
      setNotice({ tone: "success", text: "Pipeline analysis completed." });
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
    } finally {
      setBusyAction("");
    }
  }

  if (!dashboard) {
    return (
      <div className="app-loading">
        <div className="loading-orb" />
        <div>
          <p className="eyebrow">QML Vision Research Console</p>
          <h1>Preparing the workspace</h1>
        </div>
      </div>
    );
  }

  const trainingStatus = dashboard.training_status || { training: false, status_messages: [] };
  const recommendation = dashboard.recommendation || {};
  const benchmark = dashboard.benchmark || {};
  const familySummary = benchmark.family_summary || [];
  const classicalSummary = familySummary.find((item) => item.family === "classical");
  const quantumSummary = familySummary.find((item) => item.family === "quantum");
  const activeNav = NAV_ITEMS.find((item) => item.id === activeView) || NAV_ITEMS[0];
  const benchmarkGeneratedAt = formatDateTime(benchmark.generated_at);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">QV</div>
          <div>
            <p className="eyebrow">Research UI</p>
            <h1>Quantum Vision Studio</h1>
            <p className="brand-copy">QML object-detection, benchmarking, and OCR research workspace</p>
          </div>
        </div>

        <div className="sidebar-card sidebar-highlight">
          <span className="sidebar-label">Research Focus</span>
          <strong>Hybrid quantum vs classical comparison for object detection workflows</strong>
          <p>
            The UI is organized around model training, measurable benchmarking, and presentation-ready inference
            results.
          </p>
        </div>

        <nav className="side-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`side-nav-item ${activeView === item.id ? "active" : ""}`}
              onClick={() => setActiveView(item.id)}
              type="button"
            >
              <span className="nav-badge">{item.short}</span>
              <span className="nav-text">
                <strong>{item.label}</strong>
                <small>{item.description}</small>
              </span>
            </button>
          ))}
        </nav>

        <div className="sidebar-metric-grid">
          <div className="sidebar-stat">
            <span>Saved ROI Models</span>
            <strong>{dashboard.available_models?.length || 0}</strong>
          </div>
          <div className="sidebar-stat">
            <span>Detector Runs</span>
            <strong>{dashboard.inventory?.detector_weights?.length || 0}</strong>
          </div>
          <div className="sidebar-stat">
            <span>Best Classical</span>
            <strong>{classicalSummary ? formatPercent(classicalSummary.best_accuracy) : "N/A"}</strong>
          </div>
          <div className="sidebar-stat">
            <span>Best Quantum</span>
            <strong>{quantumSummary ? formatPercent(quantumSummary.best_accuracy) : "N/A"}</strong>
          </div>
        </div>

        <div className="sidebar-card">
          <span className="sidebar-label">Recommended Stack</span>
          <strong>{`${recommendation.detector_backend || "pending"} + ${recommendation.classifier_name} + ${recommendation.ocr_backend}`}</strong>
          <p>
            {recommendation.mode === "classifier_only"
              ? "ROI-only upload mode is available now. Add detector weights for full-scene operation."
              : recommendation.ready
                ? "Full pipeline inference is ready with benchmark-guided model selection."
                : "Train models or add artifacts to unlock inference."}
          </p>
          <p>{`Benchmark report: ${benchmarkGeneratedAt}`}</p>
        </div>

        <div className="sidebar-card muted">
          <span className="sidebar-label">Supported Classes</span>
          <div className="stacked-chips">
            {(dashboard.supported_classes || []).map((item) => (
              <span key={item} className="chip">
                {item}
              </span>
            ))}
            <span className="chip ghost">others = unidentified</span>
          </div>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="topbar-copy">
            <p className="eyebrow">QML Object Detection Research and Development</p>
            <h2>{activeNav.label}</h2>
            <p>{activeNav.description}</p>
          </div>
          <div className="topbar-status">
            <div className={`status-pill ${benchmark.has_report ? "good" : "warn"}`}>
              {benchmark.has_report ? "Benchmark Ready" : "Benchmark Pending"}
            </div>
            <div className={`status-pill ${trainingStatus.training ? "warn" : "good"}`}>
              {trainingStatus.training ? "Training Running" : "System Idle"}
            </div>
            <button className="ghost-btn" type="button" onClick={() => loadDashboard()}>
              Refresh Data
            </button>
          </div>
        </header>

        {notice ? (
          <div className={`notice ${notice.tone}`}>
            <span>{notice.text}</span>
            <button type="button" onClick={() => setNotice(null)}>
              Dismiss
            </button>
          </div>
        ) : null}

        {activeView === "overview" ? (
          <OverviewView
            dashboard={dashboard}
            recommendation={recommendation}
            benchmark={benchmark}
            projectBrief={dashboard.project_brief}
            onJump={setActiveView}
          />
        ) : null}

        {activeView === "workflow" ? (
          <WorkflowView
            flowSteps={dashboard.flow_steps || []}
            activeStep={activeStep}
            setActiveStep={setActiveStep}
          />
        ) : null}

        {activeView === "training" ? (
          <TrainingView
            detectorForm={detectorForm}
            setDetectorForm={setDetectorForm}
            classifierForm={classifierForm}
            setClassifierForm={setClassifierForm}
            suiteForm={suiteForm}
            setSuiteForm={setSuiteForm}
            datasetStatus={dashboard.dataset_status}
            trainingStatus={trainingStatus}
            busyAction={busyAction}
            modelCatalog={dashboard.model_catalog}
            availableModels={dashboard.available_models}
            detectorWeights={dashboard.inventory?.detector_weights || []}
            onRunDetector={() => postJson("/api/train/detector", detectorForm, "detector")}
            onRunClassifier={() => postJson("/api/train/classifier", classifierForm, "classifier")}
            onRunSuite={() => postJson("/api/train/classifier-suite", suiteForm, "suite")}
            onRunAllModels={() => postJson("/api/train/classifier-suite", { ...suiteForm, profile: "all_models" }, "suite")}
            onBuildBenchmark={() => postJson("/api/benchmark/generate", {}, "benchmark")}
          />
        ) : null}

        {activeView === "benchmarks" ? (
          <BenchmarksView benchmark={benchmark} recommendation={recommendation} projectBrief={dashboard.project_brief} />
        ) : null}

        {activeView === "inference" ? (
          <InferenceView
            recommendation={recommendation}
            analysis={analysis}
            uploadFile={uploadFile}
            setUploadFile={setUploadFile}
            inferenceForm={inferenceForm}
            setInferenceForm={setInferenceForm}
            availableModels={dashboard.available_models}
            busyAction={busyAction}
            onAnalyze={runAnalysis}
            trainingRunning={trainingStatus.training}
          />
        ) : null}

        {activeView === "future" ? (
          <FutureLabView
            projectBrief={dashboard.project_brief}
            recommendation={recommendation}
            benchmark={benchmark}
            modelCatalog={dashboard.model_catalog}
          />
        ) : null}
      </main>
    </div>
  );
}
