from __future__ import annotations

from fastapi import APIRouter

from ..deps import provider
from ...core.config import settings
from ...services import chicago_service as svc

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/filters")
def get_filters():
    return provider.fetch("meta_filters", svc.get_meta_filters)


@router.get("/config")
def get_config():
    return {
        "meta": {
            "app": settings.app_name,
            "version": settings.app_version,
            "mode": provider.mode,
            "db_available": provider.db_available,
        },
        "data": [{"mapbox_token_ready": bool(settings.mapbox_token)}],
    }
