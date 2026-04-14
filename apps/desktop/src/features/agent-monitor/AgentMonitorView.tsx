import React from "react";
import { Panel, StatusBadge, Timeline } from "../../components";
import { formatCompactDate } from "../../lib/format";
import { theme } from "../../lib/theme";
import type { AgentEvent, AgentQueueItem, AgentSnapshot, RuntimeEpisode, RuntimeEpisodeReplay, SyncBacklogItem, SyncStatusSnapshot } from "../../lib/types";

interface AgentMonitorViewProps {
  agent: AgentSnapshot;
  events: AgentEvent[];
  episodes?: RuntimeEpisode[];
  selectedEpisodeId?: string;
  replay?: RuntimeEpisodeReplay | null;
  syncStatus?: SyncStatusSnapshot | null;
  syncBacklog?: SyncBacklogItem[];
  queueItems?: AgentQueueItem[];
  runningAction?: boolean;
  syncingAction?: boolean;
  onRunOnce(): void;
  onQueueScreeningTask(): void;
  onFlushSync?(): void;
  onSelectEpisode?(episodeId: string): void;
}

const actionButtonStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: "12px",
  background: "rgba(122,167,255,0.18)",
  color: "#eef3ff",
  padding: "10px 12px",
  cursor: "pointer",
  fontWeight: 700,
} as const;

function backlogTone(status: string): "positive" | "neutral" | "warning" | "critical" {
  if (/(error|failed)/i.test(status)) {
    return "critical";
  }
  if (/(pending|retry|queued)/i.test(status)) {
    return "warning";
  }
  if (/(synced|completed)/i.test(status)) {
    return "positive";
  }
  return "neutral";
}

function syncModeDescription(syncStatus?: SyncStatusSnapshot | null): string {
  if (!syncStatus) {
    return "No sync status available.";
  }
  if (!syncStatus.enabled) {
    return "Remote sync is disabled. Backlog entries stay local until an intranet target is enabled.";
  }
  if (!syncStatus.remoteAvailable) {
    return "Remote sync is enabled, but the target is currently unavailable.";
  }
  return "Remote sync is enabled and reachable.";
}

