import React from "react";

function familyClass(family) {
  return family === "quantum" ? "quantum" : family === "classical" ? "classical" : "neutral";
}

export default function BarChartCard({ title, subtitle, items, suffix = "", emptyText }) {
  const safeItems = Array.isArray(items) ? items.slice(0, 8) : [];
  const maxValue = Math.max(...safeItems.map((item) => Number(item.value || 0)), 1);

  return (
    <div className="panel-card">
      <p className="eyebrow">{subtitle || "Benchmark Chart"}</p>
      <h3>{title}</h3>
      {safeItems.length ? (
        <div className="chart-list">
          {safeItems.map((item) => {
            const value = Number(item.value || 0);
            return (
              <div className="chart-row" key={`${item.label}-${item.artifact_path || item.family || ""}`}>
                <div className="chart-meta">
                  <strong>{item.label}</strong>
                  <span>{`${value.toFixed(2)}${suffix}`}</span>
                </div>
                <div className="chart-track">
                  <div
                    className={`chart-fill ${familyClass(item.family)}`}
                    style={{ width: `${Math.max(8, (value / maxValue) * 100)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="empty-text">{emptyText || "No chart data available yet."}</p>
      )}
    </div>
  );
}
