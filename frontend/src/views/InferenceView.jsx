import React from "react";
import BarChartCard from "../shared/BarChartCard.jsx";

export default function InferenceView({
  recommendation,
  analysis,
  uploadFile,
  setUploadFile,
  inferenceForm,
  setInferenceForm,
  availableModels,
  busyAction,
  onAnalyze,
  trainingRunning,
}) {
  const technicalStages = analysis?.steps || [];
  const objectResults = analysis?.roi_results || [];
  const modelComparison = analysis?.model_comparison || [];
  const modelOptions = (availableModels || []).map((item) => ({
    value: item.artifact_path,
    label: `${item.display_name} [${item.model_family}]`,
  }));
  const accuracyChartItems = modelComparison.map((item) => ({
    label: item.display_name,
    value: Number(item.accuracy || 0) * 100,
    family: item.model_family,
    artifact_path: item.artifact_path,
  }));
  const runtimeChartItems = (analysis?.model_runtime_breakdown || []).map((item) => ({
    label: item.label,
    value: Number(item.value_ms || 0),
    family: item.family,
    artifact_path: item.label,
  }));
  const pipelineRuntimeItems = (analysis?.runtime_benchmarks || []).map((item) => ({
    label: item.label,
    value: Number(item.value_ms || 0),
    family: "neutral",
    artifact_path: item.label,
  }));
  const modelTableRows = modelComparison.map((item) => {
    const predictions = objectResults
      .map((result, index) => {
        const matchedPrediction = (result.model_predictions || []).find(
          (prediction) => prediction.artifact_path === item.artifact_path,
        );
        return matchedPrediction ? `${index + 1}. ${matchedPrediction.prediction}` : null;
      })
      .filter(Boolean)
      .join(" | ");
    return {
      ...item,
      predictions: predictions || "N/A",
    };
  });

  return (
    <div className="page-grid">
      <section className="panel-card inference-control-card">
        <div className="panel-title-row">
          <div>
            <p className="eyebrow">Upload Inference</p>
            <h3>Run one model or compare every saved model on the same image</h3>
          </div>
          <span className="chip">{recommendation.ready ? "inference ready" : "locked"}</span>
        </div>
        <p>
          {recommendation.mode === "classifier_only"
            ? "Upload a cropped single-object image. The system will classify the object, extract text, and compare the saved ROI models."
            : "Upload a full image. The pipeline will detect objects, classify them, draw the final output, and compare selected models on the same detected regions."}
        </p>

        <div className="control-grid">
          <label className="field">
            <span>Inference Mode</span>
            <select
              value={inferenceForm.mode}
              onChange={(event) => setInferenceForm((current) => ({ ...current, mode: event.target.value }))}
              disabled={trainingRunning || !recommendation.ready}
            >
              <option value="recommended">recommended benchmark winner</option>
              <option value="selected">selected saved model</option>
              <option value="all">run all saved models</option>
            </select>
          </label>
          <label className="field">
            <span>Classifier Artifact</span>
            <select
              value={inferenceForm.classifier_artifact}
              onChange={(event) => setInferenceForm((current) => ({ ...current, classifier_artifact: event.target.value }))}
              disabled={trainingRunning || !recommendation.ready || inferenceForm.mode === "recommended"}
            >
              {modelOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="upload-zone">
          <span>{uploadFile ? uploadFile.name : "Choose an image file"}</span>
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.bmp,.webp"
            onChange={(event) => setUploadFile(event.target.files?.[0] || null)}
            disabled={trainingRunning || !recommendation.ready}
          />
        </label>

        <div className="button-stack">
          <button
            className="primary-btn"
            type="button"
            onClick={onAnalyze}
            disabled={busyAction === "analysis" || trainingRunning || !recommendation.ready}
          >
            {busyAction === "analysis" ? "Analyzing..." : "Analyze Image"}
          </button>
          {!recommendation.ready ? <p className="hint-text">Train or add artifacts to unlock inference.</p> : null}
        </div>
      </section>

      {analysis ? (
        <>
          <section className="inference-result-layout">
            <article className="panel-card image-focus-card">
              <div className="panel-title-row">
                <div>
                  <p className="eyebrow">Final Output</p>
                  <h3>Rendered prediction image</h3>
                </div>
                <span className="chip">{`${analysis.num_detections} object(s)`}</span>
              </div>
              <img
                className="result-hero-image"
                src={analysis.final_output_preview || analysis.text_overlay_preview || analysis.annotated_preview}
                alt="Final full-image prediction output"
              />
            </article>

            <div className="result-side-stack">
              <div className="panel-card">
                <p className="eyebrow">Result Summary</p>
                <h3>{analysis.pipeline_used?.classifier_name || recommendation.classifier_name}</h3>
                <div className="detail-list">
                  <div>
                    <span>Comparison Mode</span>
                    <strong>{analysis.comparison_mode}</strong>
                  </div>
                  <div>
                    <span>OCR Backend</span>
                    <strong>{analysis.pipeline_used?.ocr_backend || recommendation.ocr_backend}</strong>
                  </div>
                  <div>
                    <span>Evaluated Models</span>
                    <strong>{analysis.pipeline_used?.evaluated_models?.length || modelComparison.length}</strong>
                  </div>
                  <div>
                    <span>Saved JSON</span>
                    <strong>{analysis.saved_json ? "available" : "not saved"}</strong>
                  </div>
                </div>
              </div>

              <div className="panel-card">
                <p className="eyebrow">Technical Flow</p>
                <h3>Pipeline stages</h3>
                <div className="timeline-list compact">
                  {technicalStages.map((step, index) => (
                    <div className="timeline-item" key={step.name}>
                      <span className="timeline-index">{String(index + 1).padStart(2, "0")}</span>
                      <div>
                        <strong>{step.name}</strong>
                        <p>{step.summary}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="card-grid three">
            <BarChartCard
              title="Benchmark Accuracy"
              subtitle="Saved model quality"
              items={accuracyChartItems}
              suffix="%"
              limit={10}
              emptyText="Accuracy chart appears after analysis."
            />
            <BarChartCard
              title="Live Model Runtime"
              subtitle="Per-image classification runtime"
              items={runtimeChartItems}
              suffix=" ms"
              limit={10}
              emptyText="Model runtime comparison appears after analysis."
            />
            <BarChartCard
              title="Pipeline Stage Runtime"
              subtitle="End-to-end timing"
              items={pipelineRuntimeItems}
              suffix=" ms"
              limit={10}
              emptyText="Stage runtime appears after analysis."
            />
          </section>

          <section className="panel-card">
            <p className="eyebrow">Detected Objects</p>
            <h3>Predicted labels and extracted text</h3>
            <div className="table-wrap">
              <table className="result-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Predicted Label</th>
                    <th>Extracted Text</th>
                    <th>OCR Backend</th>
                    <th>Text Boxes</th>
                  </tr>
                </thead>
                <tbody>
                  {objectResults.map((item, index) => (
                    <tr key={`${item.object_label}-${index}`}>
                      <td>{index + 1}</td>
                      <td>{item.object_label}</td>
                      <td>{item.extracted_text}</td>
                      <td>{item.ocr_backend}</td>
                      <td>{item.text_box_count ?? item.text_boxes?.length ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel-card">
            <p className="eyebrow">All Models Comparison</p>
            <h3>{`${modelTableRows.length} model(s) evaluated on this image`}</h3>
            <div className="table-wrap">
              <table className="result-table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Family</th>
                    <th>Prediction(s)</th>
                    <th>Accuracy</th>
                    <th>Macro F1</th>
                    <th>Runtime</th>
                  </tr>
                </thead>
                <tbody>
                  {modelTableRows.map((item) => (
                    <tr key={item.artifact_path}>
                      <td>
                        <strong>{item.display_name}</strong>
                      </td>
                      <td>
                        <span className={`family-chip ${item.model_family}`}>{item.model_family}</span>
                      </td>
                      <td>{item.predictions}</td>
                      <td>{`${(Number(item.accuracy || 0) * 100).toFixed(2)}%`}</td>
                      <td>{`${(Number(item.macro_f1 || 0) * 100).toFixed(2)}%`}</td>
                      <td>{`${Number(item.avg_runtime_ms || 0).toFixed(2)} ms`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
