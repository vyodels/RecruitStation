import React from "react";
import { useI18n } from "../lib/i18n";
import type { WorkspaceTab } from "../lib/types";
import { StatusBadge } from "./StatusBadge";

interface SidebarProps {
  active: WorkspaceTab;
  onChange(tab: WorkspaceTab): void;
  counts: Partial<Record<WorkspaceTab, number>>;
}

const tabs: Array<{ key: WorkspaceTab; labelEn: string; labelZh: string; detailEn: string; detailZh: string }> = [
  { key: "home", labelEn: "Home", labelZh: "首页", detailEn: "Today's recruiting overview", detailZh: "今日招聘总览" },
  { key: "candidates", labelEn: "Candidates", labelZh: "候选人", detailEn: "Pipeline, progress, and next action", detailZh: "管道、进度与下一步" },
  { key: "import-center", labelEn: "Import Center", labelZh: "导入中心", detailEn: "Resume intake and source review", detailZh: "简历导入与来源审查" },
  { key: "jd-workspace", labelEn: "JD Workspace", labelZh: "JD 工作区", detailEn: "Role scope, workflow, and notes", detailZh: "岗位范围、流程与策略笔记" },
  { key: "communications", labelEn: "Cockpit", labelZh: "候选人舱", detailEn: "Per-candidate threads and context", detailZh: "按候选人隔离的线程与上下文" },
  { key: "ai-review", labelEn: "AI Review", labelZh: "AI 审查", detailEn: "Approvals, signals, and follow-ups", detailZh: "审批、信号与待办跟进" },
  { key: "ai-strategy", labelEn: "AI Strategy", labelZh: "AI 策略", detailEn: "Strategy, memory, and hiring rules", detailZh: "策略、记忆与招聘规则" },
  { key: "settings", labelEn: "Settings", labelZh: "设置", detailEn: "Accounts, sync, and tool setup", detailZh: "账号、同步与工具配置" },
];

export function Sidebar({ active, onChange, counts }: SidebarProps): JSX.Element {
  const { copy } = useI18n();

  return (
    <aside className="workspace-sidebar">
      <div className="workspace-sidebar__brand">
        <div className="workspace-sidebar__eyebrow">{copy("Recruiter Workspace", "招聘工作台")}</div>
        <div className="workspace-sidebar__title">{copy("Candidate Operations", "候选人运营")}</div>
        <p className="workspace-sidebar__description">
          {copy(
            "A recruiter workspace for candidate flow, AI review, and coordinated follow-up.",
            "面向招聘团队的工作台，用来处理候选人流转、AI 审查和协同跟进。",
          )}
        </p>
      </div>

      <nav className="workspace-sidebar__nav" aria-label={copy("Workspace sections", "工作区分区")}>
        {tabs.map((tab) => {
          const selected = tab.key === active;
          const count = counts[tab.key] ?? 0;

          return (
            <button
              key={tab.key}
              type="button"
              className="workspace-sidebar__item"
              data-active={selected}
              onClick={() => onChange(tab.key)}
            >
              <div className="workspace-sidebar__item-main">
                <span className="workspace-sidebar__item-label">{copy(tab.labelEn, tab.labelZh)}</span>
                {count > 0 ? <StatusBadge tone={selected ? "positive" : "neutral"}>{count}</StatusBadge> : null}
              </div>
              <span className="workspace-sidebar__item-detail">{copy(tab.detailEn, tab.detailZh)}</span>
            </button>
          );
        })}
      </nav>

      <div className="workspace-sidebar__footer">
        <div className="workspace-sidebar__footer-title">{copy("Local-first collaboration", "本地优先协作")}</div>
        <div className="workspace-sidebar__footer-row">
          <StatusBadge tone="positive">{copy("offline-ready", "离线可用")}</StatusBadge>
          <StatusBadge tone="neutral">{copy("desktop approvals", "桌面确认")}</StatusBadge>
        </div>
      </div>
    </aside>
  );
}
