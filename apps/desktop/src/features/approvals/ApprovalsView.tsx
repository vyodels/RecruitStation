import React from "react";
import { Panel, StatusBadge } from "../../components";
import { useI18n } from "../../lib/i18n";
import { translateUiToken } from "../../lib/uiText";
import type { ApprovalItem } from "../../lib/types";

interface ApprovalsViewProps {
  approvals: ApprovalItem[];
  pendingActionId?: string;
  onApprove(id: string): void;
  onReject(id: string): void;
}

const buttonStyle = {
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: "12px",
  padding: "8px 12px",
  cursor: "pointer",
  fontWeight: 700,
} as const;

export function ApprovalsView({ approvals, pendingActionId, onApprove, onReject }: ApprovalsViewProps): JSX.Element {
  const { copy } = useI18n();

  return (
    <Panel
      title={copy("Approval queue", "审批队列")}
      eyebrow={copy("Human gates", "人工关卡")}
      description={copy("Every item here blocks automation until it is explicitly accepted or rejected.", "这里的每一项都会阻塞自动化，直到被明确批准或拒绝。")}
    >
      <div style={{ display: "grid", gap: "12px" }}>
        {approvals.map((approval) => (
          <article key={approval.id} style={{ padding: "14px", borderRadius: "16px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "10px", alignItems: "start" }}>
              <div>
                <div style={{ fontWeight: 700 }}>{approval.title}</div>
                <div style={{ color: "rgba(233,239,255,0.68)", fontSize: "13px", marginTop: "4px", lineHeight: 1.5 }}>{approval.detail}</div>
              </div>
              <StatusBadge tone={approval.status === "pending" ? "warning" : approval.status === "approved" ? "positive" : "critical"}>{translateUiToken(approval.status, copy)}</StatusBadge>
            </div>
            <div style={{ marginTop: "10px", color: "rgba(233,239,255,0.56)", fontSize: "12px" }}>
              {copy("Requester", "提交方")} {approval.requester} · {approval.kind} · {approval.createdAt}
            </div>
            {approval.status === "pending" ? (
              <div style={{ display: "flex", gap: "10px", marginTop: "12px" }}>
                <button
                  type="button"
                  onClick={() => onApprove(approval.id)}
                  disabled={pendingActionId === approval.id}
                  style={{ ...buttonStyle, background: "rgba(93,216,163,0.14)", color: "#d7ffef" }}
                >
                  {pendingActionId === approval.id ? copy("Working...", "处理中...") : copy("Approve", "批准")}
                </button>
                <button
                  type="button"
                  onClick={() => onReject(approval.id)}
                  disabled={pendingActionId === approval.id}
                  style={{ ...buttonStyle, background: "rgba(255,122,122,0.12)", color: "#ffd9d9" }}
                >
                  {copy("Reject", "拒绝")}
                </button>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </Panel>
  );
}
