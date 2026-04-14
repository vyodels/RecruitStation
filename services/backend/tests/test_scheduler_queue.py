from __future__ import annotations

import sys
import tempfile
from datetime import timedelta
from pathlib import Path
import unittest


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from recruit_agent.core.settings import AppSettings
from recruit_agent.db.session import create_engine_from_settings, create_session_factory, initialize_database
from recruit_agent.scheduler.queue import InMemoryQueue, SqlAlchemyQueue, TaskEnvelope
from recruit_agent.services.sync import SyncService


class QueueTests(unittest.TestCase):
    def test_priority_ordering(self) -> None:
        queue = InMemoryQueue()
        queue.put(TaskEnvelope(task_id="low", task_type="screen", priority=1))
        queue.put(TaskEnvelope(task_id="high", task_type="screen", priority=10))
        queue.put(TaskEnvelope(task_id="mid", task_type="screen", priority=5))

        self.assertEqual(queue.peek().task_id, "high")
        self.assertEqual(queue.get().task_id, "high")
        self.assertEqual(queue.get().task_id, "mid")
        self.assertEqual(queue.get().task_id, "low")
        self.assertTrue(queue.empty())

    def test_sqlalchemy_queue_persists_priority_order(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            settings = AppSettings(
                data_dir=tempdir,
                database_url="sqlite:///./queue-test.db",
            )
            engine = create_engine_from_settings(settings)
            initialize_database(engine)
            session_factory = create_session_factory(engine)
            queue = SqlAlchemyQueue(session_factory)

            queue.put(TaskEnvelope(task_id="low", task_type="screen", priority=1, candidate_id="cand-low"))
            queue.put(TaskEnvelope(task_id="high", task_type="screen", priority=10, candidate_id="cand-high"))

            self.assertEqual(queue.size(), 2)
            self.assertEqual(queue.peek().task_id, "high")

            claimed = queue.get()
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed.task_id, "high")
            self.assertEqual(claimed.candidate_id, "cand-high")
            self.assertEqual(queue.size(), 1)

            queue.mark_complete(claimed.task_id)
            self.assertEqual(queue.get().task_id, "low")

    def test_sync_service_uses_persistent_backlog_when_session_factory_present(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            settings = AppSettings(
                data_dir=tempdir,
                database_url="sqlite:///./sync-test.db",
            )
            engine = create_engine_from_settings(settings)
            initialize_database(engine)
            session_factory = create_session_factory(engine)
            sync = SyncService(intranet_enabled=True, session_factory=session_factory)

            item = sync.enqueue("candidate", "cand-001", {"status": "passed"})
            self.assertEqual(item.item_id, "cand-001")
            self.assertEqual(sync.pending_count(), 1)
            pending_item = sync.pending()[0]
            self.assertEqual(pending_item.body["status"], "passed")
            self.assertEqual(pending_item.payload["delivery"]["mode"], "local_first")

            sync.mark_synced("cand-001", item_type="candidate")
            self.assertEqual(sync.pending_count(), 0)

    def test_sqlalchemy_queue_recovers_stale_running_task(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            settings = AppSettings(
                data_dir=tempdir,
                database_url="sqlite:///./queue-recovery.db",
            )
            engine = create_engine_from_settings(settings)
            initialize_database(engine)
            session_factory = create_session_factory(engine)
            queue = SqlAlchemyQueue(session_factory, stale_after=timedelta(seconds=0))

            queue.put(TaskEnvelope(task_id="recover-me", task_type="screen", priority=5))
            claimed = queue.get()

            self.assertIsNotNone(claimed)
            self.assertEqual(queue.size(), 0)
            self.assertEqual(queue.recover_stale(), 1)
            self.assertEqual(queue.size(), 1)
            self.assertEqual(queue.get().task_id, "recover-me")

    def test_sync_service_keeps_backlog_pending_without_remote_target(self) -> None:
        sync = SyncService(intranet_enabled=True)
        sync.enqueue("candidate", "cand-002", {"status": "pending"})

        result = sync.flush_pending()

        self.assertEqual(result.attempted, 0)
        self.assertEqual(result.synced, 0)
        self.assertEqual(result.pending, 1)

    def test_sync_service_flushes_when_transport_available(self) -> None:
        sync = SyncService(
            intranet_enabled=True,
            target={"kind": "intranet", "base_url": "http://intranet.example"},
            transport=lambda item: {"success": True, "item_id": item.item_id},
        )
        sync.enqueue("candidate", "cand-003", {"status": "ready"})

        result = sync.flush_pending()

        self.assertEqual(result.attempted, 1)
        self.assertEqual(result.synced, 1)
        self.assertEqual(sync.pending_count(), 0)

    def test_sync_service_records_failed_delivery_attempt(self) -> None:
        sync = SyncService(
            intranet_enabled=True,
            target={"kind": "intranet", "base_url": "http://intranet.example"},
            transport=lambda item: {"success": False, "error": f"failed:{item.item_id}"},
        )
        sync.enqueue("candidate", "cand-004", {"status": "ready"})

        result = sync.flush_pending()

        self.assertEqual(result.attempted, 1)
        self.assertEqual(result.failed, 1)
        pending_item = sync.pending()[0]
        self.assertEqual(pending_item.attempt_count, 1)
        self.assertEqual(pending_item.last_error, "failed:cand-004")


if __name__ == "__main__":
    unittest.main()
