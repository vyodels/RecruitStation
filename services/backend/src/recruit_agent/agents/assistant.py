from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
import json
from queue import Queue
from threading import Thread
from typing import Any, cast

from sqlalchemy.orm import Session, sessionmaker

from recruit_agent.agent_runtime.engine import InteractionEngine, InteractionEngineConfig
from recruit_agent.agent_runtime.types import InteractionOutput, LLMMessage, LLMProvider, ToolUse
from recruit_agent.assistant.conversation import ConversationService
from recruit_agent.assistant.session_store import AssistantSessionStore
from recruit_agent.runtime.limits import TurnLimits
from recruit_agent.runtime.models import CancellationToken
from recruit_agent.plugins.host import PluginHost
from recruit_agent.runtime.tools import ToolRegistry


@dataclass(slots=True)
class ActiveTurn:
    conversation_id: str
    turn_id: str
    token: CancellationToken
    queue: Queue[tuple[str, dict[str, Any]] | None]
    worker: Thread


@dataclass(slots=True)
class AssistantAgent:
    provider: LLMProvider
    tool_registry: ToolRegistry
    plugin_host: PluginHost
    session_factory: sessionmaker[Session]
    session_store: AssistantSessionStore
    turn_limits: TurnLimits = field(default_factory=TurnLimits)
    max_history_messages: int | None = None
    active_turns: dict[str, ActiveTurn] = field(default_factory=dict)
    conversations: ConversationService = field(init=False)

    def __post_init__(self) -> None:
        self.conversations = ConversationService(self.session_store)

    def create_conversation(self, *, user_id: str, title: str | None = None) -> Any:
        return self.conversations.create(user_id=user_id, title=title)

    def list_conversations(self, *, user_id: str | None = None) -> list[Any]:
        return self.conversations.list(user_id=user_id)

    def get_conversation(self, conversation_id: str) -> Any:
        return self.conversations.get(conversation_id)

    def delete_conversation(self, conversation_id: str) -> bool:
        return self.session_store.delete_session(conversation_id)

    def run_turn_stream(self, conversation_id: str, message: str) -> Iterator[tuple[str, dict[str, Any]]]:
        conversation = self.session_store.get_session(conversation_id)
        if conversation is None:
            raise KeyError(f"unknown conversation: {conversation_id}")

        user_turn = self.session_store.append_turn(
            conversation_id,
            role="user",
            content={"text": message},
            turn_metadata={"input_kind": "message"},
        )
        self.session_store.append_jsonl(
            conversation,
            {"role": "user", "content": message, "turn_id": user_turn.turn_id},
        )

        assistant_turn = self.session_store.append_turn(
            conversation_id,
            role="assistant",
            content={},
            status="running",
        )
        token = CancellationToken()
        event_queue: Queue[tuple[str, dict[str, Any]] | None] = Queue()
        worker = Thread(
            target=self._execute_turn,
            args=(conversation_id, conversation.id, user_turn.turn_id, assistant_turn.turn_id, message, token, event_queue),
            daemon=True,
        )
        self.active_turns[conversation_id] = ActiveTurn(
            conversation_id=conversation_id,
            turn_id=assistant_turn.turn_id,
            token=token,
            queue=event_queue,
            worker=worker,
        )
        worker.start()
        try:
            while True:
                item = event_queue.get()
                if item is None:
                    break
                yield item
        finally:
            active = self.active_turns.get(conversation_id)
            if active is not None and active.turn_id == assistant_turn.turn_id and active.worker.is_alive():
                active.token.cancel("sse_disconnected")

    def confirm_turn(self, conversation_id: str) -> dict[str, Any]:
        pending_turn = self.session_store.latest_pending_turn(conversation_id)
        if pending_turn is None:
            return {"conversation_id": conversation_id, "confirmed": False}
        conversation = self.session_store.get_session(conversation_id)
        if conversation is None:
            raise KeyError(f"unknown conversation: {conversation_id}")

        token = CancellationToken()
        events: list[tuple[str, dict[str, Any]]] = []
        result = self._run_confirmed_tool_turn(
            conversation_id=conversation_id,
            cancel_token=token,
            event_sink=lambda event, data: events.append((event, data)),
            pending_tool_calls=list(pending_turn.tool_calls or []),
        )
        status = result["status"]
        self.session_store.update_turn(
            pending_turn.turn_id,
            content={"text": result["final_output"] or ""},
            tool_calls=list(pending_turn.tool_calls or []),
            tool_results=list(result["tool_results"]),
            status=status,
            cancel_reason=token.reason if status == "cancelled" else None,
            turn_metadata={"confirmed": True, "events": [event for event, _data in events]},
        )
        self.session_store.append_jsonl(
            conversation,
            {
                "role": "assistant",
                "content": result["final_output"],
                "turn_id": pending_turn.turn_id,
                "confirmed": True,
            },
        )
        return {
            "conversation_id": conversation_id,
            "confirmed": True,
            "turn_id": pending_turn.turn_id,
            "status": status,
            "final_output": result["final_output"],
        }

    def cancel_turn(self, conversation_id: str) -> dict[str, Any]:
        active = self.active_turns.get(conversation_id)
        if active is None:
            return {"conversation_id": conversation_id, "cancelled": False}
        active.token.cancel("operator_cancelled")
        active.queue.put(
            (
                "turn.cancelling",
                {
                    "conversation_id": conversation_id,
                    "turn_id": active.turn_id,
                    "reason": active.token.reason,
                },
            )
        )
        active.worker.join(timeout=0.2)
        return {
            "conversation_id": conversation_id,
            "cancelled": True,
            "turn_id": active.turn_id,
            "active": active.worker.is_alive(),
        }

    def _execute_turn(
        self,
        conversation_id: str,
        conversation_pk: str,
        user_turn_id: str,
        assistant_turn_id: str,
        message: str | None,
        token: CancellationToken,
        event_queue: Queue[tuple[str, dict[str, Any]] | None],
    ) -> None:
        def _emit(event: str, payload: dict[str, Any]) -> None:
            event_queue.put((event, payload))

        _emit("turn.started", {"conversation_id": conversation_id, "turn_id": assistant_turn_id})
        try:
            engine = InteractionEngine(
                InteractionEngineConfig(
                    conversation_id=conversation_id,
                    provider=cast(Any, self.provider),
                    tools=self.tool_registry.to_agent_runtime_tools(),
                    initial_messages=self._runtime_history_messages(conversation_id, exclude_turn_id=user_turn_id),
                    max_llm_invocations=self.turn_limits.max_llm_invocations or 12,
                    max_history_messages=self.max_history_messages,
                )
            )
            final_output = ""
            status = "completed"
            tool_results: list[dict[str, Any]] = []
            tool_calls: list[dict[str, Any]] = []
            for output in engine.submitMessage(message or ""):
                if token.is_cancelled():
                    engine.interrupt()
                for event, payload in _assistant_events_from_output(output):
                    _emit(event, payload)
                if output.type == "assistant_message_completed":
                    final_output = str(output.data.get("message") or "")
                elif output.type == "tool_event":
                    data = dict(output.data)
                    if data.get("kind") == "tool_result_ready":
                        tool_results.append(
                            {
                                "tool_name": data.get("tool_name"),
                                "output": data.get("content"),
                                "is_error": data.get("is_error", False),
                                "metadata": {},
                            }
                        )
                    elif data.get("kind") in {"tool_use_completed", "tool_call_started"}:
                        tool_calls.append(data)
                elif output.type == "turn_interrupted":
                    status = "cancelled"
                elif output.type == "turn_failed":
                    status = "failed"
                elif output.type == "permission_requested":
                    status = "waiting_human"
                    tool_calls = [_permission_tool_call_payload(dict(output.data))]
            self.session_store.update_turn(
                assistant_turn_id,
                content={"text": final_output},
                tool_calls=tool_calls,
                tool_results=tool_results,
                status=status,
                cancel_reason=token.reason if status == "cancelled" else None,
            )
            conversation = self.session_store.get_session(conversation_id)
            if conversation is not None:
                compaction_event = self.session_store.append_jsonl(
                    conversation,
                    {
                        "role": "assistant",
                        "content": final_output,
                        "turn_id": assistant_turn_id,
                        "status": status,
                        "tool_calls": tool_calls,
                    },
                )
                if compaction_event is not None:
                    _emit("compacted", compaction_event)
            if status == "cancelled":
                _emit("turn.cancelled", {"turn_id": assistant_turn_id, "reason": token.reason})
            elif status == "completed":
                _emit("turn.completed", {"turn_id": assistant_turn_id, "status": status})
            elif status == "waiting_human":
                _emit("turn.waiting_human", {"turn_id": assistant_turn_id, "status": status})
            else:
                _emit("turn.failed", {"turn_id": assistant_turn_id, "status": status})
        except Exception as exc:
            self.session_store.update_turn(
                assistant_turn_id,
                content={},
                status="failed",
                turn_metadata={"error": str(exc)},
            )
            _emit("turn.failed", {"turn_id": assistant_turn_id, "error": str(exc)})
        finally:
            self.active_turns.pop(conversation_id, None)
            event_queue.put(None)

    def _run_confirmed_tool_turn(
        self,
        *,
        conversation_id: str,
        cancel_token: CancellationToken,
        event_sink: Any,
        pending_tool_calls: list[dict[str, Any]],
    ) -> dict[str, Any]:
        conversation = self.session_store.get_session(conversation_id)
        if conversation is None:
            raise KeyError(f"unknown conversation: {conversation_id}")
        initial_messages = self._runtime_history_messages(conversation_id, exclude_turn_id=None)
        tool_results: list[dict[str, Any]] = []
        for payload in pending_tool_calls:
            call = _pending_tool_use(payload)
            event_sink("tool_call", {"tool_name": call.name, "tool_use_id": call.id, "input": dict(call.input)})
            result = self.tool_registry.execute(call.name, dict(call.input or {}), cancel_token=cancel_token)
            tool_results.append(
                {
                    "tool_name": result.tool_name,
                    "output": result.output,
                    "is_error": result.is_error,
                    "arguments": dict(result.arguments or {}),
                    "metadata": dict(result.metadata or {}),
                }
            )
            event_sink("tool_result", tool_results[-1])
            initial_messages.append(LLMMessage(role="assistant", content="", tool_uses=[call]))
            initial_messages.append(
                LLMMessage(
                    role="tool",
                    name=call.name,
                    tool_use_id=call.id,
                    content=_json_text(result.output),
                    metadata={"is_error": result.is_error},
                )
            )

        engine = InteractionEngine(
            InteractionEngineConfig(
                conversation_id=conversation_id,
                provider=cast(Any, self.provider),
                tools=self.tool_registry.to_agent_runtime_tools(),
                initial_messages=initial_messages,
                max_llm_invocations=self.turn_limits.max_llm_invocations or 12,
                max_history_messages=self.max_history_messages,
            )
        )
        final_output = ""
        status = "completed"
        for output in engine.submitMessage(""):
            if cancel_token.is_cancelled():
                engine.interrupt()
            for event, payload in _assistant_events_from_output(output):
                event_sink(event, payload)
            if output.type == "assistant_message_completed":
                final_output = str(output.data.get("message") or "")
            elif output.type == "permission_requested":
                status = "waiting_human"
            elif output.type == "turn_interrupted":
                status = "cancelled"
            elif output.type == "turn_failed":
                status = "failed"
        return {"status": status, "final_output": final_output, "tool_results": tool_results}

    def _runtime_history_messages(self, conversation_id: str, *, exclude_turn_id: str | None) -> list[LLMMessage]:
        conversation = self.session_store.get_session(conversation_id)
        if conversation is None:
            return []
        messages: list[LLMMessage] = []
        for item in self.session_store.load_history(conversation):
            role = str(item.get("role") or "").strip()
            if role not in {"system", "user", "assistant", "tool"}:
                continue
            if exclude_turn_id is not None and item.get("turn_id") == exclude_turn_id:
                continue
            messages.append(LLMMessage(role=cast(Any, role), content=str(item.get("content") or "")))
        return messages


