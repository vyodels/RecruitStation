from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from queue import Queue
from threading import Thread
from typing import Any, cast

from sqlalchemy.orm import Session, sessionmaker

from scene_pilot.assistant.conversation import ConversationService
from scene_pilot.assistant.session_store import AssistantSessionStore
from scene_pilot.kernel.kernel import AgentKernel
from scene_pilot.memory.service import MemoryService
from scene_pilot.runtime.models import CancellationToken, GoalRef, Message, Observation, TickOutcome, ToolCall


@dataclass(slots=True)
class ActiveTurn:
    conversation_id: str
    turn_id: str
    token: CancellationToken
    queue: Queue[tuple[str, dict[str, Any]] | None]
    worker: Thread


@dataclass(slots=True)
class AssistantAgent:
    kernel: AgentKernel
    session_factory: sessionmaker[Session]
    session_store: AssistantSessionStore
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

        recovery_turn = self.session_store.append_turn(
            conversation_id,
            role="assistant",
            content={},
            status="running",
            turn_metadata={"recovery_of_turn_id": pending_turn.turn_id},
        )
        tool_calls = [ToolCall.from_payload(payload) for payload in list(pending_turn.tool_calls or [])]
        token = CancellationToken()
        events: list[tuple[str, dict[str, Any]]] = []
        outcome = self._run_shared_kernel_turn(
            conversation_id=conversation_id,
            conversation_pk=conversation.id,
            message="Resume approved action.",
            cancel_token=token,
            event_sink=lambda event, data: events.append((event, data)),
            seed_tool_calls=tool_calls,
        )
        tool_results = outcome.metadata.get("tool_results", [])
        status = "completed"
        if outcome.status == "wait_human":
            status = "waiting_human"
        if token.cancelled or outcome.escalate_reason == "cancelled":
            status = "cancelled"
        self.session_store.update_turn(
            recovery_turn.turn_id,
            content={"text": outcome.final_output},
            tool_calls=list(pending_turn.tool_calls or []),
            tool_results=[_serialize_tool_result(item) for item in tool_results],
            status=status,
            cancel_reason=token.reason if status == "cancelled" else None,
            turn_metadata={"recovery_of_turn_id": pending_turn.turn_id, "events": [event for event, _data in events]},
        )
        self.session_store.append_jsonl(
            conversation,
            {
                "role": "assistant",
                "content": outcome.final_output,
                "turn_id": recovery_turn.turn_id,
                "recovery_of_turn_id": pending_turn.turn_id,
            },
        )
        return {
            "conversation_id": conversation_id,
            "confirmed": True,
            "recovery_turn_id": recovery_turn.turn_id,
            "status": status,
            "final_output": outcome.final_output,
        }

    def cancel_turn(self, conversation_id: str) -> dict[str, Any]:
        active = self.active_turns.get(conversation_id)
        if active is None:
            return {"conversation_id": conversation_id, "cancelled": False}
        active.token.cancel("operator_cancelled")
        return {"conversation_id": conversation_id, "cancelled": True, "turn_id": active.turn_id}

    def _execute_turn(
        self,
        conversation_id: str,
        conversation_pk: str,
        user_turn_id: str,
        assistant_turn_id: str,
        message: str,
        token: CancellationToken,
        event_queue: Queue[tuple[str, dict[str, Any]] | None],
    ) -> None:
        def _emit(event: str, payload: dict[str, Any]) -> None:
            event_queue.put((event, payload))

        _emit("turn_started", {"conversation_id": conversation_id, "turn_id": assistant_turn_id})
        try:
            outcome = self._run_shared_kernel_turn(
                conversation_id=conversation_id,
                conversation_pk=conversation_pk,
                message=message,
                cancel_token=token,
                event_sink=_emit,
                exclude_turn_id=user_turn_id,
            )
            tool_results = [_serialize_tool_result(item) for item in outcome.metadata.get("tool_results", [])]
            tool_calls = list(outcome.metadata.get("tool_calls", []) or [])
            status = "completed"
            if outcome.status == "wait_human":
                status = "waiting_human"
            if token.cancelled or outcome.escalate_reason == "cancelled":
                status = "cancelled"
                _emit("turn_cancelled", {"turn_id": assistant_turn_id, "reason": token.reason})
            elif outcome.final_output:
                _emit("llm_final", {"content": outcome.final_output})
            self.session_store.update_turn(
                assistant_turn_id,
                content={"text": outcome.final_output},
                tool_calls=tool_calls,
                tool_results=tool_results,
                status=status,
                cancel_reason=token.reason if status == "cancelled" else None,
            )
            conversation = self.session_store.get_session(conversation_id)
            if conversation is not None:
                self.session_store.append_jsonl(
                    conversation,
                    {
                        "role": "assistant",
                        "content": outcome.final_output,
                        "turn_id": assistant_turn_id,
                        "status": status,
                        "tool_calls": tool_calls,
                    },
                )
            _emit("turn_completed", {"turn_id": assistant_turn_id, "status": status})
        except Exception as exc:
            self.session_store.update_turn(
                assistant_turn_id,
                content={},
                status="failed",
                turn_metadata={"error": str(exc)},
            )
            _emit("turn_failed", {"turn_id": assistant_turn_id, "error": str(exc)})
        finally:
            self.active_turns.pop(conversation_id, None)
            event_queue.put(None)

    def _run_shared_kernel_turn(
        self,
        *,
        conversation_id: str,
        conversation_pk: str,
        message: str,
        cancel_token: CancellationToken,
        event_sink: Any,
        seed_tool_calls: list[ToolCall] | None = None,
        exclude_turn_id: str | None = None,
    ) -> TickOutcome:
        conversation = self.session_store.get_session(conversation_id)
        if conversation is None:
            raise KeyError(f"unknown conversation: {conversation_id}")
        with self.session_factory() as session:
            memory_service = MemoryService(session)
            recent_events = memory_service.fetch_recent_events(conversation_id=conversation_id, limit=8)
            goal = GoalRef(
                goal_id=conversation_id,
                scope_kind="conversation",
                scope_ref=conversation_id,
                goal_text="Respond to the user's request using the shared kernel.",
                constraints={
                    "conversation_pk": conversation_pk,
                    "memory_scope_kind": "global",
                    "memory_scope_ref": conversation.user_id,
                    "agent_profile_id": "assistant",
                },
            )
            observation = Observation(
                world_snapshot={
                    "conversation_id": conversation_id,
                    "assistant_id": conversation.assistant_id,
                    "context_summary": memory_service.fetch_session_summary(conversation_pk),
                },
                scope_kind="conversation",
                scope_ref=conversation_id,
                recent_events=recent_events,
                available_tools=sorted(self.kernel.tool_registry.tools.keys()),
                available_skills=[],
                available_mcps=[],
                hash=conversation_id,
            )
            return self.kernel.run_turn(
                goal=goal,
                observation=observation,
                history_messages=self._history_messages(conversation, exclude_turn_id=exclude_turn_id),
                input_message=message,
                memory_service=memory_service,
                learning_writer=self.kernel.learning_writer,
                cancel_token=cancel_token,
                event_sink=event_sink,
                seed_tool_calls=seed_tool_calls,
            )

    def _history_messages(self, conversation: Any, *, exclude_turn_id: str | None) -> list[Message]:
        messages: list[Message] = []
        for item in self.session_store.load_history(conversation):
            role = str(item.get("role") or "").strip()
            if role not in {"user", "assistant", "tool"}:
                continue
            if exclude_turn_id is not None and item.get("turn_id") == exclude_turn_id:
                continue
            messages.append(Message(role=cast(Any, role), content=str(item.get("content") or "")))
        return messages


def _serialize_tool_result(result: Any) -> dict[str, Any]:
    return {
        "tool_name": result.tool_name,
        "output": result.output,
        "is_error": result.is_error,
        "arguments": dict(result.arguments or {}),
        "metadata": dict(result.metadata or {}),
    }
