from __future__ import annotations

import json
from typing import Any

from scene_pilot.plugins.host import PluginHost
from scene_pilot.runtime.models import GoalRef, Message, Observation
from scene_pilot.runtime.tools import ToolRegistry


def assemble_messages(
    goal: GoalRef,
    observation: Observation,
    *,
    plugin_host: PluginHost | None = None,
    memory_service: Any | None = None,
    tool_registry: ToolRegistry | None = None,
    history_messages: list[Message] | None = None,
    input_message: str | None = None,
) -> list[Message]:
    persona_fragments = plugin_host.collect_persona_fragments() if plugin_host is not None else []
    scope_memory_entries = []
    global_memory_entries = []
    if memory_service is not None and observation.scope_kind and observation.scope_ref:
        try:
            scope_memory_entries = memory_service.read(scope_kind=observation.scope_kind, scope_ref=observation.scope_ref, limit=5)
        except Exception:
            scope_memory_entries = []
    global_scope_ref = str(goal.constraints.get("global_scope_ref") or "").strip()
    if memory_service is not None and global_scope_ref:
        try:
            global_memory_entries = memory_service.read(scope_kind="global", scope_ref=global_scope_ref, limit=5)
        except Exception:
            global_memory_entries = []

    system_parts = [goal.goal_text or goal.title or "Complete the assigned goal."]
    if persona_fragments:
        system_parts.append("\n".join(persona_fragments))
    if tool_registry is not None:
        system_parts.append(f"Available tools: {', '.join(sorted(tool_registry.tools.keys()))}")

    user_payload = {
        "goal_id": goal.goal_id,
        "scope_kind": goal.scope_kind,
        "scope_ref": goal.scope_ref,
        "input_message": input_message,
        "world_snapshot": observation.world_snapshot,
        "recent_events": list(observation.recent_events)[-8:],
        "memory": scope_memory_entries,
        "global_memory": global_memory_entries,
    }
    messages = [Message(role="system", content="\n\n".join(part for part in system_parts if part))]
    if history_messages:
        messages.extend(history_messages)
    messages.append(Message(role="user", content=json.dumps(user_payload, ensure_ascii=False, default=str)))
    return messages
