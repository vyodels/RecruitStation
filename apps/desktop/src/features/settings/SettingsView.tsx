import React, { useEffect, useState } from "react";
import { Panel, StatusBadge } from "../../components";
import { useI18n } from "../../lib/i18n";
import { translateUiToken } from "../../lib/uiText";
import type { ProviderConfig, SettingsSnapshot } from "../../lib/types";

interface SettingsViewProps {
  settings: SettingsSnapshot;
  saving?: boolean;
  onSave(settings: Partial<SettingsSnapshot>): Promise<void> | void;
}

function translateSettingLabel(value: string): string {
  const table: Record<string, string> = {
    "Recruiting scene profile": "招聘场景配置",
    "Runtime scene profile": "内部执行配置",
    "Primary OpenAI API": "主 OpenAI 接口",
    "Fallback Anthropic": "备用 Anthropic 接口",
  };
  return table[value] ?? value;
}

const inputStyle = {
  width: "100%",
  borderRadius: "12px",
  border: "1px solid rgba(255,255,255,0.12)",
  background: "rgba(255,255,255,0.03)",
  color: "inherit",
  padding: "10px 12px",
} as const;

const providerHintStyle = {
  color: "rgba(233,239,255,0.6)",
  fontSize: "12px",
  lineHeight: 1.6,
} as const;

function providerHostExample(kind: ProviderConfig["kind"]): { example: string; noteEn: string; noteZh: string } {
  if (kind === "anthropic") {
    return {
      example: "https://api.anthropic.com",
      noteEn: "Only fill the host/base URL. Do not include a concrete endpoint path. Anthropic stays config-only for now.",
      noteZh: "只填写 host/base URL，不要填写具体接口路径。Anthropic 结构先保留，内部调用后续再接。",
    };
  }
  return {
    example: "https://api.openai.com/v1 / https://openrouter.ai/api/v1 / http://127.0.0.1:8317/v1",
    noteEn: "Only fill the base path, for example `/v1`. Do not include concrete endpoints like `/chat/completions` or `/responses`.",
    noteZh: "只填写到基础路径，例如 `/v1`；不要填写 `/chat/completions`、`/responses` 这类具体接口。",
  };
}

