from __future__ import annotations

import time
from threading import Event

from scene_pilot.execution_units.runner import ExecutionUnitRunner
from scene_pilot.execution_units.store import ExecutionUnitStore


def test_functional_closure_execution_units_have_intermediate_states() -> None:
    blocker = Event()

    def _worker(payload: dict[str, object]) -> dict[str, object]:
        blocker.wait(timeout=1)
        return {"output": {"ok": True}}

    runner = ExecutionUnitRunner(store=ExecutionUnitStore(), workers={"browser": _worker})
    unit = runner.create_execution_unit("browser", {"url": "https://example.com"})
    assert runner.wait_unit(unit.unit_id).status in {"queued", "running"}
    blocker.set()
    deadline = time.time() + 2
    while runner.wait_unit(unit.unit_id).status != "succeeded" and time.time() < deadline:
        time.sleep(0.02)
    assert runner.unit_result(unit.unit_id).status == "succeeded"
