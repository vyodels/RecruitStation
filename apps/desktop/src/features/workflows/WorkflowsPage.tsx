import { useEffect, useState } from "react";
import { Panel, StatusBadge } from "../../components";
import { apiClient } from "../../lib/api";
import { formatCompactDate } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { WorkflowDefinition } from "../../lib/types";
import { WorkflowsView } from "./WorkflowsView";

export function WorkflowsPage() {
  const { copy } = useI18n();
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);

  const loadWorkflows = async () => {
    setLoading(true);
    try {
      const items = await apiClient.listWorkflows();
      setWorkflows(items);
      setError(null);
      setLastRefreshedAt(new Date().toISOString());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : copy("Failed to load workflows.", "加载工作流失败。"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadWorkflows();
  }, []);

  if (loading && workflows.length === 0) {
    return (
      <Panel title={copy("Workflow definitions", "工作流定义")} eyebrow={copy("Pipeline orchestration", "流水线编排")} description={copy("Loading workflows from the local backend...", "正在从本地后端加载工作流...")}>
        <div style={{ color: "rgba(233,239,255,0.72)", fontSize: "14px" }}>{copy("Synchronizing workflow state.", "正在同步工作流状态。")}</div>
      </Panel>
    );
  }

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      {error ? (
        <Panel
          title={copy("Workflow definitions", "工作流定义")}
          eyebrow={copy("Pipeline orchestration", "流水线编排")}
          description={copy("The desktop client could not refresh workflow data from the backend.", "桌面客户端无法从后端刷新工作流数据。")}
          actions={<StatusBadge tone="critical">error</StatusBadge>}
        >
          <div style={{ display: "grid", gap: "12px" }}>
            <div style={{ color: "rgba(233,239,255,0.78)", lineHeight: 1.6 }}>{error}</div>
            <button
              type="button"
              onClick={() => void loadWorkflows()}
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
            ? copy("Refreshing workflow definitions...", "正在刷新工作流定义...")
            : lastRefreshedAt
              ? copy(`Last refreshed ${formatCompactDate(lastRefreshedAt)}`, `最近刷新于 ${formatCompactDate(lastRefreshedAt)}`)
              : copy("Workflow definitions are loaded from the backend.", "工作流定义已从后端加载。")}
        </div>
        <button
          type="button"
          onClick={() => void loadWorkflows()}
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

      <WorkflowsView workflows={workflows} />
    </div>
  );
}
