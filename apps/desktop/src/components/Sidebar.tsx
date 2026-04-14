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
    { key: "dashboard", label: copy("Overview", "概览"), detail: copy("Mission control", "总览面板") },
    { key: "runtime", label: copy("Runtime", "运行时"), detail: copy("Task compiler and plans", "任务编译与计划") },
    { key: "trials", label: copy("Trials", "试跑"), detail: copy("Supervised executions", "受监督执行") },
    { key: "templates", label: copy("Templates", "模板"), detail: copy("Reusable workflows", "可复用工作流") },
    { key: "patches", label: copy("Patches", "补丁"), detail: copy("Divergence proposals", "偏差修正建议") },
    { key: "domains", label: copy("Domains", "领域包"), detail: copy("Pack inventory", "能力包清单") },
    { key: "recruiting", label: copy("Recruiting", "招聘"), detail: copy("Domain pack view", "领域包视图") },
    { key: "skills", label: copy("Skills", "Skills"), detail: copy("Approval and health", "审批与 skill health") },
    { key: "approvals", label: copy("Approvals", "审批"), detail: copy("Human gates", "人工关卡") },
    { key: "monitor", label: copy("Monitor", "监控"), detail: copy("Agent runtime", "Agent 运行态") },
    { key: "settings", label: copy("Settings", "设置"), detail: copy("Provider and sync", "Provider 与同步") },
  ];
  return (
    <aside
      style={{
        width: "280px",
        padding: "18px",
        background: "rgba(8,12,26,0.82)",
        borderRight: `1px solid ${theme.colors.border}`,
        backdropFilter: "blur(16px)",
      }}
    >
      <div style={{ marginBottom: "18px" }}>
        <div style={{ color: theme.colors.accent, textTransform: "uppercase", letterSpacing: "0.2em", fontSize: "11px" }}>
          {copy("General Automation Runtime", "通用自动化运行时")}
        </div>
        <h1 style={{ margin: "10px 0 6px", fontSize: "28px", lineHeight: 1.05 }}>{copy("Desktop Control Plane", "桌面控制平面")}</h1>
        <p style={{ margin: 0, color: theme.colors.muted, fontSize: "14px", lineHeight: 1.5 }}>
          {copy(
            "Local-first natural-language automation with supervised trial runs, approvals, runtime patches, and reusable domain packs.",
            "本地优先的自然语言自动化平台，支持受监督试跑、审批、运行时补丁和可复用领域包。",
          )}
        </p>
      </div>
      <div style={{ display: "grid", gap: "10px" }}>
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
                padding: "14px",
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
