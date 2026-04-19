from __future__ import annotations

import time
from threading import Event

from scene_pilot.execution_units.runner import ExecutionUnitRunner
from scene_pilot.execution_units.store import ExecutionUnitStore


def test_execution_unit_wait_is_nonblocking_for_inflight_work() -> None:
    blocker = Event()

    def _worker(payload: dict[str, object]) -> dict[str, object]:
        blocker.wait(timeout=1)
        return {"output": {"payload": payload}}

    runner = ExecutionUnitRunner(store=ExecutionUnitStore(), workers={"browser": _worker})
    unit = runner.create_execution_unit("browser", {"url": "https://example.com"})

    snapshot = runner.wait_unit(unit.unit_id)
    assert snapshot.status in {"queued", "running"}

    blocker.set()
    deadline = time.time() + 2
    while runner.wait_unit(unit.unit_id).status != "succeeded" and time.time() < deadline:
        time.sleep(0.02)

    assert runner.unit_result(unit.unit_id).status == "succeeded"
