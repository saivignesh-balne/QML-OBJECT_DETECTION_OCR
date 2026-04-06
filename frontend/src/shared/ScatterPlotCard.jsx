import React from "react";

function familyColor(family) {
  if (family === "quantum") return "#0f9b76";
  if (family === "classical") return "#d38b24";
  return "#6b7d84";
}

export default function ScatterPlotCard({
  title,
  subtitle,
  items,
  xLabel = "Training Time (s)",
  yLabel = "Accuracy (%)",
  emptyText,
}) {
  const safeItems = Array.isArray(items)
    ? items.filter((item) => Number.isFinite(Number(item.x)) && Number.isFinite(Number(item.y)))
    : [];

  const width = 520;
  const height = 300;
  const padding = { top: 22, right: 18, bottom: 46, left: 54 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const maxX = Math.max(...safeItems.map((item) => Number(item.x || 0)), 1);
  const maxY = Math.max(...safeItems.map((item) => Number(item.y || 0)), 1);

  function scaleX(value) {
    return padding.left + (Number(value || 0) / maxX) * innerWidth;
  }

  function scaleY(value) {
    return height - padding.bottom - (Number(value || 0) / maxY) * innerHeight;
  }

  return (
    <div className="panel-card chart-card">
      <div className="chart-header">
        <div>
          <p className="eyebrow">{subtitle || "Benchmark Scatter"}</p>
          <h3>{title}</h3>
        </div>
        <span className="chart-count">{`${safeItems.length} model(s)`}</span>
      </div>

      {safeItems.length ? (
        <>
          <div className="scatter-wrap">
            <svg className="scatter-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
              <line
                x1={padding.left}
                y1={height - padding.bottom}
                x2={width - padding.right}
                y2={height - padding.bottom}
                className="scatter-axis"
              />
              <line
                x1={padding.left}
                y1={padding.top}
                x2={padding.left}
                y2={height - padding.bottom}
                className="scatter-axis"
              />

              {[0.25, 0.5, 0.75, 1].map((ratio) => {
                const y = padding.top + (1 - ratio) * innerHeight;
                return (
                  <g key={`grid-${ratio}`}>
                    <line
                      x1={padding.left}
                      y1={y}
                      x2={width - padding.right}
                      y2={y}
                      className="scatter-grid"
                    />
                    <text x={padding.left - 10} y={y + 4} className="scatter-tick" textAnchor="end">
                      {(maxY * ratio).toFixed(0)}
                    </text>
                  </g>
                );
              })}

              {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
                const x = padding.left + ratio * innerWidth;
                return (
                  <g key={`xtick-${ratio}`}>
                    <line
                      x1={x}
                      y1={padding.top}
                      x2={x}
                      y2={height - padding.bottom}
                      className="scatter-grid vertical"
                    />
                    <text x={x} y={height - padding.bottom + 22} className="scatter-tick" textAnchor="middle">
                      {(maxX * ratio).toFixed(ratio === 0 || maxX >= 100 ? 0 : 1)}
                    </text>
                  </g>
                );
              })}

              {safeItems.map((item) => (
                <g key={`${item.label}-${item.x}-${item.y}`}>
                  <circle
                    cx={scaleX(item.x)}
                    cy={scaleY(item.y)}
                    r="7.5"
                    fill={familyColor(item.family)}
                    fillOpacity="0.88"
                    stroke="#ffffff"
                    strokeWidth="2"
                  >
                    <title>{`${item.label}: ${Number(item.y).toFixed(2)}% accuracy, ${Number(item.x).toFixed(2)} s`}</title>
                  </circle>
                </g>
              ))}

              <text
                x={(padding.left + width - padding.right) / 2}
                y={height - 8}
                className="scatter-label"
                textAnchor="middle"
              >
                {xLabel}
              </text>
              <text
                x="16"
                y={(padding.top + height - padding.bottom) / 2}
                className="scatter-label"
                textAnchor="middle"
                transform={`rotate(-90 16 ${(padding.top + height - padding.bottom) / 2})`}
              >
                {yLabel}
              </text>
            </svg>
          </div>

          <div className="chart-legend">
            <span className="legend-item">
              <span className="legend-dot classical" />
              Classical
            </span>
            <span className="legend-item">
              <span className="legend-dot quantum" />
              Quantum / Hybrid
            </span>
          </div>
        </>
      ) : (
        <p className="empty-text">{emptyText || "No scatter data available yet."}</p>
      )}
    </div>
  );
}
