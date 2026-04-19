from __future__ import annotations

from scene_pilot.runtime.models import Deliberation, Effects, TickOutcome


def evaluate(deliberation: Deliberation, effects: Effects) -> TickOutcome:
    if deliberation.metadata.get("cancelled"):
        status = "escalate"
        return TickOutcome(
            status=status,
            final_output=deliberation.final_content,
            effects=effects,
            escalate_reason="cancelled",
            metadata={"stop_reason": deliberation.stop_reason},
        )
    if deliberation.stop_reason == "wait_human" or deliberation.metadata.get("pending_tool_calls"):
        return TickOutcome(
            status="wait_human",
            final_output=deliberation.final_content,
            effects=effects,
            wait_reason="pending_confirmation",
            metadata={"stop_reason": deliberation.stop_reason},
        )
    status = "complete" if deliberation.final_content else "continue"
    return TickOutcome(
        status=status,
        final_output=deliberation.final_content,
        effects=effects,
        metadata={"stop_reason": deliberation.stop_reason},
    )
