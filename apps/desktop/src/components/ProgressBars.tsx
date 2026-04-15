import React from "react";
import type { PipelineStage } from "../lib/types";

interface ProgressBarsProps {
  stages: PipelineStage[];
}

export function ProgressBars({ stages }: ProgressBarsProps): JSX.Element {
  return (
    <div className="progress-bars">
      {stages.map((stage) => {
        const target = stage.target ?? Math.max(stage.value, 1);
        const width = `${Math.min(100, Math.round((stage.value / target) * 100))}%`;

        return (
          <div key={stage.label} className="progress-bars__row">
            <div className="progress-bars__head">
              <span className="progress-bars__label">{stage.label}</span>
              <span className="progress-bars__value">
                {stage.value}/{target}
              </span>
            </div>
            <div className="progress-bars__track">
              <div className="progress-bars__fill" style={{ width }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
