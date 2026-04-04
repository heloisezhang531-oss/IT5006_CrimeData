from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.deps import provider
from backend.app.services import chicago_service as svc

router = APIRouter(prefix="/strategic", tags=["strategic"])


@router.get("/crime-count-year")
def crime_count_year():
    return provider.fetch("strategic_crime_count_year", svc.strategic_crime_count_year)


@router.get("/crime-type-year-by-region")
def crime_type_year_by_region():
    return provider.fetch("strategic_crime_type_year_by_region", svc.strategic_type_year_by_region)


@router.get("/crime-count-year-by-type")
def crime_count_year_by_type():
    return provider.fetch("strategic_crime_count_year_by_type", svc.strategic_count_year_by_type)
