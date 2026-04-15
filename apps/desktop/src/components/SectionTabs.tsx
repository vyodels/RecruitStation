import React from "react";
import { StatusBadge } from "./StatusBadge";

export interface SectionTabItem {
  key: string;
  label: string;
  detail?: string;
  count?: number;
}

interface SectionTabsProps {
  items: SectionTabItem[];
  active: string;
  onChange(key: string): void;
  variant?: "card" | "topbar";
}

export function SectionTabs({ items, active, onChange, variant = "card" }: SectionTabsProps): JSX.Element {
  return (
    <div className="section-tabs" data-variant={variant}>
      {items.map((item) => {
        const selected = item.key === active;
        const showDetail = variant !== "topbar" && item.detail;

        return (
          <button
            key={item.key}
            type="button"
            className="section-tabs__item"
            data-active={selected}
            onClick={() => onChange(item.key)}
          >
            <span className="section-tabs__item-content">
              <span className="section-tabs__label-row">
                <span className="section-tabs__label">{item.label}</span>
                {item.count != null ? <StatusBadge tone={selected ? "positive" : "neutral"}>{item.count}</StatusBadge> : null}
              </span>
              {showDetail ? <span className="section-tabs__detail">{item.detail}</span> : null}
            </span>
          </button>
        );
      })}
    </div>
  );
}
