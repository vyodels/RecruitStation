from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from recruit_agent.repositories import SyncBacklogRepository


SyncTransport = Callable[["SyncBacklogItem"], bool | dict[str, Any]]


@dataclass(slots=True)
class SyncBacklogItem:
    item_id: str
    item_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    protocol_version: str = "2026-04-14"
    target: dict[str, Any] = field(default_factory=dict)
    body: dict[str, Any] = field(default_factory=dict)
    attempt_count: int = 0
    last_error: str | None = None

    @classmethod
    def from_record(cls, record: Any) -> "SyncBacklogItem":
        envelope = dict(record.payload or {})
        delivery = envelope.get("delivery") if isinstance(envelope.get("delivery"), dict) else {}
        return cls(
            item_id=str(record.item_id),
            item_type=str(record.item_type),
            payload=envelope,
            status=str(record.status),
            synced_at=getattr(record, "synced_at", None),
            created_at=getattr(record, "created_at", None),
            updated_at=getattr(record, "updated_at", None),
            protocol_version=str(envelope.get("protocol_version") or "2026-04-14"),
            target=dict(envelope.get("target") or {}),
            body=dict(envelope.get("body") or {}),
            attempt_count=int(delivery.get("attempt_count", 0) or 0),
            last_error=str(delivery.get("last_error")) if delivery.get("last_error") is not None else None,
        )


@dataclass(slots=True)
class SyncFlushResult:
    attempted: int = 0
    synced: int = 0
    failed: int = 0
    pending: int = 0


@dataclass(slots=True)
class SyncStatusSnapshot:
    enabled: bool
    remote_available: bool
    protocol_version: str
    source: str
    target: dict[str, Any] = field(default_factory=dict)
    pending_count: int = 0
    synced_count: int = 0
    failed_delivery_count: int = 0
    backlog_total: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    latest_error: str | None = None