def _assistant_events_from_output(output: InteractionOutput) -> list[tuple[str, dict[str, Any]]]:
    base = {
        "conversation_id": output.conversation_id,
        "turn_id": output.turn_id,
        "seq": output.seq,
        **dict(output.data or {}),
    }
    if output.type == "turn_started":
        return [("turn.started", base)]
    if output.type == "assistant_message_delta":
        return [("llm_delta", {"delta": base.get("delta", ""), "seq": output.seq})]
    if output.type == "assistant_message_completed":
        content = base.get("message", "")
        return [
            ("llm_delta", {"delta": content, "seq": output.seq}),
            ("llm_final", {"content": content, "seq": output.seq}),
        ]
    if output.type == "llm_invocation_started":
        return [("provider_started", base)]
    if output.type == "llm_invocation_completed":
        return [("provider_completed", base)]
    if output.type == "tool_event":
        kind = str(base.get("kind") or "tool_event")
        if kind == "tool_call_started":
            return [("tool_call", base)]
        if kind == "tool_result_ready":
            return [("tool_result", base)]
        return [("tool_event", base)]
    if output.type == "permission_requested":
        return [("turn.waiting_human", base)]
    if output.type == "turn_completed":
        return [("turn.completed", base)]
    if output.type == "turn_interrupted":
        return [("turn.cancelled", base)]
    if output.type == "turn_failed":
        return [("turn.failed", base)]
    return [(output.type, base)]


def _permission_tool_call_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(data.get("tool_use_id") or data.get("tool_call_id") or ""),
        "type": "function",
        "function": {
            "name": str(data.get("tool_name") or ""),
            "arguments": json.dumps(dict(data.get("input") or {}), ensure_ascii=False),
        },
    }


def _pending_tool_use(payload: dict[str, Any]) -> ToolUse:
    function = payload.get("function") if isinstance(payload.get("function"), dict) else {}
    arguments = function.get("arguments", {})
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            arguments = {"_raw": arguments}
    return ToolUse(
        id=str(payload.get("id") or payload.get("tool_use_id") or payload.get("tool_call_id") or ""),
        name=str(function.get("name") or payload.get("name") or payload.get("tool_name") or ""),
        input=dict(arguments or payload.get("input") or {}),
        raw=dict(payload),
    )


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
