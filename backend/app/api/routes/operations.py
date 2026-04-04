from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.deps import provider
from backend.app.services import chicago_service as svc

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/hourly-year-by-region")
def hourly_year_by_region():
    return provider.fetch("operations_hourly_year_region", svc.operations_hour_year_region)


@router.get("/hourly-count-by-type")
def hourly_count_by_type():
    return provider.fetch("operations_hourly_count_type", svc.operations_hour_count_type)


@router.get("/predicted-risk-next-month")
def predicted_risk_next_month(target_month: str | None = None):
    key = f"operations_predicted_risk_{target_month or 'latest'}"
    return provider.fetch(key, lambda engine, table: svc.model_predict_next_month(engine, table, target_month=target_month))