export function AgentMonitorView({
  agent,
  events,
  episodes = [],
  selectedEpisodeId,
  replay,
  syncStatus,
  syncBacklog = [],
  queueItems = [],
  runningAction,
  syncingAction,
  onRunOnce,
  onQueueScreeningTask,
  onFlushSync,
  onSelectEpisode,
}: AgentMonitorViewProps): JSX.Element {
  return (
    <div style={{ display: "grid", gap: "18px" }}>
      <div style={{ display: "grid", gap: "18px", gridTemplateColumns: "minmax(0, 1.1fr) minmax(320px, 0.9fr)" }}>
        <Panel
          title="Agent runtime"
          eyebrow="Serialized execution"
          description="Current run state, browser lock status, and direct operator actions."
          actions={
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button type="button" onClick={onQueueScreeningTask} disabled={runningAction} style={actionButtonStyle}>
                Queue recruiting task
              </button>
              <button type="button" onClick={onRunOnce} disabled={runningAction} style={actionButtonStyle}>
                {runningAction ? "Running..." : "Run next task"}
              </button>
            </div>
          }
        >
          <div style={{ display: "grid", gap: "12px" }}>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <StatusBadge tone={agent.status === "running" ? "positive" : agent.status === "waiting_human" ? "warning" : "neutral"}>{agent.status}</StatusBadge>
              <StatusBadge tone={agent.browserLock === "held" ? "warning" : "positive"}>{agent.browserLock}</StatusBadge>
              <StatusBadge tone={agent.health === "healthy" ? "positive" : agent.health === "warning" ? "warning" : "critical"}>{agent.health}</StatusBadge>
            </div>
            <div style={{ display: "grid", gap: "8px", color: "rgba(233,239,255,0.72)", fontSize: "13px" }}>
              <div>Active task: {agent.activeTask}</div>
              <div>Uptime: {agent.uptime}</div>
              <div>Queue depth: {agent.queueDepth}</div>
              <div>Token budget used: {agent.tokenBudgetUsed}%</div>
            </div>
          </div>
        </Panel>
        <Panel title="Sync backlog" eyebrow="Local-First Sync" description="Local backlog state and manual flush controls for optional intranet sync.">
          <div style={{ display: "grid", gap: "12px" }}>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <StatusBadge tone={syncStatus?.enabled ? "positive" : "neutral"}>{syncStatus?.mode ?? "local_only"}</StatusBadge>
              <StatusBadge tone={syncStatus?.remoteAvailable ? "positive" : "warning"}>
                {syncStatus?.remoteAvailable ? "remote reachable" : "remote unavailable"}
              </StatusBadge>
              <StatusBadge tone={syncStatus?.pendingCount ? "warning" : "positive"}>
                {syncStatus?.pendingCount ?? syncBacklog.length} pending
              </StatusBadge>
              {syncStatus?.failedDeliveryCount ? (
                <StatusBadge tone="warning">{syncStatus.failedDeliveryCount} failed deliveries</StatusBadge>
              ) : null}
              {syncStatus?.deferredCount ? <StatusBadge tone="neutral">{syncStatus.deferredCount} deferred</StatusBadge> : null}
            </div>
            <div style={{ color: theme.colors.muted, fontSize: "13px", lineHeight: 1.6 }}>
              {syncStatus?.recentErrors[0] ?? syncStatus?.latestError ?? syncModeDescription(syncStatus)}
            </div>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {syncStatus?.protocolVersion ? <StatusBadge tone="neutral">protocol {syncStatus.protocolVersion}</StatusBadge> : null}
              {syncStatus?.source ? <StatusBadge tone="neutral">source {syncStatus.source}</StatusBadge> : null}
              {typeof syncStatus?.backlogTotal === "number" ? <StatusBadge tone="neutral">{syncStatus.backlogTotal} total</StatusBadge> : null}
              {syncStatus?.lastAttemptAt ? <StatusBadge tone="neutral">Last attempt {formatCompactDate(syncStatus.lastAttemptAt)}</StatusBadge> : null}
              {syncStatus?.lastSuccessAt ? <StatusBadge tone="neutral">Last success {formatCompactDate(syncStatus.lastSuccessAt)}</StatusBadge> : null}
              {syncStatus?.nextAttemptAt ? <StatusBadge tone="neutral">Next retry {formatCompactDate(syncStatus.nextAttemptAt)}</StatusBadge> : null}
            </div>
            {syncStatus?.byStatus && Object.keys(syncStatus.byStatus).length ? (
              <div style={{ color: theme.colors.muted, fontSize: "13px", lineHeight: 1.6 }}>
                Status mix: {Object.entries(syncStatus.byStatus).map(([key, value]) => `${key}=${value}`).join(" · ")}
              </div>
            ) : null}
            {onFlushSync ? (
              <button type="button" onClick={onFlushSync} disabled={syncingAction} style={actionButtonStyle}>
                {syncingAction ? "Flushing..." : "Flush backlog"}
              </button>
            ) : null}
          </div>
        </Panel>
      </div>

      <Panel title="Queue audit" eyebrow="Persistent queue" description="Recent queued work and lifecycle audit emitted by the serialized scheduler.">
        <div style={{ display: "grid", gap: "12px" }}>
          {queueItems.length ? (
            queueItems.slice(0, 4).map((item) => (
              <article
                key={item.taskId}
                style={{
                  padding: "12px",
                  borderRadius: "14px",
                  border: "1px solid rgba(255,255,255,0.08)",
                  background: "rgba(255,255,255,0.03)",
                  display: "grid",
                  gap: "6px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", flexWrap: "wrap" }}>
                  <strong>{item.taskType}</strong>
                  <StatusBadge tone={backlogTone(item.status)}>{item.status}</StatusBadge>
                </div>
                <div style={{ color: theme.colors.muted, fontSize: "13px", lineHeight: 1.5 }}>
                  {item.taskId}
                  {item.candidateId ? ` · candidate ${item.candidateId}` : ""}
                  {item.workflowNodeId ? ` · node ${item.workflowNodeId}` : ""}
                </div>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <StatusBadge tone="neutral">priority {item.priority}</StatusBadge>
                  <StatusBadge tone="neutral">attempts {item.attempts}</StatusBadge>
                </div>
                {item.queueAudit.length ? (
                  <div style={{ color: theme.colors.muted, fontSize: "12px", lineHeight: 1.6 }}>
                    Audit:{" "}
                    {item.queueAudit
                      .slice(-3)
                      .map((entry) => `${entry.kind}${entry.error ? ` (${entry.error})` : ""}`)
                      .join(" → ")}
                  </div>
                ) : null}
              </article>
            ))
          ) : (
            <div style={{ color: theme.colors.muted, fontSize: "13px" }}>Queue audit will appear after the scheduler persists work items.</div>
          )}
        </div>
      </Panel>

      <div style={{ display: "grid", gap: "18px", gridTemplateColumns: "minmax(0, 1.1fr) minmax(320px, 0.9fr)" }}>
        <Panel title="Replay diagnostics" eyebrow="Episode Replay" description="Select a supervised episode to inspect divergence, snapshots, and derived learning artifacts.">
          <div style={{ display: "grid", gap: "12px" }}>
            {episodes.length ? (
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                {episodes.slice(0, 6).map((episode) => (
                  <button
                    key={episode.id}
                    type="button"
                    onClick={() => onSelectEpisode?.(episode.id)}
                    style={{
                      ...actionButtonStyle,
                      background: selectedEpisodeId === episode.id ? "rgba(122,167,255,0.28)" : "rgba(255,255,255,0.04)",
                    }}
                  >
                    {episode.id}
                  </button>
                ))}
              </div>
            ) : null}
            {replay ? (
              <div style={{ display: "grid", gap: "12px" }}>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <StatusBadge tone={replay.episode.divergenceDetected ? "critical" : "positive"}>{replay.episode.status}</StatusBadge>
                  {replay.patch ? <StatusBadge tone="warning">patch proposed</StatusBadge> : null}
                  {replay.template ? <StatusBadge tone="positive">template ready</StatusBadge> : null}
                  {replay.approval ? <StatusBadge tone="warning">approval pending</StatusBadge> : null}
                </div>
                <div style={{ color: theme.colors.muted, fontSize: "13px", lineHeight: 1.6 }}>
                  {replay.episode.resultSummary ?? "No replay summary available."}
                </div>
                <Timeline events={replay.diagnostics} />
              </div>
            ) : (
              <div style={{ color: theme.colors.muted, fontSize: "13px" }}>Replay diagnostics will appear after you select a trial episode.</div>
            )}
          </div>
        </Panel>
        <Panel title="Replay context" eyebrow="Snapshots and backlog" description="Captured environment state and the newest local sync backlog entries.">
          <div style={{ display: "grid", gap: "12px" }}>
            {replay?.snapshots?.length ? (
              replay.snapshots.map((snapshot) => (
                <article
                  key={snapshot.id}
                  style={{
                    padding: "14px",
                    borderRadius: "16px",
                    border: "1px solid rgba(255,255,255,0.08)",
                    background: "rgba(255,255,255,0.03)",
                    display: "grid",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", flexWrap: "wrap" }}>
                    <strong>{snapshot.title ?? snapshot.environmentKey ?? snapshot.id}</strong>
                    <StatusBadge tone="neutral">{snapshot.pageType ?? snapshot.source}</StatusBadge>
                  </div>
                  <div style={{ color: theme.colors.muted, fontSize: "13px" }}>{snapshot.url ?? "No URL captured."}</div>
                </article>
              ))
            ) : (
              <div style={{ color: theme.colors.muted, fontSize: "13px" }}>No replay snapshots available for the selected episode.</div>
            )}
            <div style={{ display: "grid", gap: "8px" }}>
              {syncBacklog.slice(0, 3).map((item) => (
                <article
                  key={item.id}
                  style={{
                    padding: "12px",
                    borderRadius: "14px",
                    border: "1px solid rgba(255,255,255,0.08)",
                    background: "rgba(255,255,255,0.03)",
                    display: "grid",
                    gap: "6px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", flexWrap: "wrap" }}>
                    <strong>{item.entityType}</strong>
                    <StatusBadge tone={backlogTone(item.status)}>{item.status}</StatusBadge>
                  </div>
                  <div style={{ color: theme.colors.muted, fontSize: "13px", lineHeight: 1.5 }}>
                    {item.payloadSummary ?? item.target}
                  </div>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    <StatusBadge tone="neutral">{item.target}</StatusBadge>
                    <StatusBadge tone="neutral">attempts {item.attemptCount}</StatusBadge>
                    {item.deliveryMode ? <StatusBadge tone="neutral">{item.deliveryMode}</StatusBadge> : null}
                    {item.protocolVersion ? <StatusBadge tone="neutral">protocol {item.protocolVersion}</StatusBadge> : null}
                  </div>
                  {(item.lastAttemptedAt || item.nextAttemptAt || item.lastError) ? (
                    <div style={{ color: theme.colors.muted, fontSize: "12px", lineHeight: 1.6 }}>
                      {item.lastAttemptedAt ? `Last attempt ${formatCompactDate(item.lastAttemptedAt)} · ` : ""}
                      {item.nextAttemptAt ? `Next retry ${formatCompactDate(item.nextAttemptAt)} · ` : ""}
                      {item.lastError ? `Error: ${item.lastError}` : "No delivery error recorded."}
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Runtime events" eyebrow="Agent stream" description="Events that can be surfaced in the final desktop event stream.">
        <Timeline
          events={events.map((event) => ({
            id: event.id,
            label: `${event.source}: ${event.message}`,
            detail: event.message,
            at: event.at,
            tone: event.level === "error" ? "critical" : event.level === "warning" ? "warning" : event.level === "success" ? "positive" : "neutral",
          }))}
        />
      </Panel>
    </div>
  );
}
