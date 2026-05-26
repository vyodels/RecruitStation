import React from "react";
import { FormTextarea } from "../../components";
import { useI18n } from "../../lib/i18n";
import type { AgentKind } from "../../lib/types";

export interface ChatComposerCommand {
  id: string;
  command: string;
  title: string;
  description: string;
  disabled?: boolean;
}

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
  commandItems?: ChatComposerCommand[];
  onCommand?(commandId: string): void;
  shouldSubmitOnEnter?(value: string): boolean;
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
  commandItems = [],
  onCommand,
  shouldSubmitOnEnter,
}: ChatComposerProps): JSX.Element {
  const { copy } = useI18n();
  const commandQuery = commandQueryFromValue(value);
  const matchingCommands = commandQuery == null
    ? []
    : commandItems.filter((item) => commandMatches(item, commandQuery));
  const primaryCommand = matchingCommands.find((item) => !item.disabled);
  const commandPaletteVisible = commandQuery != null;
  const submitBlocked = submitDisabled || (submitRequiresValue && !value.trim());

  const executeCommand = (command: ChatComposerCommand | undefined) => {
    if (!command || command.disabled) {
      return;
    }
    onCommand?.(command.id);
  };

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

      {commandPaletteVisible ? (
        <div className="chat-composer-command-palette" role="listbox" aria-label={copy("Commands", "命令")}>
          {matchingCommands.length ? matchingCommands.map((command, index) => (
            <button
              key={command.id}
              type="button"
              role="option"
              aria-selected={index === 0}
              data-active={index === 0 ? "true" : "false"}
              disabled={command.disabled}
              onClick={() => executeCommand(command)}
            >
              <span className="chat-composer-command-palette__command">/{command.command}</span>
              <span className="chat-composer-command-palette__body">
                <strong>{command.title}</strong>
                <small>{command.description}</small>
              </span>
              {index === 0 && !command.disabled ? <kbd>Enter</kbd> : null}
            </button>
          )) : (
            <div className="chat-composer-command-palette__empty">
              {copy("No matching commands", "没有匹配的命令")}
            </div>
          )}
        </div>
      ) : null}

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
            if (event.key === "Enter" && !event.shiftKey && commandPaletteVisible) {
              event.preventDefault();
              executeCommand(primaryCommand);
              return;
            }
            if (event.key === "Enter" && !event.shiftKey && shouldSubmitOnEnter?.(value)) {
              event.preventDefault();
              onSubmit();
              return;
            }
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
          disabled={submitBlocked}
        >
          {submitLabel || copy("Send", "发送")}
        </button>
      </div>

      <div className="chat-composer__hint">{copy("Cmd/Ctrl + Enter to send · Enter keeps newline", "Cmd/Ctrl + Enter 发送 · Enter 保留换行")}</div>
    </div>
  );
}

function commandQueryFromValue(value: string): string | null {
  const trimmed = value.trimStart();
  if (!trimmed.startsWith("/") || trimmed.includes("\n")) {
    return null;
  }
  const commandText = trimmed.slice(1);
  if (/\s/.test(commandText)) {
    return null;
  }
  return commandText.toLowerCase();
}

function commandMatches(command: ChatComposerCommand, query: string): boolean {
  if (!query) {
    return true;
  }
  const normalized = query.toLowerCase();
  return (
    command.command.toLowerCase().startsWith(normalized)
    || command.title.toLowerCase().includes(normalized)
    || command.description.toLowerCase().includes(normalized)
  );
}