@dataclass(slots=True)
class SyncService:
    intranet_enabled: bool = False
    session_factory: sessionmaker[Session] | None = None
    backlog: list[SyncBacklogItem] = field(default_factory=list)
    target: dict[str, Any] = field(default_factory=dict)
    transport: SyncTransport | None = None
    protocol_version: str = "2026-04-14"
    source: str = "desktop_app"

    def enqueue(self, item_type: str, item_id: str, payload: dict[str, Any]) -> SyncBacklogItem:
        envelope = self._build_envelope(item_type=item_type, item_id=item_id, body=payload)
        if self.session_factory is None:
            now = datetime.now(timezone.utc)
            item = SyncBacklogItem(
                item_id=item_id,
                item_type=item_type,
                payload=envelope,
                protocol_version=self.protocol_version,
                target=dict(self.target),
                body=dict(payload),
                created_at=now,
                updated_at=now,
            )
            self.backlog.append(item)
            return item

        with self.session_factory() as session:
            record = SyncBacklogRepository(session).enqueue(item_type=item_type, item_id=item_id, payload=envelope)
            return SyncBacklogItem.from_record(record)

    def pending(self, limit: int = 100, offset: int = 0) -> list[SyncBacklogItem]:
        return self.list_backlog(status="pending", limit=limit, offset=offset)

    def list_backlog(
        self,
        *,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SyncBacklogItem]:
        if self.session_factory is None:
            items = list(self.backlog)
            if status is not None:
                items = [item for item in items if item.status == status]
            items.sort(
                key=lambda item: (
                    item.created_at or datetime.min.replace(tzinfo=timezone.utc),
                    item.item_id,
                ),
                reverse=True,
            )
            return items[offset : offset + limit]

        with self.session_factory() as session:
            records = SyncBacklogRepository(session).list(status=status, limit=limit, offset=offset)
            return [SyncBacklogItem.from_record(record) for record in records]

    def pending_count(self) -> int:
        if self.session_factory is None:
            return sum(1 for item in self.backlog if item.status == "pending")

        with self.session_factory() as session:
            return SyncBacklogRepository(session).pending_count()

    def status_snapshot(self) -> SyncStatusSnapshot:
        if self.session_factory is None:
            by_status: dict[str, int] = {}
            latest_error: str | None = None
            failed_delivery_count = 0
            for item in self.backlog:
                by_status[item.status] = by_status.get(item.status, 0) + 1
                if item.last_error:
                    failed_delivery_count += 1
                    latest_error = item.last_error
            return SyncStatusSnapshot(
                enabled=bool(self.intranet_enabled),
                remote_available=self.remote_available(),
                protocol_version=self.protocol_version,
                source=self.source,
                target=dict(self.target),
                pending_count=by_status.get("pending", 0),
                synced_count=by_status.get("synced", 0),
                failed_delivery_count=failed_delivery_count,
                backlog_total=len(self.backlog),
                by_status=by_status,
                latest_error=latest_error,
            )

        with self.session_factory() as session:
            repo = SyncBacklogRepository(session)
            by_status = repo.counts_by_status()
            return SyncStatusSnapshot(
                enabled=bool(self.intranet_enabled),
                remote_available=self.remote_available(),
                protocol_version=self.protocol_version,
                source=self.source,
                target=dict(self.target),
                pending_count=by_status.get("pending", 0),
                synced_count=by_status.get("synced", 0),
                failed_delivery_count=repo.delivery_error_count(),
                backlog_total=sum(by_status.values()),
                by_status=by_status,
                latest_error=repo.latest_delivery_error(),
            )

    def mark_synced(self, item_id: str, item_type: str | None = None) -> SyncBacklogItem | None:
        if self.session_factory is None:
            for item in self.backlog:
                if item.item_id == item_id and (item_type is None or item.item_type == item_type):
                    item.status = "synced"
                    item.synced_at = datetime.now(timezone.utc)
                    item.updated_at = item.synced_at
                    return item
            return None

        with self.session_factory() as session:
            record = SyncBacklogRepository(session).mark_synced(item_id=item_id, item_type=item_type)
            return SyncBacklogItem.from_record(record) if record is not None else None

    def remote_available(self) -> bool:
        return bool(self.intranet_enabled and self.transport is not None and self.target.get("base_url"))

    def flush_pending(self, limit: int = 100) -> SyncFlushResult:
        pending_items = self.pending(limit=limit)
        if not self.remote_available():
            return SyncFlushResult(
                attempted=0,
                synced=0,
                failed=0,
                pending=len(pending_items),
            )

        result = SyncFlushResult()
        for item in pending_items:
            result.attempted += 1
            try:
                response = self.transport(item) if self.transport is not None else False
                if self._is_successful_response(response):
                    self.mark_synced(item.item_id, item_type=item.item_type)
                    result.synced += 1
                    continue
                error = self._extract_response_error(response)
            except Exception as exc:  # pragma: no cover - defensive guard
                error = str(exc)

            self._mark_delivery_failure(item, error)
            result.failed += 1

        result.pending = self.pending_count()
        return result

    def _build_envelope(self, *, item_type: str, item_id: str, body: dict[str, Any]) -> dict[str, Any]:
        queued_at = datetime.now(timezone.utc).isoformat()
        return {
            "protocol_version": self.protocol_version,
            "source": self.source,
            "target": dict(self.target),
            "item": {
                "type": item_type,
                "id": item_id,
            },
            "body": dict(body),
            "delivery": {
                "mode": "local_first",
                "attempt_count": 0,
                "last_error": None,
                "queued_at": queued_at,
                "last_attempt_at": None,
            },
        }

    def _mark_delivery_failure(self, item: SyncBacklogItem, error: str | None) -> None:
        attempt_count = item.attempt_count + 1
        payload = dict(item.payload)
        delivery = payload.get("delivery") if isinstance(payload.get("delivery"), dict) else {}
        delivery.update(
            {
                "mode": "local_first",
                "attempt_count": attempt_count,
                "last_error": error,
                "last_attempt_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        payload["delivery"] = delivery

        if self.session_factory is None:
            for backlog_item in self.backlog:
                if backlog_item.item_id == item.item_id and backlog_item.item_type == item.item_type:
                    backlog_item.payload = payload
                    backlog_item.attempt_count = attempt_count
                    backlog_item.last_error = error
                    backlog_item.updated_at = datetime.now(timezone.utc)
                    break
            return

        with self.session_factory() as session:
            SyncBacklogRepository(session).update_payload(item.item_id, item.item_type, payload)

    def _is_successful_response(self, response: bool | dict[str, Any]) -> bool:
        if isinstance(response, bool):
            return response
        if isinstance(response, dict):
            if "success" in response:
                return bool(response["success"])
            if "status" in response:
                return str(response["status"]).lower() in {"ok", "success", "synced"}
        return False

    def _extract_response_error(self, response: bool | dict[str, Any]) -> str | None:
        if isinstance(response, dict):
            for key in ("error", "detail", "message"):
                value = response.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return "Remote sync did not acknowledge the payload."
