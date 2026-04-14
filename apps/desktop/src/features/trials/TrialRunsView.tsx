import React from "react";
import { Panel, StatusBadge } from "../../components";
import { formatCompactDate } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { theme } from "../../lib/theme";
import type { RuntimeEpisode, RuntimeExecutionPlan, RuntimeSnapshot, RuntimeTaskSpec } from "../../lib/types";

interface TrialRunsViewProps {
  episodes: RuntimeEpisode[];
  taskSpecs: RuntimeTaskSpec[];
  plans: RuntimeExecutionPlan[];
  snapshots: RuntimeSnapshot[];
  busyEpisodeId?: string;
  onExecute(episodeId: string): void;
  onLearn(episodeId: string): void;
  onConfirm(episodeId: string): void;
}

const buttonStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: "12px",
  padding: "8px 12px",
  cursor: "pointer",
  fontWeight: 700,
} as const;

export function TrialRunsView({
  episodes,
  taskSpecs,
  plans,
  snapshots,
  busyEpisodeId,
  onExecute,
  onLearn,
  onConfirm,
}: TrialRunsViewProps): JSX.Element {
  const { copy } = useI18n();

  return (
    <Panel
      title={copy("Supervised trial runs", "受监督试跑")}
      eyebrow={copy("Trial runner", "试跑执行器")}
      description={copy("New plans execute here first. Each run records actions, observations, snapshots, divergence, and learning candidates.", "新计划会先在这里执行。每次运行都会记录动作、观察、快照、偏差和学习候选项。")}
    >
      <div style={{ display: "grid", gap: "12px" }}>
        {episodes.map((episode) => {
          const task = taskSpecs.find((item) => item.id === episode.taskSpecId);
          const plan = plans.find((item) => item.id === episode.executionPlanId);
          const snapshot = snapshots.find((item) => item.executionEpisodeId === episode.id);
          const busy = busyEpisodeId === episode.id;
          return (
            <article
              key={episode.id}
              style={{
                borderRadius: "18px",
                border: `1px solid ${theme.colors.border}`,
                background: "rgba(255,255,255,0.03)",
                padding: "16px",
                display: "grid",
                gap: "10px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                    <strong>{task?.title ?? episode.id}</strong>
                    <StatusBadge tone="neutral">{task?.domain ?? copy("general", "通用")}</StatusBadge>
                    <StatusBadge tone={episode.divergenceDetected ? "critical" : episode.status === "awaiting_review" ? "warning" : "positive"}>
                      {episode.status}
                    </StatusBadge>
                  </div>
                  <div style={{ marginTop: "6px", color: theme.colors.muted, fontSize: "13px" }}>
                    {plan?.name ?? copy("Unnamed plan", "未命名计划")} · {episode.mode} · {copy(`${episode.actions.length} actions`, `${episode.actions.length} 个动作`)} · {copy(`${episode.observations.length} observations`, `${episode.observations.length} 个观察`)}
                  </div>
                </div>
                <div style={{ color: "rgba(233,239,255,0.56)", fontSize: "12px" }}>
                  {episode.finishedAt ? copy(`Finished ${formatCompactDate(episode.finishedAt)}`, `完成于 ${formatCompactDate(episode.finishedAt)}`) : copy(`Created ${formatCompactDate(episode.createdAt)}`, `创建于 ${formatCompactDate(episode.createdAt)}`)}
                </div>
              </div>
              {episode.resultSummary ? (
                <div style={{ color: "rgba(233,239,255,0.74)", fontSize: "13px", lineHeight: 1.5 }}>{episode.resultSummary}</div>
              ) : null}
              {snapshot ? (
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <StatusBadge tone="neutral">{snapshot.pageType ?? snapshot.source}</StatusBadge>
                  {snapshot.url ? <StatusBadge tone="neutral">{snapshot.url}</StatusBadge> : null}
                </div>
              ) : null}
              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                {episode.status === "pending" ? (
                  <button
                    type="button"
                    onClick={() => onExecute(episode.id)}
                    disabled={busy}
                    style={{ ...buttonStyle, background: "rgba(93,216,163,0.14)", color: "#d7ffef" }}
                  >
                    {busy ? copy("Executing...", "执行中...") : copy("Execute trial", "执行试跑")}
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => onLearn(episode.id)}
                  disabled={busy}
                  style={{ ...buttonStyle, background: "rgba(122,167,255,0.16)", color: "#edf4ff" }}
                >
                  {busy ? copy("Working...", "处理中...") : copy("Refresh learning", "刷新学习结果")}
                </button>
                {episode.requiresConfirmation || episode.status === "awaiting_review" ? (
                  <button
                    type="button"
                    onClick={() => onConfirm(episode.id)}
                    disabled={busy}
                    style={{ ...buttonStyle, background: "rgba(93,216,163,0.14)", color: "#d7ffef" }}
                  >
                    {busy ? copy("Confirming...", "确认中...") : copy("Confirm trial", "确认试跑")}
                  </button>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>
    </Panel>
  );
}
