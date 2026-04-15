import React from "react";
import { SectionTabs, type SectionTabItem } from "./SectionTabs";

interface TopTabPageProps {
  items: SectionTabItem[];
  active: string;
  onChange(key: string): void;
  children: React.ReactNode;
}

export function TopTabPage({ items, active, onChange, children }: TopTabPageProps): JSX.Element {
  return (
    <div className="top-tab-page">
      <div className="top-tab-page__sticky">
        <SectionTabs items={items} active={active} onChange={onChange} variant="topbar" />
      </div>
      <div className="top-tab-page__content">{children}</div>
    </div>
  );
}
