import { useEffect, useState } from "react";
import { Panel, StatusBadge } from "../../components";
import { apiClient } from "../../lib/api";
import { formatCompactDate } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { SkillRecord } from "../../lib/types";
import { SkillsView } from "./SkillsView";

export function SkillsPage() {
  const { copy } = useI18n();
  const [skills, setSkills] = useState<SkillRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);

  const loadSkills = async () => {
    setLoading(true);
    try {
      const items = await apiClient.listSkills();
      setSkills(items);
      setError(null);
      setLastRefreshedAt(new Date().toISOString());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : copy("Failed to load skills.", "加载 Skills 失败。"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSkills();
  }, []);

  if (loading && skills.length === 0) {
    return (
      <Panel title={copy("Skill registry", "Skill 注册表")} eyebrow={copy("Learning gates", "学习关卡")} description={copy("Loading skills from the local backend...", "正在从本地后端加载 Skills...")}>
        <div style={{ color: "rgba(233,239,255,0.72)", fontSize: "14px" }}>{copy("Synchronizing skill state.", "正在同步 skill 状态。")}</div>
      </Panel>
    );
  }

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      {error ? (
        <Panel
          title={copy("Skill registry", "Skill 注册表")}
          eyebrow={copy("Learning gates", "学习关卡")}
          description={copy("The desktop client could not refresh skill data from the backend.", "桌面客户端无法从后端刷新 skill 数据。")}
          actions={<StatusBadge tone="critical">error</StatusBadge>}
        >
          <div style={{ display: "grid", gap: "12px" }}>
            <div style={{ color: "rgba(233,239,255,0.78)", lineHeight: 1.6 }}>{error}</div>
            <button
              type="button"
              onClick={() => void loadSkills()}
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
            ? copy("Refreshing skill registry...", "正在刷新 Skill 注册表...")
            : lastRefreshedAt
              ? copy(`Last refreshed ${formatCompactDate(lastRefreshedAt)}`, `最近刷新于 ${formatCompactDate(lastRefreshedAt)}`)
              : copy("Skill registry is loaded from the backend.", "Skill 注册表已从后端加载。")}
        </div>
        <button
          type="button"
          onClick={() => void loadSkills()}
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

      <SkillsView skills={skills} />
    </div>
  );
}
