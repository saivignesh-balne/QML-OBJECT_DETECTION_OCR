import React from "react";

function familyClass(family) {
  return family === "quantum" ? "quantum" : family === "classical" ? "classical" : "neutral";
}

export default function BarChartCard({
  title,
  subtitle,
  items,
  suffix = "",
  emptyText,
  limit = 8,
}) {
  const safeItems = Array.isArray(items) ? items.slice(0, limit) : [];
  const maxValue = Math.max(...safeItems.map((item) => Number(item.value || 0)), 1);
  const lead = safeItems[0];

  return (
    <div className="panel-card chart-card">
      <div className="chart-header">
        <div>
          <p className="eyebrow">{subtitle || "Benchmark Chart"}</p>
          <h3>{title}</h3>
        </div>
        <span className="chart-count">{`${safeItems.length} item(s)`}</span>
      </div>

      {lead ? (
        <div className={`chart-feature ${familyClass(lead.family)}`}>
          <div>
            <span className="chart-feature-label">Top Performer</span>
            <strong>{lead.label}</strong>
          </div>
          <span className="chart-feature-value">{`${Number(lead.value || 0).toFixed(2)}${suffix}`}</span>
        </div>
      ) : null}

      {safeItems.length ? (
        <div className="chart-list">
          {safeItems.map((item, index) => {
            const value = Number(item.value || 0);
            return (
              <div className="chart-row" key={`${item.label}-${item.artifact_path || item.family || ""}`}>
                <div className="chart-meta">
                  <div className="chart-title-block">
                    <span className={`chart-rank ${familyClass(item.family)}`}>{String(index + 1).padStart(2, "0")}</span>
                    <strong>{item.label}</strong>
                  </div>
                  <span>{`${value.toFixed(2)}${suffix}`}</span>
                </div>
                <div className="chart-track">
                  <div
                    className={`chart-fill ${familyClass(item.family)}`}
                    style={{ width: `${Math.max(6, (value / maxValue) * 100)}%` }}
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
