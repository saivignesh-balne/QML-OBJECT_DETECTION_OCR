import React from "react";

export default function ActionCard({ title, subtitle, text, onClick }) {
  return (
    <button className="action-card" type="button" onClick={onClick}>
      <span className="eyebrow">{title}</span>
      <strong>{subtitle}</strong>
      <p>{text}</p>
    </button>
  );
}
