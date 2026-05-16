import React from "react";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import type { AgentConversationMessage } from "../../lib/types";

interface ChatMessageStreamProps {
  loading?: boolean;
  messages: AgentConversationMessage[];
  renderTimelineAttachment?: (message: AgentConversationMessage) => React.ReactNode;
  variant?: "cards" | "timeline";
}

type Block =
  | { type: "paragraph"; lines: string[] }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "table"; header: string[]; rows: string[][] }
  | { type: "callout"; tone: "info" | "warning" | "success" | "critical"; title: string; lines: string[] }
  | { type: "code"; language: string | null; value: string }
  | { type: "diagram"; label: string; language: string; value: string };

interface Segment {
  type: "text" | "code";
  value: string;
  language: string | null;
}

function splitSegments(content: string): Segment[] {
  const segments: Segment[] = [];
  const pattern = /```([a-zA-Z0-9_-]+)?\n?([\s\S]*?)```/g;
  let cursor = 0;

  for (const match of content.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > cursor) {
      segments.push({
        type: "text",
        value: content.slice(cursor, index),
        language: null,
      });
    }
    segments.push({
      type: "code",
      language: match[1] ? match[1].trim().toLowerCase() : null,
      value: match[2].trim(),
    });
    cursor = index + match[0].length;
  }

  if (cursor < content.length) {
    segments.push({
      type: "text",
      value: content.slice(cursor),
      language: null,
    });
  }

  return segments.filter((segment) => segment.value.trim().length > 0);
}

function isMarkdownTable(lines: string[]): boolean {
  if (lines.length < 2) {
    return false;
  }
  const separator = lines[1].replace(/\|/g, "").trim();
  return lines[0].includes("|") && /^:?-{3,}:?(?:\s+:?-{3,}:?)*$/.test(separator.replace(/\s+/g, " "));
}

function parseTableRow(line: string): string[] {
  return line
    .split("|")
    .map((part) => part.trim())
    .filter((part, index, array) => !(index === 0 && part === "") && !(index === array.length - 1 && part === ""));
}

function parseCallout(lines: string[]): Block | null {
  if (!lines.length) {
    return null;
  }

  const match = lines[0].match(/^(IMPORTANT|WARNING|NOTE|TIP|SUCCESS|INFO|关键|重要|警告|提示|注意|结论)\s*[:：]\s*(.*)$/i);
  if (!match) {
    return null;
  }

  const keyword = match[1].toLowerCase();
  const title = match[1];
  const firstLine = match[2]?.trim();
  const tone =
    keyword === "warning" || keyword === "警告" || keyword === "注意"
      ? "warning"
      : keyword === "success"
        ? "success"
        : keyword === "important" || keyword === "关键" || keyword === "重要"
          ? "critical"
          : "info";

  return {
    type: "callout",
    tone,
    title,
    lines: [firstLine, ...lines.slice(1)].filter((line) => line.length > 0),
  };
}

function diagramLabelFor(language: string | null, value: string): string | null {
  const normalized = (language ?? "").toLowerCase();
  const firstLine = value.split("\n")[0]?.trim().toLowerCase() ?? "";

  if (normalized === "mermaid") {
    if (firstLine.startsWith("sequencediagram")) {
      return "时序图";
    }
    if (firstLine.startsWith("graph") || firstLine.startsWith("flowchart")) {
      return "流程图";
    }
    if (firstLine.startsWith("statediagram")) {
      return "状态图";
    }
    if (firstLine.startsWith("gantt")) {
      return "甘特图";
    }
    if (firstLine.startsWith("classdiagram")) {
      return "类图";
    }
    return "图示";
  }

  if (normalized === "flowchart") {
    return "流程图";
  }
  if (normalized === "sequence" || normalized === "sequence-diagram") {
    return "时序图";
  }
  if (normalized === "architecture" || normalized === "arch") {
    return "架构图";
  }
  if (normalized === "diagram" || normalized === "plantuml") {
    return "图示";
  }

  return null;
}

