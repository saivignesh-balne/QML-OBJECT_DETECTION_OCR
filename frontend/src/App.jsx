import React, { useEffect, useRef, useState } from "react";
import { fetchJson } from "./api.js";
import OverviewView from "./views/OverviewView.jsx";
import WorkflowView from "./views/WorkflowView.jsx";
import TrainingView from "./views/TrainingView.jsx";
import BenchmarksView from "./views/BenchmarksView.jsx";
import InferenceView from "./views/InferenceView.jsx";
import FutureLabView from "./views/FutureLabView.jsx";

const NAV_ITEMS = [
  { id: "overview", label: "Overview", short: "OV" },
  { id: "workflow", label: "Workflow", short: "WF" },
  { id: "training", label: "Training", short: "TR" },
  { id: "benchmarks", label: "Benchmarks", short: "BM" },
  { id: "inference", label: "Inference Lab", short: "IN" },
  { id: "future", label: "Project Brief", short: "PB" },
];

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
          if (!current) {
            return current;
          }
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
          <p className="eyebrow">Quantum Vision Studio</p>
          <h1>Preparing workspace</h1>
        </div>
      </div>
    );
  }

  const trainingStatus = dashboard.training_status || { training: false, status_messages: [] };
  const recommendation = dashboard.recommendation;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">QV</div>
          <div>
            <p className="eyebrow">React Control Room</p>
            <h1>Quantum Vision Studio</h1>
          </div>
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
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-card">
          <span className="sidebar-label">Best Available Stack</span>
          <strong>{`${recommendation.detector_backend || "pending"} + ${recommendation.classifier_name} + ${recommendation.ocr_backend}`}</strong>
          <p>
            {recommendation.mode === "classifier_only"
              ? "ROI upload mode is ready. Cropped single-object uploads are supported now."
              : recommendation.ready
                ? "Ready for full upload inference."
                : "Train or add artifacts to unlock inference."}
          </p>
          <p>{`Classifier family: ${recommendation.classifier_family || "unknown"}`}</p>
        </div>

        <div className="sidebar-card muted">
          <span className="sidebar-label">Supported Classes</span>
          <div className="stacked-chips">
            {dashboard.supported_classes.map((item) => (
              <span key={item} className="chip">
                {item}
              </span>
            ))}
            <span className="chip ghost">others -&gt; unidentified</span>
          </div>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Professional QML + OCR Workspace</p>
            <h2>{NAV_ITEMS.find((item) => item.id === activeView)?.label}</h2>
          </div>
          <div className="topbar-status">
            <div className={`status-pill ${trainingStatus.training ? "warn" : "good"}`}>
              {trainingStatus.training ? "Training Running" : "System Ready"}
            </div>
            <button className="ghost-btn" type="button" onClick={() => loadDashboard()}>
              Refresh
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
            benchmark={dashboard.benchmark}
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
          <BenchmarksView benchmark={dashboard.benchmark} recommendation={recommendation} projectBrief={dashboard.project_brief} />
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
            benchmark={dashboard.benchmark}
            modelCatalog={dashboard.model_catalog}
          />
        ) : null}
      </main>
    </div>
  );
}
