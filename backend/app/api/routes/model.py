from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.deps import provider
from backend.app.schemas.common import PredictRequest
from backend.app.services import chicago_service as svc

router = APIRouter(prefix="/model", tags=["model"])


@router.post("/predict-next-month")
def predict_next_month(payload: PredictRequest):
    key = f"model_predict_{payload.target_month or 'latest'}_{payload.feature_mode}"
    response = provider.fetch(
        key,
        lambda engine, table: svc.model_predict_next_month(engine, table, target_month=payload.target_month),
    )
    if payload.region_ids:
        kept = [r for r in response.get("data", []) if int(r.get("community_area", -1)) in set(payload.region_ids)]
        response["data"] = kept
        response.setdefault("meta", {})["rows"] = len(kept)
    response.setdefault("meta", {})["feature_mode"] = payload.feature_mode
    return response
