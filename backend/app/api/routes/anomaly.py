from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.deps import provider
from backend.app.services import chicago_service as svc

router = APIRouter(prefix="/anomaly", tags=["anomaly"])


@router.get("/mom-count-change")
def mom_count_change():
    return provider.fetch("anomaly_mom_count_change", svc.anomaly_mom_count_change)


@router.get("/mom-composition-change")
def mom_composition_change():
    return provider.fetch("anomaly_mom_composition_change", svc.anomaly_mom_composition_change)


@router.get("/observed-vs-predicted")
def observed_vs_predicted():
    return provider.fetch("anomaly_observed_vs_predicted", svc.anomaly_observed_vs_predicted)
