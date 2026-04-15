import React from "react";
import { formatCompactDate } from "../lib/format";
import { useI18n } from "../lib/i18n";
import { translateUiToken } from "../lib/uiText";
import type { TimelineEvent } from "../lib/types";
import { StatusBadge } from "./StatusBadge";

interface TimelineProps {
  events: TimelineEvent[];
}

export function Timeline({ events }: TimelineProps): JSX.Element {
  const { copy } = useI18n();

  return (
    <div className="timeline">
      {events.map((event) => (
        <article key={event.id} className="timeline__item" data-tone={event.tone}>
          <div className="timeline__header">
            <strong className="timeline__label">{event.label}</strong>
            <StatusBadge tone={event.tone}>{formatCompactDate(event.at)}</StatusBadge>
          </div>
          <div className="timeline__detail">{event.detail}</div>
        </article>
      ))}
    </div>
  );
}
