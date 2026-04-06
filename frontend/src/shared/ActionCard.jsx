import React from "react";

export default function ActionCard({ title, subtitle, text, onClick }) {
  return (
    <button className="action-card" type="button" onClick={onClick}>
      <div className="action-card-head">
        <span className="eyebrow">{title}</span>
        <span className="action-card-arrow">Open</span>
      </div>
      <strong>{subtitle}</strong>
      <p>{text}</p>
    </button>
  );
}
