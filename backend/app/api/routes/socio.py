from __future__ import annotations

from fastapi import APIRouter

from ..deps import provider
from ...services import chicago_service as svc

router = APIRouter(prefix="/socio", tags=["socio"])


@router.get("/risk-vs-hardship")
def risk_vs_hardship():
    return provider.fetch("socio_risk_vs_hardship", svc.socio_risk_vs_hardship)


@router.get("/predicted-risk-hardship-map")
def predicted_risk_hardship_map(target_month: str | None = None):
    key = f"socio_predicted_risk_map_v4_{target_month or 'latest'}"
    return provider.fetch(key, lambda engine, table: svc.model_predict_next_month(engine, table, target_month=target_month))


@router.get("/region-risk-hardship-trend")
def region_risk_hardship_trend():
    return provider.fetch("socio_region_risk_hardship_trend", svc.socio_region_risk_hardship_trend)
