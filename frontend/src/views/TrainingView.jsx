import React from "react";
import FormCard from "../shared/FormCard.jsx";

export default function TrainingView({
  detectorForm,
  setDetectorForm,
  classifierForm,
  setClassifierForm,
  suiteForm,
  setSuiteForm,
  datasetStatus,
  trainingStatus,
  busyAction,
  modelCatalog,
  availableModels,
  detectorWeights,
  onRunDetector,
  onRunClassifier,
  onRunSuite,
  onRunAllModels,
  onBuildBenchmark,
}) {
  const detectorStatus = datasetStatus?.detector || {};
  const classifierStatus = datasetStatus?.classifier || {};
  const detectorReady = Boolean(detectorStatus.ready);
  const classifierReady = Boolean(classifierStatus.ready);
  const modelOptions = (modelCatalog || [])
    .filter((item) => item.model_type !== "pegasos_qsvc")
    .map((item) => ({
      value: item.model_type,
      label: `${item.display_name} [${item.family}]`,
    }));
  const suiteProgress =
    trainingStatus.progress_total > 0
      ? `${trainingStatus.progress_current || 0}/${trainingStatus.progress_total}`
      : "not started";
  const activeTrainingLabel = trainingStatus.active_item || "waiting";
  const savedDetectorCount = detectorWeights?.length || 0;

  return (
    <div className="page-grid">
      <section className="card-grid two">
        <div className={`panel-card dataset-card ${detectorReady ? "ready" : "warn"}`}>
          <p className="eyebrow">Detector Dataset Check</p>
          <h3>{detectorReady ? "YOLO dataset ready" : "Detector dataset missing"}</h3>
          <p>{detectorStatus.message}</p>
          <div className="dataset-stats">
            <div>
              <span>Train Images</span>
              <strong>{detectorStatus.train_images || 0}</strong>
            </div>
            <div>
              <span>Val Images</span>
              <strong>{detectorStatus.val_images || 0}</strong>
            </div>
            <div>
              <span>Train Labels</span>
              <strong>{detectorStatus.train_labels || 0}</strong>
            </div>
            <div>
              <span>Val Labels</span>
              <strong>{detectorStatus.val_labels || 0}</strong>
            </div>
          </div>
        </div>

        <div className={`panel-card dataset-card ${classifierReady ? "ready" : "warn"}`}>
          <p className="eyebrow">ROI Classifier Dataset Check</p>
          <h3>{classifierReady ? "ROI dataset ready" : "ROI dataset incomplete"}</h3>
          <p>{classifierStatus.message}</p>
          <div className="dataset-stats">
            <div>
              <span>chip_packet</span>
              <strong>{classifierStatus.class_counts?.chip_packet || 0}</strong>
            </div>
            <div>
              <span>medicine_box</span>
              <strong>{classifierStatus.class_counts?.medicine_box || 0}</strong>
            </div>
            <div>
              <span>bottle</span>
              <strong>{classifierStatus.class_counts?.bottle || 0}</strong>
            </div>
            <div>
              <span>Total ROI Images</span>
              <strong>{classifierStatus.total_images || 0}</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="card-grid two">
        <FormCard
          title="Detector Trainer"
          subtitle="Optional: full-scene YOLO detection dataset required"
          fields={[
            { key: "dataset_yaml", label: "Dataset YAML" },
            { key: "model", label: "Base Model" },
            { key: "epochs", label: "Epochs" },
            { key: "imgsz", label: "Image Size" },
            { key: "batch", label: "Batch Size" },
            { key: "project", label: "Project Folder" },
            { key: "name", label: "Run Name" },
            { key: "device", label: "Device" },
            { key: "summary_path", label: "Summary JSON" },
            { key: "reuse_existing", label: "Reuse Existing", type: "select", options: ["true", "false"] },
          ]}
          data={detectorForm}
          onChange={setDetectorForm}
          onSubmit={onRunDetector}
          submitLabel={busyAction === "detector" ? "Starting..." : detectorReady ? "Start Detector Training" : "Detector Dataset Required"}
          disabled={trainingStatus.training}
          submitDisabled={trainingStatus.training || !detectorReady}
          message={detectorStatus.message}
          messageTone={detectorReady ? "success" : "warning"}
        />

        <FormCard
          title="Single Model Trainer"
          subtitle="Train a specific classical or quantum-ready ROI classifier"
          fields={[
            { key: "dataset_dir", label: "ROI Dataset Directory" },
            { key: "artifact_path", label: "Artifact Path" },
            { key: "model_type", label: "Model Type", type: "select", options: modelOptions },
            { key: "encoding", label: "Encoding", type: "select", options: ["angle", "amplitude"] },
            { key: "n_qubits", label: "Qubits" },
            { key: "test_size", label: "Test Split" },
            { key: "device", label: "Device" },
            { key: "summary_path", label: "Summary JSON" },
            { key: "reuse_existing", label: "Reuse Existing", type: "select", options: ["true", "false"] },
          ]}
          data={classifierForm}
          onChange={setClassifierForm}
          onSubmit={onRunClassifier}
          submitLabel={busyAction === "classifier" ? "Starting..." : classifierReady ? "Start Classifier Training" : "ROI Dataset Required"}
          disabled={trainingStatus.training}
          submitDisabled={trainingStatus.training || !classifierReady}
          message="Choose a classical baseline, a quantum-kernel model, or a trainable VQC. Encoding mainly affects the quantum families."
          messageTone="success"
        />
      </section>

      <section className="card-grid two">
        <FormCard
          title="Comparison Suite Runner"
          subtitle="Run saved, reusable benchmark suites"
          fields={[
            { key: "dataset_dir", label: "ROI Dataset Directory" },
            { key: "artifacts_dir", label: "Artifacts Directory" },
            {
              key: "profile",
              label: "Suite Profile",
              type: "select",
              options: [
                { value: "core", label: "core - strong baselines + one quantum reference" },
                { value: "quantum", label: "quantum - kernel and VQC variants only" },
                { value: "presentation", label: "presentation - clean manager-ready mix" },
                { value: "all_models", label: "all models - train every supported ROI model" },
                { value: "extended", label: "extended - broader classical + quantum grid" },
              ],
            },
            { key: "test_size", label: "Test Split" },
            { key: "device", label: "Device" },
            { key: "reuse_existing", label: "Reuse Existing", type: "select", options: ["true", "false"] },
          ]}
          data={suiteForm}
          onChange={setSuiteForm}
          onSubmit={onRunSuite}
          submitLabel={busyAction === "suite" ? "Starting..." : classifierReady ? "Run Comparison Suite" : "ROI Dataset Required"}
          disabled={trainingStatus.training}
          submitDisabled={trainingStatus.training || !classifierReady}
          message="Use suite runs to save a full benchmark pack. Reuse mode skips compatible artifacts so you do not retrain the same models repeatedly."
          messageTone="success"
        />

        <div className="panel-card">
          <p className="eyebrow">Quick Actions</p>
          <h3>Detector can stay saved while ROI models expand</h3>
          <p>
            {savedDetectorCount > 0
              ? `Saved detector weights found: ${savedDetectorCount}. You only need to train new ROI models unless you want to retrain detection.`
              : "No saved detector weights found yet. You can still train ROI models now and add or retrain detection later."}
          </p>
          <div className="button-stack">
            <button
              className="primary-btn"
              type="button"
              onClick={onRunAllModels}
              disabled={trainingStatus.training || !classifierReady}
            >
              Train All ROI Models
            </button>
            <button
              className="secondary-btn"
              type="button"
              onClick={onBuildBenchmark}
              disabled={trainingStatus.training || busyAction === "benchmark"}
            >
              {busyAction === "benchmark" ? "Building..." : "Generate Benchmark Report"}
            </button>
          </div>
        </div>
      </section>

      <section className="card-grid one">
        <div className="panel-card log-card">
          <p className="eyebrow">Live Job Status</p>
          <h3>{trainingStatus.title || "Idle"}</h3>
          <div className="status-line">
            <span>{trainingStatus.job_type || "no active job"}</span>
            <strong>
              {trainingStatus.training
                ? "Running"
                : trainingStatus.return_code === 0
                  ? "Completed"
                : trainingStatus.return_code === 1
                    ? "Failed"
                    : "Idle"}
            </strong>
          </div>
          <div className="training-progress-grid">
            <div className="progress-pill">
              <span>Active Item</span>
              <strong>{activeTrainingLabel}</strong>
            </div>
            <div className="progress-pill">
              <span>Suite Progress</span>
              <strong>{suiteProgress}</strong>
            </div>
            <div className="progress-pill">
              <span>Status</span>
              <strong>{trainingStatus.progress_status || "idle"}</strong>
            </div>
          </div>
          <div className="log-stream">
            {(trainingStatus.status_messages || []).slice().reverse().map((line, index) => (
              <div className="log-line" key={`${line}-${index}`}>
                {line}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="card-grid two">
        <div className="panel-card">
          <p className="eyebrow">Supported Models</p>
          <h3>Comparison menu</h3>
          <div className="catalog-grid">
            {(modelCatalog || []).map((item) => (
              <article className="catalog-card" key={item.model_type}>
                <div className="step-row">
                  <strong>{item.display_name}</strong>
                  <span className={`family-chip ${item.family}`}>{item.family}</span>
                </div>
                <p>{item.summary}</p>
                <div className="meta-chip-row">
                  <span className="chip">{item.kernel_name}</span>
                  <span className="chip">{item.feature_map_name}</span>
                  <span className="chip">{item.ansatz_name}</span>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="panel-card">
          <p className="eyebrow">Saved Models</p>
          <h3>{`${(availableModels || []).length} trained artifacts available`}</h3>
          {(availableModels || []).length ? (
            <div className="catalog-grid compact">
              {availableModels.map((item) => (
                <article className="catalog-card compact" key={item.artifact_path}>
                  <div className="step-row">
                    <strong>{item.display_name}</strong>
                    <span className={`family-chip ${item.model_family}`}>{item.model_family}</span>
                  </div>
                  <p>{`${(item.accuracy * 100).toFixed(2)}% accuracy | ${(item.macro_f1 * 100).toFixed(2)}% macro F1`}</p>
                  <p className="hint-text">{item.kernel_name}</p>
                </article>
              ))}
            </div>
          ) : (
            <p className="empty-text">No trained classifier artifacts yet. Train one model or run a suite to populate this area.</p>
          )}
        </div>
      </section>
    </div>
  );
}
