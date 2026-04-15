import React from "react";

interface StatusBadgeProps {
  tone: "positive" | "neutral" | "warning" | "critical";
  children: React.ReactNode;
}

export function StatusBadge({ tone, children }: StatusBadgeProps): JSX.Element {
  return (
    <span className="status-badge" data-tone={tone}>
      {children}
    </span>
  );
}
