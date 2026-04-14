from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from recruit_agent.services.agent import AgentControlService
from recruit_agent.services.events import EventStreamService


@dataclass(slots=True)
class AutonomyLoopService:
    agent_control: AgentControlService
    events: EventStreamService
    enabled: bool = False
    idle_poll_interval: float = 0.5
    active_poll_interval: float = 0.05
    _task: asyncio.Task[None] | None = field(default=None, init=False, repr=False)
    _stop_event: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False)

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if not self.enabled or self.is_running():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="recruit-agent-autonomy-loop")
        self.events.publish("info", "autonomy", "Autonomy loop started.")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        task = self._task
        self._task = None
        await task
        self.events.publish("info", "autonomy", "Autonomy loop stopped.")

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                outcome = self.agent_control.run_once()
            except Exception as exc:  # pragma: no cover - defensive guard
                self.events.publish("error", "autonomy", "Autonomy loop iteration failed.", error=str(exc))
                outcome = None

            interval = self.active_poll_interval if outcome is not None else self.idle_poll_interval
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue
