from __future__ import annotations

from fastapi import APIRouter

from ..deps import provider
from ...services import chicago_service as svc

router = APIRouter(prefix="/crime-action", tags=["crime-action"])


@router.get("/dominant-type-by-region")
def dominant_type_by_region():
    return provider.fetch("crime_action_dominant_type_region", svc.crime_action_dominant_type_region)


@router.get("/dominant-type-by-hour")
def dominant_type_by_hour():
    return provider.fetch("crime_action_dominant_type_hour", svc.crime_action_dominant_type_hour)


@router.get("/domestic-trend")
def domestic_trend():
    return provider.fetch("crime_action_domestic_trend", svc.crime_action_domestic_trend)
