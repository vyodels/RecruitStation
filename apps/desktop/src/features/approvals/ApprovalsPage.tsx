import { useEffect, useState } from "react";
import { Panel, StatusBadge } from "../../components";
import { apiClient } from "../../lib/api";
import { formatCompactDate } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { ApprovalItem } from "../../lib/types";
import { ApprovalsView } from "./ApprovalsView";

export function ApprovalsPage() {
  const { copy } = useI18n();
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const [pendingActionId, setPendingActionId] = useState<string>();

  const loadApprovals = async () => {
    setLoading(true);
    try {
      const items = await apiClient.listApprovals();
      setApprovals(items);
      setError(null);
      setLastRefreshedAt(new Date().toISOString());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : copy("Failed to load approvals.", "加载审批失败。"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadApprovals();
  }, []);

  const handleApprove = async (id: string) => {
    setPendingActionId(id);
    try {
      await apiClient.approveItem(id);
      await loadApprovals();
    } finally {
      setPendingActionId(undefined);
    }
  };

  const handleReject = async (id: string) => {
    setPendingActionId(id);
    try {
      await apiClient.rejectItem(id, "Rejected from approvals page.");
      await loadApprovals();
    } finally {
      setPendingActionId(undefined);
    }
  };

  if (loading && approvals.length === 0) {
    return (
      <Panel title={copy("Approval queue", "审批队列")} eyebrow={copy("Human gates", "人工关卡")} description={copy("Loading approvals from the local backend...", "正在从本地后端加载审批数据...")}>
        <div style={{ color: "rgba(233,239,255,0.72)", fontSize: "14px" }}>{copy("Synchronizing approval state.", "正在同步审批状态。")}</div>
      </Panel>
    );
  }

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      {error ? (
        <Panel
          title={copy("Approval queue", "审批队列")}
          eyebrow={copy("Human gates", "人工关卡")}
          description={copy("The desktop client could not refresh approval data from the backend.", "桌面客户端无法从后端刷新审批数据。")}
          actions={<StatusBadge tone="critical">error</StatusBadge>}
        >
          <div style={{ display: "grid", gap: "12px" }}>
            <div style={{ color: "rgba(233,239,255,0.78)", lineHeight: 1.6 }}>{error}</div>
            <button
              type="button"
              onClick={() => void loadApprovals()}
              style={{
                alignSelf: "start",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: "12px",
                background: "rgba(122,167,255,0.18)",
                color: "#eef3ff",
                padding: "10px 14px",
                cursor: "pointer",
                fontWeight: 700,
              }}
            >
              {copy("Retry", "重试")}
            </button>
          </div>
        </Panel>
      ) : null}

      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center" }}>
        <div style={{ color: "rgba(233,239,255,0.72)", fontSize: "13px" }}>
          {loading
            ? copy("Refreshing approval queue...", "正在刷新审批队列...")
            : lastRefreshedAt
              ? copy(`Last refreshed ${formatCompactDate(lastRefreshedAt)}`, `最近刷新于 ${formatCompactDate(lastRefreshedAt)}`)
              : copy("Approval queue is loaded from the backend.", "审批队列已从后端加载。")}
        </div>
        <button
          type="button"
          onClick={() => void loadApprovals()}
          disabled={loading}
          style={{
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: "12px",
            background: "rgba(122,167,255,0.18)",
            color: "#eef3ff",
            padding: "10px 14px",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 700,
          }}
        >
          {loading ? copy("Refreshing...", "刷新中...") : copy("Refresh", "刷新")}
        </button>
      </div>

      <ApprovalsView approvals={approvals} pendingActionId={pendingActionId} onApprove={handleApprove} onReject={handleReject} />
    </div>
  );
}
