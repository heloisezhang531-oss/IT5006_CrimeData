from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.deps import provider
from backend.app.services import chicago_service as svc

router = APIRouter(prefix="/model-lab", tags=["model-lab"])


@router.get("/ablation")
def ablation():
    return provider.fetch("model_lab_ablation", svc.model_lab_ablation)


@router.get("/generalization")
def generalization():
    return provider.fetch("model_lab_generalization", svc.model_lab_generalization)


@router.get("/reliability")
def reliability():
    return provider.fetch("model_lab_reliability", svc.model_lab_reliability)
