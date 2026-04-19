from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from scene_pilot.kernel.act import act
from scene_pilot.kernel.assemble import assemble_messages
from scene_pilot.kernel.deliberate import deliberate
from scene_pilot.kernel.evaluate import evaluate
from scene_pilot.kernel.guard import run_final
from scene_pilot.kernel.sense import sense
from scene_pilot.kernel.update_memory import update_memory
from scene_pilot.plugins.host import PluginHost
from scene_pilot.runtime.limits import RuntimeLimits
from scene_pilot.runtime.models import CancellationToken, GoalRef, Message, Observation, TickOutcome, ToolCall
from scene_pilot.runtime.providers import LLMProvider
from scene_pilot.runtime.tools import ToolRegistry


EventSink = Callable[[str, dict[str, Any]], None]


@dataclass(slots=True)
class AgentKernel:
    provider: LLMProvider
    tool_registry: ToolRegistry
    plugin_host: PluginHost
    memory_service: Any | None = None
    learning_writer: Any | None = None
    limits: RuntimeLimits = field(default_factory=RuntimeLimits)

    def run_tick(
        self,
        goal: GoalRef,
        observation: Observation,
        *,
        memory_service: Any | None = None,
        learning_writer: Any | None = None,
        cancel_token: CancellationToken | None = None,
        event_sink: EventSink | None = None,
    ) -> TickOutcome:
        active_memory = memory_service if memory_service is not None else self.memory_service
        active_learning_writer = learning_writer if learning_writer is not None else self.learning_writer
        sensed = sense(observation, self.plugin_host)
        messages = assemble_messages(
            goal,
            sensed,
            plugin_host=self.plugin_host,
            memory_service=active_memory,
            tool_registry=self.tool_registry,
        )
        deliberation = deliberate(
            provider=self.provider,
            messages=messages,
            tool_registry=self.tool_registry,
            observation=sensed,
            plugin_host=self.plugin_host,
            limits=self.limits,
            cancel_token=cancel_token,
            event_sink=event_sink,
        )
        effects = act(deliberation)
        memory_updates = update_memory(
            deliberation,
            active_memory,
            learning_writer=active_learning_writer,
            scope_kind=goal.scope_kind,
            scope_ref=goal.scope_ref,
            agent_profile_id=str(goal.constraints.get("agent_profile_id") or "") or None,
            run_pk=str(goal.constraints.get("run_pk") or "") or None,
            source_kind="autonomous",
        )
        outcome = evaluate(deliberation, effects)
        final_guard = run_final(deliberation.final_content, sensed)
        outcome.metadata.update(
            {
                "assembled_messages": messages,
                "tool_results": deliberation.tool_results,
                "memory_updates": memory_updates,
                "final_guard": final_guard,
                "observation": sensed,
            }
        )
        if not final_guard.allowed:
            outcome.status = "escalate"
            outcome.escalate_reason = final_guard.reason
        return outcome

    def run_turn(
        self,
        *,
        goal: GoalRef,
        observation: Observation,
        history_messages: list[Message],
        input_message: str,
        memory_service: Any | None = None,
        learning_writer: Any | None = None,
        cancel_token: CancellationToken | None = None,
        event_sink: EventSink | None = None,
        seed_tool_calls: list[ToolCall] | None = None,
    ) -> TickOutcome:
        active_memory = memory_service if memory_service is not None else self.memory_service
        sensed = sense(observation, self.plugin_host)
        messages = assemble_messages(
            goal,
            sensed,
            plugin_host=self.plugin_host,
            memory_service=active_memory,
            tool_registry=self.tool_registry,
            history_messages=history_messages,
            input_message=input_message,
        )
        deliberation = deliberate(
            provider=self.provider,
            messages=messages,
            tool_registry=self.tool_registry,
            observation=sensed,
            plugin_host=self.plugin_host,
            limits=self.limits,
            cancel_token=cancel_token,
            event_sink=event_sink,
            confirmation_gate=self._assistant_confirmation_gate,
            seed_tool_calls=seed_tool_calls,
        )
        effects = act(deliberation)
        memory_updates = update_memory(
            deliberation,
            None,
            learning_writer=learning_writer if learning_writer is not None else self.learning_writer,
            scope_kind=str(goal.constraints.get("memory_scope_kind") or "global"),
            scope_ref=str(goal.constraints.get("memory_scope_ref") or goal.scope_ref),
            agent_profile_id=str(goal.constraints.get("agent_profile_id") or "assistant"),
            conversation_pk=str(goal.constraints.get("conversation_pk") or "") or None,
            source_kind="assistant",
        )
        outcome = evaluate(deliberation, effects)
        outcome.metadata.update(
            {
                "assembled_messages": messages,
                "tool_results": deliberation.tool_results,
                "memory_updates": memory_updates,
                "pending_tool_calls": deliberation.metadata.get("pending_tool_calls", []),
                "tool_calls": [call.to_provider_payload() for call in deliberation.tool_calls],
            }
        )
        return outcome

    def _assistant_confirmation_gate(self, tool_name: str, arguments: dict[str, object]) -> bool:
        tool = self.tool_registry.tools.get(tool_name)
        if tool is None:
            return False
        if bool(tool.metadata.get("requires_confirmation")):
            return True
        if tool.external_target:
            return True
        return bool(arguments.get("requires_confirmation"))
