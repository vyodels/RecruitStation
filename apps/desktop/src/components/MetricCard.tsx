import React from "react";
import { StatusBadge } from "./StatusBadge";

interface MetricCardProps {
  label: string;
  value: string;
  delta: string;
  tone: "positive" | "neutral" | "warning";
  caption: string;
  onClick?: () => void;
}

export function MetricCard({ label, value, delta, tone, caption, onClick }: MetricCardProps): JSX.Element {
  const interactive = Boolean(onClick);

  return (
    <article
      className={`metric-card${interactive ? " metric-card--clickable" : ""}`}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        interactive
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
    >
      <div className="metric-card__header">
        <div className="metric-card__label">{label}</div>
        <StatusBadge tone={tone === "positive" ? "positive" : tone === "warning" ? "warning" : "neutral"}>{delta}</StatusBadge>
      </div>
      <div className="metric-card__value">{value}</div>
      <div className="metric-card__caption">{caption}</div>
    </article>
  );
}
