from __future__ import annotations

import time

from scene_pilot.execution_units.runner import ExecutionUnitRunner
from scene_pilot.execution_units.store import ExecutionUnitStore


def test_execution_unit_runner_returns_intermediate_and_final_states() -> None:
    store = ExecutionUnitStore()

    def _worker(payload: dict[str, object]) -> dict[str, object]:
        time.sleep(0.05)
        return {"output": {"observed": payload["url"]}}

    runner = ExecutionUnitRunner(store=store, workers={"browser": _worker})
    unit = runner.create_execution_unit("browser", {"url": "https://example.com"}, cooldown_seconds=5)

    assert unit.status in {"queued", "running"}

    deadline = time.time() + 2
    while runner.wait_unit(unit.unit_id).status not in {"succeeded", "failed"} and time.time() < deadline:
        time.sleep(0.02)

    result = runner.unit_result(unit.unit_id)
    assert result.status == "succeeded"
    assert result.output == {"observed": "https://example.com"}
    assert result.metadata["cooldown_seconds"] == 5
