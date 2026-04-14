import { useEffect, useState } from "react";
import { Panel, StatusBadge } from "../../components";
import { apiClient } from "../../lib/api";
import { formatCompactDate } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { SettingsSnapshot } from "../../lib/types";
import { SettingsView } from "./SettingsView";

export function SettingsPage() {
  const { copy } = useI18n();
  const [settings, setSettings] = useState<SettingsSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const nextSettings = await apiClient.getSettings();
      setSettings(nextSettings);
      setError(null);
      setLastRefreshedAt(new Date().toISOString());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : copy("Failed to load settings.", "加载设置失败。"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSettings();
  }, []);

  const handleSave = async (patch: Partial<SettingsSnapshot>) => {
    setSaving(true);
    try {
      const nextSettings = await apiClient.updateSettings(patch);
      setSettings(nextSettings);
      setLastRefreshedAt(new Date().toISOString());
      setError(null);
    } finally {
      setSaving(false);
    }
  };

  if (loading && settings === null) {
    return (
      <Panel title={copy("Execution settings", "执行设置")} eyebrow={copy("Local-first", "本地优先")} description={copy("Loading workspace settings from the local backend...", "正在从本地后端加载工作区设置...")}>
        <div style={{ color: "rgba(233,239,255,0.72)", fontSize: "14px" }}>{copy("Synchronizing settings state.", "正在同步设置状态。")}</div>
      </Panel>
    );
  }

  if (settings === null) {
    return (
      <Panel
        title={copy("Execution settings", "执行设置")}
        eyebrow={copy("Local-first", "本地优先")}
        description={copy("The desktop client could not load settings from the backend.", "桌面客户端无法从后端加载设置。")}
        actions={<StatusBadge tone="critical">error</StatusBadge>}
      >
        <div style={{ display: "grid", gap: "12px" }}>
          <div style={{ color: "rgba(233,239,255,0.78)", lineHeight: 1.6 }}>{error ?? copy("Unknown settings error.", "未知设置错误。")}</div>
          <button
            type="button"
            onClick={() => void loadSettings()}
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
    );
  }

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center" }}>
        <div style={{ color: "rgba(233,239,255,0.72)", fontSize: "13px" }}>
          {lastRefreshedAt ? copy(`Last refreshed ${formatCompactDate(lastRefreshedAt)}`, `最近刷新于 ${formatCompactDate(lastRefreshedAt)}`) : copy("Settings are loaded from the backend.", "设置已从后端加载。")}
        </div>
        <button
          type="button"
          onClick={() => void loadSettings()}
          disabled={loading || saving}
          style={{
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: "12px",
            background: "rgba(122,167,255,0.18)",
            color: "#eef3ff",
            padding: "10px 14px",
            cursor: loading || saving ? "not-allowed" : "pointer",
            fontWeight: 700,
          }}
        >
          {loading ? copy("Refreshing...", "刷新中...") : copy("Refresh", "刷新")}
        </button>
      </div>
      {error ? (
        <Panel
          title={copy("Execution settings", "执行设置")}
          eyebrow={copy("Local-first", "本地优先")}
          description={copy("The desktop client could not refresh settings from the backend.", "桌面客户端无法从后端刷新设置。")}
          actions={<StatusBadge tone="critical">error</StatusBadge>}
        >
          <div style={{ display: "grid", gap: "12px" }}>
            <div style={{ color: "rgba(233,239,255,0.78)", lineHeight: 1.6 }}>{error}</div>
            <button
              type="button"
              onClick={() => void loadSettings()}
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
      <SettingsView settings={settings} saving={saving} onSave={handleSave} />
    </div>
  );
}