export function SettingsView({ settings, saving, onSave }: SettingsViewProps): JSX.Element {
  const { copy } = useI18n();
  const [draft, setDraft] = useState(settings);

  useEffect(() => {
    setDraft(settings);
  }, [settings]);

  const updateProvider = (index: number, patch: Partial<ProviderConfig>) => {
    setDraft((current) => ({
      ...current,
      providers: current.providers.map((provider, providerIndex) =>
        providerIndex === index ? { ...provider, ...patch } : provider,
      ),
    }));
  };

  return (
    <div style={{ display: "grid", gap: "18px", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
      <Panel title={copy("Execution settings", "执行设置")} eyebrow={copy("Local-first", "本地优先")} description={copy("Base workspace settings and safety gates.", "工作台基础设置与安全控制。")}>
        <div style={{ display: "grid", gap: "10px" }}>
          <StatusBadge tone={draft.desktopApprovalsOnly ? "warning" : "neutral"}>{draft.desktopApprovalsOnly ? copy("desktop approvals only", "仅桌面审批") : copy("mixed approvals", "混合审批")}</StatusBadge>
          <StatusBadge tone={draft.intranetEnabled ? "positive" : "neutral"}>{draft.intranetEnabled ? copy("intranet sync enabled", "已启用内网同步") : copy("no intranet sync", "未启用内网同步")}</StatusBadge>
          <StatusBadge tone={draft.skillHealthAutonomyEnabled ? "positive" : "neutral"}>
            {draft.skillHealthAutonomyEnabled
              ? copy(`skill health autonomy every ${draft.skillHealthAutonomyIntervalSeconds}s`, `skill health 巡检每 ${draft.skillHealthAutonomyIntervalSeconds} 秒执行一次`)
              : copy("skill health autonomy idle", "skill health 巡检未启用")}
          </StatusBadge>
          <div style={{ color: "rgba(233,239,255,0.72)", fontSize: "13px" }}>
            {copy("Locale", "语言区域")} {draft.locale} · {copy("Timezone", "时区")} {draft.timezone}
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "14px" }}>
            <input
              type="checkbox"
              checked={draft.intranetEnabled}
              onChange={(event) => setDraft((current) => ({ ...current, intranetEnabled: event.target.checked }))}
            />
            {copy("Enable intranet sync", "启用内网同步")}
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "14px" }}>
            <input
              type="checkbox"
              checked={draft.desktopApprovalsOnly}
              onChange={(event) => setDraft((current) => ({ ...current, desktopApprovalsOnly: event.target.checked }))}
            />
            {copy("Keep approvals desktop-only", "审批仅在桌面端完成")}
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "14px" }}>
            <input
              type="checkbox"
              checked={draft.skillHealthAutonomyEnabled}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  skillHealthAutonomyEnabled: event.target.checked,
                }))
              }
            />
            {copy("Enable periodic skill health autonomy", "启用周期性 skill health 巡检")}
          </label>
          <label style={{ display: "grid", gap: "6px", fontSize: "13px", color: "rgba(233,239,255,0.72)" }}>
            {copy("Skill health autonomy interval (seconds)", "skill health 巡检间隔（秒）")}
            <input
              type="number"
              min={1}
              value={draft.skillHealthAutonomyIntervalSeconds ?? 300}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  skillHealthAutonomyIntervalSeconds: Number(event.target.value || current.skillHealthAutonomyIntervalSeconds || 300),
                }))
              }
              style={inputStyle}
            />
          </label>
        </div>
      </Panel>
      <Panel title={copy("Platform profile", "平台配置")} eyebrow={translateSettingLabel(draft.platform.name)} description={copy("Current platform account and contact policy.", "当前平台账号与联络策略。")}>
        <div style={{ display: "grid", gap: "10px" }}>
          <label style={{ display: "grid", gap: "6px", fontSize: "13px", color: "rgba(233,239,255,0.72)" }}>
            {copy("Account", "账号")}
            <input
              type="text"
              value={draft.platform.account}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  platform: { ...current.platform, account: event.target.value },
                }))
              }
              style={inputStyle}
            />
          </label>
          <label style={{ display: "grid", gap: "6px", fontSize: "13px", color: "rgba(233,239,255,0.72)" }}>
            {copy("Cooldown days", "冷却天数")}
            <input
              type="number"
              min={1}
              value={draft.platform.cooldownDays}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  platform: {
                    ...current.platform,
                    cooldownDays: Number(event.target.value || current.platform.cooldownDays),
                  },
                }))
              }
              style={inputStyle}
            />
          </label>
          <label style={{ display: "grid", gap: "6px", fontSize: "13px", color: "rgba(233,239,255,0.72)" }}>
            {copy("Max concurrent AgentRuns", "最大并发 AgentRun")}
            <input
              type="number"
              min={1}
              value={draft.platform.maxConcurrentRuns}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  platform: {
                    ...current.platform,
                    maxConcurrentRuns: Math.max(1, Number(event.target.value || current.platform.maxConcurrentRuns || 1)),
                  },
                }))
              }
              style={inputStyle}
            />
          </label>
          <label style={{ display: "grid", gap: "6px", fontSize: "13px", color: "rgba(233,239,255,0.72)" }}>
            {copy("Boss max concurrent AgentRuns", "Boss 最大并发 AgentRun")}
            <input
              type="number"
              min={1}
              value={draft.platform.bossMaxConcurrentRuns ?? draft.platform.maxConcurrentRuns}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  platform: {
                    ...current.platform,
                    bossMaxConcurrentRuns: Math.max(
                      1,
                      Number(event.target.value || current.platform.bossMaxConcurrentRuns || current.platform.maxConcurrentRuns || 1),
                    ),
                  },
                }))
              }
              style={inputStyle}
            />
            <span style={providerHintStyle}>
              {copy(
                "Use this to cap concurrent runs on Boss separately when the site has stricter bot risk controls.",
                "如果 Boss 的风控更严格，可以单独限制 Boss 平台的并发 run 数量。",
              )}
            </span>
          </label>
          <StatusBadge tone={draft.platform.allowOutboundMessaging ? "positive" : "warning"}>
            {draft.platform.allowOutboundMessaging ? copy("outbound messaging on", "允许外发消息") : copy("outbound messaging gated", "外发消息受控")}
          </StatusBadge>
          <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "14px" }}>
            <input
              type="checkbox"
              checked={draft.platform.allowOutboundMessaging}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  platform: { ...current.platform, allowOutboundMessaging: event.target.checked },
                }))
              }
            />
            {copy("Allow outbound messaging", "允许外发消息")}
          </label>
        </div>
      </Panel>
      <Panel title={copy("Providers", "模型提供方")} eyebrow={copy("LLM routing", "LLM 路由")} description={copy("Provider preferences and deployment targets.", "模型提供方偏好与部署目标。")}>
        <div style={{ display: "grid", gap: "10px" }}>
          {draft.providers.map((provider, index) => {
            const hint = providerHostExample(provider.kind);
            return (
              <article key={provider.name} style={{ padding: "14px", borderRadius: "16px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
                  <strong>{translateSettingLabel(provider.name)}</strong>
                  <StatusBadge tone={provider.enabled ? "positive" : "neutral"}>{translateUiToken(provider.kind.replace(/-/g, "_"), copy)}</StatusBadge>
                </div>
                <div style={{ display: "grid", gap: "10px", marginTop: "10px" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "14px" }}>
                    <input
                      type="checkbox"
                      checked={provider.enabled}
                      onChange={(event) => updateProvider(index, { enabled: event.target.checked })}
                    />
                    {copy("Enable this provider", "启用该提供方")}
                  </label>
                  <label style={{ display: "grid", gap: "6px", fontSize: "13px", color: "rgba(233,239,255,0.72)" }}>
                    {copy("Model", "模型")}
                    <input
                      type="text"
                      value={provider.model}
                      onChange={(event) => updateProvider(index, { model: event.target.value })}
                      style={inputStyle}
                      placeholder={provider.kind === "anthropic" ? "claude-sonnet-4" : "gpt-5.4"}
                    />
                  </label>
                  <label style={{ display: "grid", gap: "6px", fontSize: "13px", color: "rgba(233,239,255,0.72)" }}>
                    {copy("Host / Base URL", "Host / Base URL")}
                    <input
                      type="text"
                      value={provider.baseUrl ?? ""}
                      onChange={(event) => updateProvider(index, { baseUrl: event.target.value })}
                      style={inputStyle}
                      placeholder={hint.example}
                    />
                    <span style={providerHintStyle}>
                      {copy(`Example: ${hint.example}`, `示例：${hint.example}`)}
                    </span>
                    <span style={providerHintStyle}>{copy(hint.noteEn, hint.noteZh)}</span>
                  </label>
                  <label style={{ display: "grid", gap: "6px", fontSize: "13px", color: "rgba(233,239,255,0.72)" }}>
                    {copy("API key", "API Key")}
                    <input
                      type="password"
                      value={provider.apiKey ?? ""}
                      onChange={(event) => updateProvider(index, { apiKey: event.target.value })}
                      style={inputStyle}
                      placeholder={provider.kind === "anthropic" ? "sk-ant-..." : "sk-..."}
                      autoComplete="off"
                    />
                    <span style={providerHintStyle}>
                      {copy(
                        "The key is stored locally in the backend settings store and reused after restart.",
                        "Key 会保存到本地后端设置存储中，重启后仍会继续使用。",
                      )}
                    </span>
                  </label>
                </div>
              </article>
            );
          })}
        </div>
        <div style={{ marginTop: "14px", display: "flex", justifyContent: "flex-end" }}>
          <button
            type="button"
            onClick={() =>
              onSave({
                intranetEnabled: draft.intranetEnabled,
                desktopApprovalsOnly: draft.desktopApprovalsOnly,
                skillHealthAutonomyEnabled: draft.skillHealthAutonomyEnabled,
                skillHealthAutonomyIntervalSeconds: draft.skillHealthAutonomyIntervalSeconds,
                platform: draft.platform,
                providers: draft.providers,
              })
            }
            disabled={saving}
            style={{
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: "12px",
              background: "rgba(122,167,255,0.18)",
              color: "#eef3ff",
              padding: "10px 14px",
              cursor: "pointer",
              fontWeight: 700,
            }}
          >
            {saving ? copy("Saving...", "保存中...") : copy("Save settings", "保存设置")}
          </button>
        </div>
      </Panel>
    </div>
  );
}