function textToBlocks(content: string): Block[] {
  const blocks: Block[] = [];
  const paragraphs = content
    .split(/\n{2,}/g)
    .map((part) => part.trim())
    .filter(Boolean);

  paragraphs.forEach((paragraph) => {
    const lines = paragraph.split("\n").map((line) => line.trimEnd()).filter((line) => line.trim().length > 0);
    if (!lines.length) {
      return;
    }

    const callout = parseCallout(lines);
    if (callout) {
      blocks.push(callout);
      return;
    }

    if (isMarkdownTable(lines)) {
      const [headerLine, , ...rowLines] = lines;
      blocks.push({
        type: "table",
        header: parseTableRow(headerLine),
        rows: rowLines.map(parseTableRow),
      });
      return;
    }

    if (lines.every((line) => /^\d+\.\s+/.test(line))) {
      blocks.push({
        type: "list",
        ordered: true,
        items: lines.map((line) => line.replace(/^\d+\.\s+/, "").trim()),
      });
      return;
    }

    if (lines.every((line) => /^[-*]\s+/.test(line))) {
      blocks.push({
        type: "list",
        ordered: false,
        items: lines.map((line) => line.replace(/^[-*]\s+/, "").trim()),
      });
      return;
    }

    blocks.push({
      type: "paragraph",
      lines,
    });
  });

  return blocks;
}

function contentToBlocks(content: string): Block[] {
  return splitSegments(content).flatMap((segment) => {
    if (segment.type === "text") {
      return textToBlocks(segment.value);
    }

    const label = diagramLabelFor(segment.language, segment.value);
    if (label) {
      return [
        {
          type: "diagram",
          label,
          language: segment.language ?? "diagram",
          value: segment.value,
        },
      ];
    }

    return [
      {
        type: "code",
        language: segment.language,
        value: segment.value,
      },
    ];
  });
}

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|==[^=]+==)/g;
  let cursor = 0;
  let index = 0;

  for (const match of text.matchAll(pattern)) {
    const start = match.index ?? 0;
    if (start > cursor) {
      nodes.push(<React.Fragment key={`${keyPrefix}-text-${index}`}>{text.slice(cursor, start)}</React.Fragment>);
      index += 1;
    }

    const token = match[0];
    if (token.startsWith("**")) {
      nodes.push(
        <strong key={`${keyPrefix}-strong-${index}`} className="chat-message__strong">
          {token.slice(2, -2)}
        </strong>,
      );
    } else {
      nodes.push(
        <mark key={`${keyPrefix}-mark-${index}`} className="chat-message__mark">
          {token.slice(2, -2)}
        </mark>,
      );
    }

    cursor = start + token.length;
    index += 1;
  }

  if (cursor < text.length) {
    nodes.push(<React.Fragment key={`${keyPrefix}-tail-${index}`}>{text.slice(cursor)}</React.Fragment>);
  }

  return nodes;
}

function renderLine(line: string, keyPrefix: string): React.ReactNode {
  return renderInline(line, keyPrefix).map((node, index) => <React.Fragment key={`${keyPrefix}-${index}`}>{node}</React.Fragment>);
}

