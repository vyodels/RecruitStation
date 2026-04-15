import React from "react";
import type { CSSProperties } from "react";
import { useI18n } from "../lib/i18n";
import { theme } from "../lib/theme";
import type { WorkspaceTab } from "../lib/types";
import { StatusBadge } from "./StatusBadge";

interface SidebarProps {
  active: WorkspaceTab;
  onChange(tab: WorkspaceTab): void;
  counts: Partial<Record<WorkspaceTab, number>>;
}

export function Sidebar({ active, onChange, counts }: SidebarProps): JSX.Element {
  const { copy } = useI18n();
  const tabs: Array<{ key: WorkspaceTab; label: string; detail: string }> = [
    { key: "dashboard", label: copy("Overview", "概览"), detail: copy("Candidate progress, approvals, and live signals", "候选人进度、审批和实时信号") },
    { key: "agent-inbox", label: copy("Agent IM", "Agent IM"), detail: copy("Run-time confirmations, blocked flow, and operator chat", "运行时确认、流程阻塞和操作员会话") },
    { key: "recruit-agent", label: copy("Recruit Agent", "招聘 Agent"), detail: copy("Role, prompt, blueprint, memory, and skill contracts", "角色、提示词、执行蓝图、memory 和 skill 契约") },
    { key: "workbench", label: copy("Workbench", "工作台"), detail: copy("Candidate progress and recent agent execution results", "候选人进度与最近的 agent 执行结果") },
    { key: "communications", label: copy("Communications", "沟通中心"), detail: copy("Candidate-scoped threads and runtime confirmations", "候选人隔离线程与运行时确认") },
    { key: "evolution", label: copy("Evolution", "自学习/演进"), detail: copy("Skill degradation, compaction, and evolution approvals", "skill 退化、compact 和演进审批") },
    { key: "settings", label: copy("Settings", "设置"), detail: copy("Provider and sync", "Provider 与同步") },
  ];
  return (
    <aside
      style={{
        width: "248px",
        padding: "16px",
        background: "rgba(8,12,26,0.74)",
        borderRight: `1px solid ${theme.colors.border}`,
        backdropFilter: "blur(12px)",
      }}
    >
      <div style={{ marginBottom: "16px" }}>
        <div style={{ color: theme.colors.accent, textTransform: "uppercase", letterSpacing: "0.2em", fontSize: "11px" }}>
          {copy("Recruit Agent", "Recruit Agent")}
        </div>
        <h1 style={{ margin: "8px 0 6px", fontSize: "24px", lineHeight: 1.08 }}>{copy("Recruit Agent Console", "招聘 Agent 控制台")}</h1>
        <p style={{ margin: 0, color: theme.colors.muted, fontSize: "13px", lineHeight: 1.5 }}>
          {copy(
            "Local-first recruit-agent workspace focused on candidate progress, operator-visible configuration, isolated memory, communications, and skill evolution.",
            "本地优先的 recruit-agent 工作区，聚焦候选人进度、可外露的 agent 配置、隔离 memory、沟通管理和 skill 演进。",
          )}
        </p>
      </div>
      <div style={{ display: "grid", gap: "8px" }}>
        {tabs.map((tab) => {
          const selected = tab.key === active;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => onChange(tab.key)}
              style={{
                cursor: "pointer",
                textAlign: "left",
                padding: "12px 13px",
                borderRadius: theme.radius.lg,
                border: `1px solid ${selected ? "rgba(122,167,255,0.36)" : theme.colors.border}`,
                background: selected ? "rgba(122,167,255,0.12)" : "rgba(255,255,255,0.02)",
                color: theme.colors.text,
                display: "grid",
                gap: "4px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>{tab.label}</span>
                {counts[tab.key] ? <StatusBadge tone={selected ? "positive" : "neutral"}>{counts[tab.key]}</StatusBadge> : null}
              </div>
              <span style={{ color: theme.colors.muted, fontSize: "12px" }}>{tab.detail}</span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
