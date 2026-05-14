from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from recruit_station.api.deps import get_session
from recruit_station.repositories import MetricsRepository
from recruit_station.schemas import MetricsSummary

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("", response_model=MetricsSummary)
def get_metrics(session: Session = Depends(get_session)) -> MetricsSummary:
    return MetricsRepository(session).summary()

