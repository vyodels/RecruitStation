from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from scene_pilot.models.domain import PromptOverlayRevision


class PromptEvolution:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def create_revision(self, *, job_description_id: str, content: dict[str, object]) -> PromptOverlayRevision:
        with self.session_factory() as session:
            next_version = int(
                session.scalar(
                    select(func.max(PromptOverlayRevision.version)).where(
                        PromptOverlayRevision.job_description_id == job_description_id
                    )
                )
                or 0
            ) + 1
            revision = PromptOverlayRevision(
                job_description_id=job_description_id,
                version=next_version,
                content=dict(content),
                status="trial",
            )
            session.add(revision)
            session.commit()
            session.refresh(revision)
            return revision

    def record_trial_metrics(
        self,
        revision_id: str,
        *,
        success: bool,
        latency_ms: int | None = None,
    ) -> PromptOverlayRevision:
        with self.session_factory() as session:
            revision = session.get(PromptOverlayRevision, revision_id)
            if revision is None:
                raise KeyError(f"unknown prompt revision: {revision_id}")
            metrics = dict(revision.trial_metrics or {})
            metrics["runs"] = int(metrics.get("runs") or 0) + 1
            if success:
                metrics["successes"] = int(metrics.get("successes") or 0) + 1
            else:
                metrics["failures"] = int(metrics.get("failures") or 0) + 1
            if latency_ms is not None:
                latencies = list(metrics.get("latency_ms_samples") or [])
                latencies.append(int(latency_ms))
                metrics["latency_ms_samples"] = latencies[-20:]
                metrics["avg_latency_ms"] = sum(metrics["latency_ms_samples"]) / len(metrics["latency_ms_samples"])
            runs = max(int(metrics.get("runs") or 0), 1)
            metrics["success_rate"] = int(metrics.get("successes") or 0) / runs
            revision.trial_metrics = metrics
            session.commit()
            session.refresh(revision)
            return revision
