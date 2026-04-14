import React from "react";
import { Panel, StatusBadge } from "../../components";
import { formatCompactDate } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { translateUiToken } from "../../lib/uiText";
import type { SkillRecord } from "../../lib/types";

interface SkillsViewProps {
  skills: SkillRecord[];
}

export function SkillsView({ skills }: SkillsViewProps): JSX.Element {
  const { copy } = useI18n();

  return (
    <div style={{ display: "grid", gap: "18px", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
      {skills.map((skill) => (
        <Panel
          key={skill.id}
          title={skill.name}
          eyebrow={copy(`Bound to ${skill.boundNode}`, `绑定到 ${skill.boundNode}`)}
          description={skill.summary}
          actions={<StatusBadge tone={skill.health === "healthy" ? "positive" : skill.health === "warning" ? "warning" : "critical"}>{translateUiToken(skill.status, copy)}</StatusBadge>}
        >
          <div style={{ display: "grid", gap: "10px" }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              <StatusBadge tone={skill.health === "healthy" ? "positive" : skill.health === "warning" ? "warning" : "critical"}>{translateUiToken(skill.health, copy)}</StatusBadge>
              <StatusBadge tone="neutral">{skill.platform}</StatusBadge>
              <StatusBadge tone="neutral">v{skill.version}</StatusBadge>
            </div>
            <div style={{ color: "rgba(233,239,255,0.7)", fontSize: "13px" }}>{copy(`Last checked ${formatCompactDate(skill.lastCheckedAt)}`, `最近检查于 ${formatCompactDate(skill.lastCheckedAt)}`)}</div>
          </div>
        </Panel>
      ))}
    </div>
  );
}
