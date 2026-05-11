from __future__ import annotations

from dataclasses import dataclass, field

from .types import LLMMessage


@dataclass(slots=True)
class ConversationHistory:
    messages: list[LLMMessage] = field(default_factory=list)

    def append(self, messages: list[LLMMessage]) -> None:
        self.messages.extend(messages)

    def snapshot(self) -> list[LLMMessage]:
        return list(self.messages)

    def replace(self, messages: list[LLMMessage]) -> None:
        self.messages = list(messages)

    def compact(self, *, max_messages: int, summary_max_chars: int = 2000) -> list[LLMMessage] | None:
        if max_messages < 2 or len(self.messages) <= max_messages:
            return None

        prefix: list[LLMMessage] = []
        compactable = list(self.messages)
        while compactable and compactable[0].role == "system" and compactable[0].metadata.get("kind") != "context_compaction_summary":
            prefix.append(compactable.pop(0))

        recent_count = max(1, max_messages - len(prefix) - 1)
        if len(compactable) <= recent_count:
            return None

        recent_start = max(0, len(compactable) - recent_count)
        recent_start = _include_tool_context(compactable, recent_start)
        old_messages = compactable[:recent_start]
        recent_messages = compactable[recent_start:]
        if not old_messages:
            return None

        summary = _summarize_messages(old_messages, max_chars=summary_max_chars)
        summary_message = LLMMessage(
            role="system",
            content=f"Conversation history compacted. Earlier messages summary:\n{summary}",
            metadata={
                "kind": "context_compaction_summary",
                "compacted_message_count": len(old_messages),
            },
        )
        compacted = [*prefix, summary_message, *recent_messages]
        self.replace(compacted)
        return compacted


def _include_tool_context(messages: list[LLMMessage], recent_start: int) -> int:
    while recent_start > 0 and messages[recent_start].role == "tool":
        tool_use_id = messages[recent_start].tool_use_id
        assistant_index = recent_start - 1
        while assistant_index >= 0:
            candidate = messages[assistant_index]
            if candidate.role == "assistant" and any(tool_use.id == tool_use_id for tool_use in candidate.tool_uses):
                recent_start = assistant_index
                break
            assistant_index -= 1
        else:
            break
    return recent_start


def _summarize_messages(messages: list[LLMMessage], *, max_chars: int) -> str:
    parts: list[str] = []
    for message in messages:
        text = _message_text(message).strip()
        if not text and message.tool_uses:
            text = ", ".join(tool_use.name for tool_use in message.tool_uses)
        if not text:
            continue
        parts.append(f"- {message.role}: {_clip(text, 240)}")
    summary = "\n".join(parts) or "- Earlier messages were compacted."
    return _clip(summary, max_chars)


def _message_text(message: LLMMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    parts: list[str] = []
    for block in message.content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
    return "".join(parts)


def _clip(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)].rstrip() + "..."
