import React from "react";

export default function BenchmarkCard({ title, rows, emptyText, fullWidth = false }) {
  function buildMeta(row) {
    const meta = [];
    if (row.model_family) meta.push(row.model_family);
    if (row.model) meta.push(row.model);
    if (row.encoding && row.encoding !== "classical_projection") meta.push(row.encoding);
    if (row.n_qubits) meta.push(`${row.n_qubits}q`);
    if (row.kernel_name) meta.push(row.kernel_name);
    if (row.feature_map_name) meta.push(row.feature_map_name);
    if (row.ansatz_name && row.ansatz_name !== "none") meta.push(row.ansatz_name);
    if (row.artifact_reused) meta.push("reused");
    return meta;
  }

  return (
    <div className={`panel-card ${fullWidth ? "full-width" : ""}`}>
      <p className="eyebrow">Benchmark Data</p>
      <h3>{title}</h3>
      {rows && rows.length ? (
        <div className="benchmark-list">
          {rows.map((row, index) => (
            <div className="benchmark-row" key={`${row.name || row.pipeline || row.model}-${index}`}>
              <div>
                <strong>{row.pipeline || row.name || row.model}</strong>
                <p>{row.summary || row.notes || row.encoding || row.metric || "benchmark entry"}</p>
                {buildMeta(row).length ? (
                  <div className="meta-chip-row">
                    {buildMeta(row).map((item) => (
                      <span className="chip benchmark-chip" key={`${row.name || row.pipeline}-${item}`}>
                        {item}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
              <div className="benchmark-score">
                <strong>
                  {typeof row.score === "string"
                    ? row.score
                    : `${(((row.accuracy || row.Accuracy || 0) * 100)).toFixed(2)}%`}
                </strong>
                {row.macro_f1 ? <span>{`F1 ${(row.macro_f1 * 100).toFixed(2)}%`}</span> : null}
                {row.train_time_seconds ? <span>{`${row.train_time_seconds.toFixed(1)} s`}</span> : null}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="empty-text">{emptyText}</p>
      )}
    </div>
  );
}
