import { useEffect, useState } from "react";
import { Panel, StatusBadge } from "../../components";
import { apiClient } from "../../lib/api";
import { formatCompactDate } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { DashboardSummary } from "../../lib/types";
import { DashboardView } from "../dashboard/DashboardView";

export function OverviewPage() {
  const { copy } = useI18n();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);

  const loadOverview = async () => {
    setLoading(true);
    try {
      const nextSummary = await apiClient.getDashboardSummary();
      setSummary(nextSummary);
      setError(null);
      setLastRefreshedAt(new Date().toISOString());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : copy("Failed to load dashboard overview.", "加载仪表盘概览失败。"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadOverview();
  }, []);

  if (loading && summary === null) {
    return (
      <Panel title={copy("Live command center", "实时指挥中心")} eyebrow={copy("Overview", "概览")} description={copy("Loading dashboard summary from the local backend...", "正在从本地后端加载仪表盘摘要...")}>
        <div style={{ color: "rgba(233,239,255,0.72)", fontSize: "14px" }}>{copy("Synchronizing workspace state.", "正在同步工作区状态。")}</div>
      </Panel>
    );
  }

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      {error ? (
        <Panel
          title={copy("Live command center", "实时指挥中心")}
          eyebrow={copy("Overview", "概览")}
          description={copy("The desktop client could not refresh the dashboard summary from the backend.", "桌面客户端无法从后端刷新仪表盘摘要。")}
          actions={<StatusBadge tone="critical">error</StatusBadge>}
        >
          <div style={{ display: "grid", gap: "12px" }}>
            <div style={{ color: "rgba(233,239,255,0.78)", lineHeight: 1.6 }}>{error}</div>
            <button
              type="button"
              onClick={() => void loadOverview()}
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
            ? copy("Refreshing dashboard summary...", "正在刷新仪表盘摘要...")
            : lastRefreshedAt
              ? copy(`Last refreshed ${formatCompactDate(lastRefreshedAt)}`, `最近刷新于 ${formatCompactDate(lastRefreshedAt)}`)
              : copy("Dashboard summary is loaded from the backend.", "仪表盘摘要已从后端加载。")}
        </div>
        <button
          type="button"
          onClick={() => void loadOverview()}
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

      {summary ? <DashboardView summary={summary} /> : null}
    </div>
  );
}
