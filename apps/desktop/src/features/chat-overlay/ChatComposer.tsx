import React from "react";
import { FormTextarea } from "../../components";
import { useI18n } from "../../lib/i18n";
import type { AgentKind } from "../../lib/types";

interface ChatComposerProps {
  agentKind: AgentKind;
  inputDisabled?: boolean;
  submitDisabled?: boolean;
  submitRequiresValue?: boolean;
  modelLabel?: string | null;
  contextLabel?: string | null;
  submitLabel?: string | null;
  controlActions?: React.ReactNode;
  executionAction?: React.ReactNode;
  value: string;
  onChange(value: string): void;
  onSubmit(): void;
}

export function ChatComposer({
  agentKind,
  inputDisabled,
  submitDisabled,
  submitRequiresValue = true,
  modelLabel,
  contextLabel,
  submitLabel,
  controlActions,
  executionAction,
  value,
  onChange,
  onSubmit,
}: ChatComposerProps): JSX.Element {
  const { copy } = useI18n();

  return (
    <div className="chat-composer">
      <div className="chat-composer__bar">
        <div className="chat-composer__chips">
          <span className="chat-chip">
            {agentKind === "assistant" ? copy("AI assistant", "AI助手") : agentKind === "jd_sync" ? copy("JD sync", "JD 同步") : copy("Recruiting automation", "自动化招聘")}
          </span>
          {modelLabel ? <span className="chat-chip">{modelLabel}</span> : null}
          {contextLabel ? <span className="chat-chip">{contextLabel}</span> : null}
        </div>
        {controlActions ? <div className="chat-composer__controls">{controlActions}</div> : null}
      </div>

      <div className="chat-composer__box">
        <button type="button" className="chat-composer__icon-button" disabled aria-label={copy("Attachment coming soon", "附件能力后续补齐")}>
          +
        </button>
        <FormTextarea
          className="chat-composer__input"
          placeholder={
            agentKind === "assistant"
              ? copy("Ask the AI assistant to inspect or summarize the workspace…", "让 AI助手帮你分析或总结当前工作区…")
              : agentKind === "jd_sync"
                ? copy("Start the agent, then send JD sync follow-up instructions…", "启动 Agent 后，可发送 JD 同步后续指令…")
              : copy("Start the agent, then send the next automation instruction…", "启动 Agent 后，可发送下一条自动化指令…")
          }
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
              event.preventDefault();
              onSubmit();
            }
          }}
          disabled={inputDisabled}
        />
        {executionAction}
        <button
          type="button"
          className="chat-composer__submit"
          onClick={onSubmit}
          disabled={submitDisabled || (submitRequiresValue && !value.trim())}
        >
          {submitLabel || copy("Send", "发送")}
        </button>
      </div>

      <div className="chat-composer__hint">{copy("Cmd/Ctrl + Enter to send · Enter keeps newline", "Cmd/Ctrl + Enter 发送 · Enter 保留换行")}</div>
    </div>
  );
}
