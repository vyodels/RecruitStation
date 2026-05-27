from __future__ import annotations

from dataclasses import dataclass


SCENE_BROWSER_COMPUTER_MIN_LLM_INVOCATIONS = 8


@dataclass(slots=True)
class SceneExecutionLimits:
    token_budget: int | None = None
    max_llm_invocations: int = SCENE_BROWSER_COMPUTER_MIN_LLM_INVOCATIONS
    tool_timeout_seconds: int = 30
    scene_turn_timeout_seconds: int = 360
    min_wakeup_delay_seconds: int = 60
    max_wakeup_delay_seconds: int = 86_400


@dataclass(slots=True)
class TurnLimits:
    max_llm_invocations: int | None = None
    turn_timeout_seconds: int | None = None
    token_budget: int | None = None
    cooldown_seconds: int = 0
