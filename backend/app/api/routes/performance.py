from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.deps import provider
from backend.app.services import chicago_service as svc

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/hotspot-hit")
def hotspot_hit():
    return provider.fetch("performance_hotspot_hit", svc.performance_hotspot_hit)


@router.get("/by-region")
def by_region():
    return provider.fetch("performance_by_region", svc.performance_by_region)


@router.get("/by-crime-type")
def by_crime_type():
    return provider.fetch("performance_by_crime_type", svc.performance_by_crime_type)
