from __future__ import annotations

import time

from scene_pilot.execution_units.runner import ExecutionUnitRunner
from scene_pilot.execution_units.store import ExecutionUnitStore


def test_execution_unit_supports_blocked_and_timeout_statuses() -> None:
    def _blocked_worker(payload: dict[str, object]) -> dict[str, object]:
        return {"status": "blocked_human", "output": {"reason": "approval_required"}}

    def _timeout_worker(payload: dict[str, object]) -> dict[str, object]:
        time.sleep(0.2)
        return {"output": {"done": True}}

    runner = ExecutionUnitRunner(
        store=ExecutionUnitStore(),
        workers={"blocked": _blocked_worker, "timeout": _timeout_worker},
    )

    blocked = runner.create_execution_unit("blocked", {"candidate_id": "c-1"})
    timeout = runner.create_execution_unit("timeout", {"candidate_id": "c-2"}, timeout_seconds=0)
    assert blocked.status in {"queued", "running", "blocked_human"}

    deadline = time.time() + 2
    while runner.wait_unit(blocked.unit_id).status not in {"blocked_human", "failed"} and time.time() < deadline:
        time.sleep(0.02)

    timed = runner.create_execution_unit("timeout", {"candidate_id": "c-3"}, timeout_seconds=0.05)
    deadline = time.time() + 2
    while runner.wait_unit(timed.unit_id).status not in {"timed_out", "succeeded", "failed"} and time.time() < deadline:
        time.sleep(0.02)

    assert runner.unit_result(blocked.unit_id).status == "blocked_human"
    assert runner.unit_result(timed.unit_id).status == "timed_out"
    assert timeout.status in {"queued", "running"}