function renderBlock(block: Block, key: string): React.ReactNode {
  switch (block.type) {
    case "paragraph":
      return (
        <p key={key} className="chat-message__paragraph">
          {block.lines.map((line, lineIndex) => (
            <React.Fragment key={`${key}-line-${lineIndex}`}>
              {renderLine(line, `${key}-line-${lineIndex}`)}
              {lineIndex < block.lines.length - 1 ? <br /> : null}
            </React.Fragment>
          ))}
        </p>
      );
    case "list":
      if (block.ordered) {
        return (
          <ol key={key} className="chat-message__list chat-message__list--ordered">
            {block.items.map((item, index) => (
              <li key={`${key}-item-${index}`}>{renderLine(item, `${key}-item-${index}`)}</li>
            ))}
          </ol>
        );
      }
      return (
        <ul key={key} className="chat-message__list">
          {block.items.map((item, index) => (
            <li key={`${key}-item-${index}`}>{renderLine(item, `${key}-item-${index}`)}</li>
          ))}
        </ul>
      );
    case "table":
      return (
        <div key={key} className="chat-message__table-shell">
          <table className="chat-message__table">
            <thead>
              <tr>
                {block.header.map((cell, index) => (
                  <th key={`${key}-head-${index}`}>{renderLine(cell, `${key}-head-${index}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, rowIndex) => (
                <tr key={`${key}-row-${rowIndex}`}>
                  {row.map((cell, cellIndex) => (
                    <td key={`${key}-row-${rowIndex}-cell-${cellIndex}`}>{renderLine(cell, `${key}-row-${rowIndex}-cell-${cellIndex}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    case "callout":
      return (
        <section key={key} className="chat-message__callout" data-tone={block.tone}>
          <div className="chat-message__callout-title">{block.title}</div>
          <div className="chat-message__callout-body">
            {block.lines.map((line, index) => (
              <p key={`${key}-callout-${index}`} className="chat-message__paragraph">
                {renderLine(line, `${key}-callout-${index}`)}
              </p>
            ))}
          </div>
        </section>
      );
    case "diagram":
      return (
        <section key={key} className="chat-message__diagram-shell">
          <div className="chat-message__diagram-head">
            <span className="chat-message__diagram-label">{block.label}</span>
            <span className="chat-message__diagram-language">{block.language}</span>
          </div>
          <pre className="chat-message__diagram-code">
            <code>{block.value}</code>
          </pre>
        </section>
      );
    case "code":
      return (
        <section key={key} className="chat-message__code-shell">
          {block.language ? <div className="chat-message__code-head">{block.language}</div> : null}
          <pre className="chat-message__code">
            <code>{block.value}</code>
          </pre>
        </section>
      );
    default:
      return null;
  }
}

function roleLabel(message: AgentConversationMessage, copy: ReturnType<typeof useI18n>["copy"]): string {
  if (message.kind === "tool_use") {
    return copy("Tool call", "工具调用");
  }
  if (message.kind === "tool_result") {
    return copy("Tool result", "工具结果");
  }
  if (message.role === "assistant") {
    return copy("Assistant", "Assistant");
  }
  if (message.role === "user") {
    return copy("You", "你");
  }
  if (message.role === "tool") {
    return copy("Tool", "工具");
  }
  return copy("System", "系统");
}

function messageKindLabel(message: AgentConversationMessage, copy: ReturnType<typeof useI18n>["copy"]): string | null {
  if (message.kind === "status") {
    return copy("Run update", "状态更新");
  }
  if (message.kind === "tool_use") {
    return copy("Tool call", "工具调用");
  }
  if (message.kind === "tool_result") {
    return copy("Tool result", "工具结果");
  }
  return null;
}

type TimelineEventKind = "thinking" | "tool_call" | "execution_result" | "human" | "confirmation";

interface TimelineRenderItem {
  id: string;
  messages: AgentConversationMessage[];
  primary: AgentConversationMessage;
  kind: TimelineEventKind;
  toolGroup: boolean;
}

function metadataString(message: AgentConversationMessage, keys: string[]): string | null {
  const metadata = message.metadata ?? {};
  for (const key of keys) {
    const value = metadata[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return null;
}

function metadataObject(message: AgentConversationMessage, keys: string[]): Record<string, unknown> | null {
  const metadata = message.metadata ?? {};
  for (const key of keys) {
    const value = metadata[key];
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return value as Record<string, unknown>;
    }
  }
  return null;
}

function timelinePayloadData(message: AgentConversationMessage): Record<string, unknown> | null {
  const payload = metadataObject(message, ["payload"]);
  const data = payload?.data;
  return data && typeof data === "object" && !Array.isArray(data) ? data as Record<string, unknown> : null;
}

function isToolRelatedTimelineMessage(message: AgentConversationMessage): boolean {
  if (message.kind === "tool_use" || message.kind === "tool_result" || message.role === "tool") {
    return true;
  }
  const semanticHints = [
    metadataString(message, ["traceKind", "itemType", "eventType", "eventKind", "payloadKind"]),
    metadataString(message, ["toolName", "tool_name", "name"]),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  if (/tool|mcp|command_execution|web_search/.test(semanticHints)) {
    return true;
  }
  const data = timelinePayloadData(message);
  const dataKind = String(data?.kind ?? "").toLowerCase();
  const dataToolName = String(data?.tool_name ?? data?.name ?? "").trim();
  return Boolean(dataToolName || /tool|mcp|command_execution|web_search/.test(dataKind));
}

function timelineToolGroupKey(message: AgentConversationMessage): string | null {
  if (!isToolRelatedTimelineMessage(message)) {
    return null;
  }
  const explicitId = metadataString(message, ["toolUseId", "toolCallId", "tool_use_id", "tool_call_id"]);
  const data = timelinePayloadData(message);
  const dataId = typeof data?.id === "string" && data.id.trim()
    ? data.id.trim()
    : typeof data?.tool_use_id === "string" && data.tool_use_id.trim()
      ? data.tool_use_id.trim()
      : typeof data?.tool_call_id === "string" && data.tool_call_id.trim()
        ? data.tool_call_id.trim()
        : null;
  const runId = metadataString(message, ["run_id", "latest_run_id", "runId"]) ?? "run";
  const turnId = metadataString(message, ["turn_id", "turnId"]) ?? "turn";
  const toolName = metadataString(message, ["toolName", "tool_name", "name"])
    ?? (typeof data?.tool_name === "string" && data.tool_name.trim() ? data.tool_name.trim() : null)
    ?? (typeof data?.name === "string" && data.name.trim() ? data.name.trim() : null);
  const stableId = explicitId ?? dataId;
  if (stableId) {
    return `${runId}:${turnId}:${stableId}`;
  }
  if (toolName) {
    return `${runId}:${turnId}:${toolName}`;
  }
  return null;
}

function timelinePayloadKind(message: AgentConversationMessage): string {
  return metadataString(message, ["payloadKind", "traceKind", "eventKind", "eventType", "itemType"])
    ?? String(timelinePayloadData(message)?.kind ?? "");
}

function buildTimelineRenderItems(messages: AgentConversationMessage[]): TimelineRenderItem[] {
  const items: TimelineRenderItem[] = [];
  const toolGroups = new Map<string, TimelineRenderItem>();

  messages.forEach((message) => {
    const toolGroupKey = timelineToolGroupKey(message);
    if (!toolGroupKey) {
      items.push({
        id: message.id,
        messages: [message],
        primary: message,
        kind: resolveTimelineEventKind(message),
        toolGroup: false,
      });
      return;
    }

    const existing = toolGroups.get(toolGroupKey);
    if (existing) {
      existing.messages.push(message);
      existing.primary = message;
      existing.kind = resolveToolGroupEventKind(existing.messages);
      return;
    }

    const item: TimelineRenderItem = {
      id: `tool:${toolGroupKey}`,
      messages: [message],
      primary: message,
      kind: resolveToolGroupEventKind([message]),
      toolGroup: true,
    };
    toolGroups.set(toolGroupKey, item);
    items.push(item);
  });

  return items;
}

function resolveToolGroupEventKind(messages: AgentConversationMessage[]): TimelineEventKind {
  if (messages.some((message) => {
    const kind = timelinePayloadKind(message).toLowerCase();
    return kind.includes("error") || metadataString(message, ["isError"]) === "true";
  })) {
    return "execution_result";
  }
  if (messages.some((message) => {
    const kind = timelinePayloadKind(message).toLowerCase();
    return kind.includes("result") || kind.includes("completed");
  })) {
    return "execution_result";
  }
  return "tool_call";
}

function compactValue(value: unknown): string | null {
  if (value == null) {
    return null;
  }
  if (typeof value === "string") {
    return value.trim() || null;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    const values = value.map(compactValue).filter((item): item is string => Boolean(item));
    return values.length ? values.slice(0, 3).join(", ") : null;
  }
  if (typeof value === "object") {
    return null;
  }
  return String(value);
}

function timelineMetadataPairs(message: AgentConversationMessage): Array<{ key: string; value: string }> {
  const metadata = message.metadata ?? {};
  const hiddenKeys = new Set([
    "eventKind",
    "eventType",
    "itemType",
    "presentationKind",
    "uiKind",
    "traceKind",
    "displayLabel",
    "eventLabel",
    "label",
    "uiLabel",
    "message_type",
    "latest_run_id",
    "run_id",
    "turn_id",
    "seq",
    "priority",
    "lane",
    "requested_by",
    "constraints",
    "turn_metadata",
    "payload",
    "summary",
    "title",
    "content",
    "message",
    "delta",
    "toolName",
    "tool_name",
    "toolUseId",
    "toolCallId",
    "payloadKind",
    "isError",
  ]);

  return Object.entries(metadata)
    .filter(([key]) => !hiddenKeys.has(key))
    .map(([key, value]) => ({ key, value: compactValue(value) }))
    .filter((item): item is { key: string; value: string } => Boolean(item.value))
    .slice(0, 4);
}

function timelineKindFromLifecycle(message: AgentConversationMessage): TimelineEventKind {
  const lifecycle = [
    metadataString(message, ["status", "runStatus", "turnStatus", "state"]),
    message.status,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (/approval|confirm|permission|waiting_human|blocked|timeout/.test(lifecycle)) {
    return "confirmation";
  }
  if (/completed|failed|cancelled|interrupted|sent/.test(lifecycle)) {
    return "execution_result";
  }
  return "thinking";
}

function resolveTimelineEventKind(message: AgentConversationMessage): TimelineEventKind {
  /*
   * Timeline rendering follows protocol/runtime item semantics first
   * (`eventKind`, `itemType`, `traceKind`), mirroring Claude Code/Codex-style
   * adapters. The management timeline intentionally does not infer execution
   * semantics from the older card-view `message.kind` field.
   */
  const explicitKind = metadataString(message, ["uiKind", "presentationKind", "eventKind", "eventType", "itemType"]);
  if (explicitKind) {
    const normalizedKind = explicitKind.toLowerCase();
    if (/approval|confirm|permission|human/.test(normalizedKind)) {
      return "confirmation";
    }
    if (/tool[_\s-]?use|tool[_\s-]?call|mcp_tool_call|command_execution|web_search/.test(normalizedKind)) {
      return "tool_call";
    }
    if (/tool[_\s-]?result|result|completed|execution|file_change/.test(normalizedKind)) {
      return "execution_result";
    }
    if (/status|run_update|state/.test(normalizedKind)) {
      return timelineKindFromLifecycle(message);
    }
    if (/reasoning|thinking/.test(normalizedKind)) {
      return "thinking";
    }
  }

  const traceKind = metadataString(message, ["traceKind"]);
  if (traceKind) {
    const normalizedTraceKind = traceKind.toLowerCase();
    if (/approval|confirm|permission|human/.test(normalizedTraceKind)) {
      return "confirmation";
    }
    if (/tool[_\s-]?use|tool[_\s-]?call|mcp_tool_call|command_execution|web_search/.test(normalizedTraceKind)) {
      return "tool_call";
    }
    if (/tool[_\s-]?result|result|completed|execution|file_change/.test(normalizedTraceKind)) {
      return "execution_result";
    }
    if (/status|run_update|state|queued|started|running|blocked|failed|cancelled/.test(normalizedTraceKind)) {
      return timelineKindFromLifecycle(message);
    }
    if (/reasoning|thinking/.test(normalizedTraceKind)) {
      return "thinking";
    }
  }
  return timelineKindFromLifecycle(message);
}

function timelineLabel(message: AgentConversationMessage, copy: ReturnType<typeof useI18n>["copy"]): string {
  const explicitLabel = metadataString(message, ["uiLabel", "displayLabel", "eventLabel", "label"]);
  if (explicitLabel) {
    return explicitLabel;
  }
  switch (resolveTimelineEventKind(message)) {
    case "tool_call":
      return copy("Tool Call", "工具调用");
    case "execution_result":
      return isToolRelatedTimelineMessage(message) ? copy("Tool Result", "工具结果") : copy("Run Result", "运行结果");
    case "confirmation":
      return copy("Needs Confirmation", "需要确认");
    case "human":
      return copy("Human Instruction", "人工指令");
    case "thinking":
      return copy("Thinking", "思考中");
  }
}

function timelineSummary(message: AgentConversationMessage, copy: ReturnType<typeof useI18n>["copy"]): string {
  const metadataTitle = metadataString(message, ["toolName", "tool_name", "name", "title", "summary"]);
  if (message.title || metadataTitle) {
    return message.title || metadataTitle || "";
  }
  switch (resolveTimelineEventKind(message)) {
    case "tool_call":
      return copy("Calling connected tool", "调用已连接工具");
    case "execution_result":
      return isToolRelatedTimelineMessage(message)
        ? copy("Connected tool returned result", "已连接工具返回结果")
        : copy("Agent returned business output", "Agent 返回业务产出");
    case "confirmation":
      return copy("Waiting for human decision", "等待人工决策");
    default:
      return timelineLabel(message, copy);
  }
}

function firstContentLine(content: string): string | null {
  return content
    .split(/\n+/)
    .map((line) => line.trim())
    .find((line) => line.length > 0) ?? null;
}

function normalizedText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function compactRunResultLines(content: string, title: string | null): string[] {
  const titleText = title ? normalizedText(title) : "";
  const lines = content
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  if (titleText && lines.length && normalizedText(lines[0]) === titleText) {
    return lines.slice(1);
  }
  return lines;
}

function formatTimelineTime(value: string): string {
  const numericValue = /^\d+$/.test(value.trim()) ? Number(value.trim()) : null;
  const date = numericValue == null
    ? new Date(value)
    : new Date(numericValue > 1_000_000_000_000 ? numericValue : numericValue * 1000);
  if (Number.isNaN(date.getTime())) {
    return formatDateTime(value);
  }
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function renderTimelinePayload(message: AgentConversationMessage, blocks: Block[], copy: ReturnType<typeof useI18n>["copy"]): React.ReactNode {
  const eventKind = resolveTimelineEventKind(message);
  const isToolRelated = isToolRelatedTimelineMessage(message);
  const isRunResult = eventKind === "execution_result" && !isToolRelated;
  const metadataPairs = timelineMetadataPairs(message);
  const toolName = metadataString(message, ["toolName", "tool_name", "name"]);
  const contentLine = firstContentLine(message.content);
  const payloadTitle = eventKind === "execution_result" && !isRunResult
    ? contentLine || toolName || message.title || timelineSummary(message, copy)
    : message.title || toolName || contentLine || timelineSummary(message, copy);
  const shouldRenderBody = Boolean(
    message.content && !(eventKind === "execution_result" && contentLine && normalizedText(message.content) === normalizedText(contentLine)),
  );
  const payloadHint =
    eventKind === "tool_call"
      ? copy("Parameters", "参数")
      : isRunResult
        ? copy("Business output", "业务产出")
      : eventKind === "confirmation"
        ? copy("Human-in-the-loop", "Human-in-the-loop")
        : null;

  if (eventKind === "thinking" || eventKind === "human") {
    return (
      <div className="agent-execution-event__plain">
        {message.content
          ? blocks.map((block, index) => renderBlock(block, `${message.id}-timeline-${index}`))
          : message.status === "streaming"
            ? copy("Assistant is responding…", "Assistant 正在输出…")
            : timelineSummary(message, copy)}
        {message.metadata?.payload ? (
          <details className="agent-execution-payload__details">
            <summary>{copy("Show event details", "查看事件细节")}</summary>
            <div className="agent-execution-payload__details-body">
              <pre className="agent-execution-payload__raw">{JSON.stringify(message.metadata.payload, null, 2)}</pre>
            </div>
          </details>
        ) : null}
      </div>
    );
  }

  return (
    <div className="agent-execution-payload">
      <div className="agent-execution-payload__head">
        <span className="agent-execution-payload__icon" aria-hidden="true" />
        <div>
          <strong>{payloadTitle}</strong>
          {payloadHint ? <span>{payloadHint}</span> : null}
        </div>
      </div>
      {metadataPairs.length ? (
        <div className="agent-execution-payload__chips">
          {metadataPairs.map((item) => (
            <span key={`${message.id}-${item.key}`}>
              {item.key}: {item.value}
            </span>
          ))}
        </div>
      ) : null}
      {shouldRenderBody && isRunResult ? (
        <div className="agent-execution-payload__body agent-execution-payload__body--compact">
          {compactRunResultLines(message.content, payloadTitle).slice(0, 8).map((line, index) => (
            <p className="agent-execution-payload__summary-line" key={`${message.id}-summary-${index}`}>{line}</p>
          ))}
          {compactRunResultLines(message.content, payloadTitle).length > 8 ? (
            <details className="agent-execution-payload__details">
              <summary>{copy("Show full output", "查看完整输出")}</summary>
              <div className="agent-execution-payload__details-body">
                {blocks.map((block, index) => renderBlock(block, `${message.id}-timeline-full-${index}`))}
              </div>
            </details>
          ) : null}
          {message.metadata?.payload ? (
            <details className="agent-execution-payload__details">
              <summary>{copy("Show event details", "查看事件细节")}</summary>
              <div className="agent-execution-payload__details-body">
                <pre className="agent-execution-payload__raw">{JSON.stringify(message.metadata.payload, null, 2)}</pre>
              </div>
            </details>
          ) : null}
        </div>
      ) : shouldRenderBody ? (
        <div className="agent-execution-payload__body">
          {blocks.map((block, index) => renderBlock(block, `${message.id}-timeline-${index}`))}
          {message.metadata?.payload ? (
            <details className="agent-execution-payload__details">
              <summary>{copy("Show event details", "查看事件细节")}</summary>
              <div className="agent-execution-payload__details-body">
                <pre className="agent-execution-payload__raw">{JSON.stringify(message.metadata.payload, null, 2)}</pre>
              </div>
            </details>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function toolGroupName(messages: AgentConversationMessage[]): string {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    const data = timelinePayloadData(message);
    const name = metadataString(message, ["toolName", "tool_name", "name"])
      ?? (typeof data?.tool_name === "string" && data.tool_name.trim() ? data.tool_name.trim() : null)
      ?? (typeof data?.name === "string" && data.name.trim() ? data.name.trim() : null);
    if (name) {
      return name;
    }
  }
  return "tool";
}

function toolGroupStatus(messages: AgentConversationMessage[], copy: ReturnType<typeof useI18n>["copy"]): { label: string; tone: "running" | "success" | "error" } {
  const hasError = messages.some((message) => {
    const data = timelinePayloadData(message);
    const kind = timelinePayloadKind(message).toLowerCase();
    return kind.includes("error") || data?.is_error === true || metadataString(message, ["isError"]) === "true";
  });
  if (hasError) {
    return { label: copy("Failed", "失败"), tone: "error" };
  }
  const hasResult = messages.some((message) => {
    const kind = timelinePayloadKind(message).toLowerCase();
    return kind.includes("result");
  });
  if (hasResult) {
    return { label: copy("Completed", "已完成"), tone: "success" };
  }
  const hasStarted = messages.some((message) => timelinePayloadKind(message).toLowerCase().includes("started"));
  return { label: hasStarted ? copy("Running", "调用中") : copy("Preparing", "准备中"), tone: "running" };
}

function compactToolText(value: string, maxLength = 220): string {
  const normalized = value
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .join(" ");
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength)}...` : normalized;
}

function toolStageSummary(message: AgentConversationMessage): string | null {
  const data = timelinePayloadData(message);
  const payloadContent = compactValue(data?.content);
  const payloadInput = compactValue(data?.input);
  const payloadDelta = compactValue(data?.delta);
  const body = compactToolText(message.content || payloadContent || payloadInput || payloadDelta || "");
  if (!body) {
    return null;
  }
  return body;
}

function toolGroupInputSummary(messages: AgentConversationMessage[]): string | null {
  const completed = [...messages].reverse().find((message) => {
    const kind = timelinePayloadKind(message).toLowerCase();
    return kind.includes("use_completed") || kind.includes("started");
  });
  const completedData = completed ? timelinePayloadData(completed) : null;
  if (completedData?.input && typeof completedData.input === "object") {
    return compactToolText(JSON.stringify(completedData.input), 260);
  }
  const deltas = messages
    .map((message) => timelinePayloadData(message))
    .map((data) => typeof data?.delta === "string" ? data.delta : "")
    .filter(Boolean)
    .join("")
    .trim();
  return deltas ? compactToolText(deltas, 260) : null;
}

function toolGroupStages(messages: AgentConversationMessage[], copy: ReturnType<typeof useI18n>["copy"]): Array<{ key: string; label: string; detail: string }> {
  const stages: Array<{ key: string; label: string; detail: string }> = [];
  const appendStage = (key: string, label: string, message: AgentConversationMessage | undefined, fallback: string) => {
    if (!message) {
      return;
    }
    stages.push({
      key,
      label,
      detail: key === "prepare" ? fallback : toolStageSummary(message) ?? fallback,
    });
  };

  appendStage(
    "prepare",
    copy("Prepared input", "准备参数"),
    messages.find((message) => {
      const kind = timelinePayloadKind(message).toLowerCase();
      return kind.includes("input_streamed") || kind.includes("use_completed");
    }),
    toolGroupInputSummary(messages) ?? copy("Tool input prepared.", "工具参数已准备。"),
  );
  appendStage(
    "started",
    copy("Called tool", "执行调用"),
    messages.find((message) => timelinePayloadKind(message).toLowerCase().includes("started")),
    copy("Tool call has started.", "工具调用已发起。"),
  );
  appendStage(
    "result",
    toolGroupStatus(messages, copy).tone === "error" ? copy("Returned error", "返回异常") : copy("Returned result", "返回结果"),
    [...messages].reverse().find((message) => {
      const kind = timelinePayloadKind(message).toLowerCase();
      return kind.includes("result") || kind.includes("error");
    }),
    copy("Tool returned.", "工具已返回。"),
  );

  return stages.length ? stages : [{ key: "event", label: copy("Tool activity", "工具活动"), detail: copy("Tool event recorded.", "已记录工具事件。") }];
}

function renderToolGroupPayload(item: TimelineRenderItem, copy: ReturnType<typeof useI18n>["copy"]): React.ReactNode {
  const status = toolGroupStatus(item.messages, copy);
  const name = toolGroupName(item.messages);
  const rawRecordCount = item.messages.length;
  return (
    <div className="agent-tool-call" data-tool-status={status.tone}>
      <div className="agent-tool-call__head">
        <span className="agent-tool-call__icon" aria-hidden="true" />
        <div>
          <strong>{name}</strong>
          <span>{status.label}</span>
        </div>
      </div>
      <div className="agent-tool-call__stages">
        {toolGroupStages(item.messages, copy).map((stage) => (
          <div key={`${item.id}-${stage.key}`} className="agent-tool-call__stage">
            <span>{stage.label}</span>
            <p>{stage.detail}</p>
          </div>
        ))}
      </div>
      <details className="agent-tool-call__raw">
        <summary>{copy("Show raw tool events", "查看原始工具事件")} · {rawRecordCount}</summary>
        <div className="agent-tool-call__raw-body">
          {item.messages.map((message) => (
            <section key={`${item.id}-${message.id}`}>
              <strong>{message.title || timelinePayloadKind(message) || timelineLabel(message, copy)}</strong>
              {message.content ? <pre>{message.content}</pre> : null}
              <pre>{JSON.stringify(message.metadata?.payload ?? message.metadata ?? {}, null, 2)}</pre>
            </section>
          ))}
        </div>
      </details>
    </div>
  );
}

function TimelineNodeIcon({ kind }: { kind: TimelineEventKind }): JSX.Element {
  switch (kind) {
    case "tool_call":
      return (
        <svg viewBox="0 0 18 18" aria-hidden="true">
          <path d="M9 2.7 14.4 5.8v6.4L9 15.3l-5.4-3.1V5.8L9 2.7Z" />
          <path d="M9 8.8 14.2 5.9M9 8.8 3.8 5.9M9 8.8v6" />
        </svg>
      );
    case "execution_result":
      return (
        <svg viewBox="0 0 18 18" aria-hidden="true">
          <path d="m5 9.2 2.6 2.5L13 6.5" />
        </svg>
      );
    case "confirmation":
      return (
        <svg viewBox="0 0 18 18" aria-hidden="true">
          <path d="M9 3.2 15 14H3L9 3.2Z" />
          <path d="M9 7v3.2M9 12.3h.01" />
        </svg>
      );
    case "human":
      return (
        <svg viewBox="0 0 18 18" aria-hidden="true">
          <path d="M9 8.4a2.6 2.6 0 1 0 0-5.2 2.6 2.6 0 0 0 0 5.2Z" />
          <path d="M4.8 14.4c.7-2.1 2-3.1 4.2-3.1s3.5 1 4.2 3.1" />
        </svg>
      );
    case "thinking":
      return (
        <svg viewBox="0 0 18 18" aria-hidden="true">
          <path d="M4.8 9h.01M9 9h.01M13.2 9h.01" />
        </svg>
      );
  }
}

export function ChatMessageStream({ loading, messages, renderTimelineAttachment, variant = "cards" }: ChatMessageStreamProps): JSX.Element {
  const { copy } = useI18n();

  if (loading) {
    return (
      <div className="chat-stream chat-stream--empty">
        <div className="chat-stream__empty-title">{copy("Loading conversation…", "正在加载会话…")}</div>
      </div>
    );
  }

  if (!messages.length) {
    return (
      <div className="chat-stream chat-stream--empty">
        <div className="chat-stream__empty-title">{copy("No messages yet", "还没有消息")}</div>
        <div className="chat-stream__empty-text">
          {copy(
            "Use the composer below to start a new assistant request or automation task.",
            "在下方输入框发起第一条 Assistant 请求或自动化任务。",
          )}
        </div>
      </div>
    );
  }

  if (variant === "timeline") {
    const timelineItems = buildTimelineRenderItems(messages);
    return (
      <div className="agent-execution-timeline">
        {timelineItems.map((item) => {
          const message = item.primary;
          const blocks = contentToBlocks(message.content);
          const eventKind = item.kind;
          const suppressSummary = item.toolGroup || (eventKind === "execution_result" && !isToolRelatedTimelineMessage(message));
          return (
            <article
              key={item.id}
              className="agent-execution-event"
              data-role={message.role}
              data-event-kind={eventKind}
              data-status={message.status}
              data-tool-group={item.toolGroup ? "true" : undefined}
            >
              <div className="agent-execution-event__node">
                <TimelineNodeIcon kind={eventKind} />
              </div>
              <div className="agent-execution-event__body">
                <div className="agent-execution-event__head">
                  <div>
                    <strong>{item.toolGroup ? copy("Tool Call", "工具调用") : timelineLabel(message, copy)}</strong>
                    {suppressSummary ? null : <span>{timelineSummary(message, copy)}</span>}
                  </div>
                  <time>{formatTimelineTime(message.createdAt)}</time>
                </div>
                {item.toolGroup ? renderToolGroupPayload(item, copy) : renderTimelinePayload(message, blocks, copy)}
                {item.messages.map((itemMessage) => renderTimelineAttachment?.(itemMessage) ?? null)}
              </div>
            </article>
          );
        })}
      </div>
    );
  }

  return (
    <div className="chat-stream">
      {messages.map((message) => {
        const blocks = contentToBlocks(message.content);
        const kindLabel = messageKindLabel(message, copy);
        return (
          <article key={message.id} className="chat-message" data-role={message.role} data-kind={message.kind}>
            <div className="chat-message__meta">
              <span className="chat-message__meta-main">
                <span className="chat-message__role-badge">{roleLabel(message, copy)}</span>
                {kindLabel ? <span className="chat-message__meta-kind">{kindLabel}</span> : null}
              </span>
              <span className="chat-message__meta-time">
                {message.status === "streaming" ? copy("Streaming", "流式输出中") : formatDateTime(message.createdAt)}
              </span>
            </div>
            {message.title ? <div className="chat-message__title">{message.title}</div> : null}
            <div className="chat-message__body">
              {message.content
                ? blocks.map((block, index) => renderBlock(block, `${message.id}-${index}`))
                : message.status === "streaming"
                  ? copy("Assistant is responding…", "Assistant 正在输出…")
                  : copy("Waiting for content…", "等待内容返回…")}
            </div>
          </article>
        );
      })}
    </div>
  );
}
