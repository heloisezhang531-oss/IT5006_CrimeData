from __future__ import annotations

from fastapi import APIRouter, Query

from ..deps import provider
from ...services import eda_service as svc

router = APIRouter(prefix="/eda", tags=["eda"])


@router.get("/key-stats/arrest-domestic")
def key_stats_arrest_domestic():
    return provider.fetch("eda_key_stats_arrest_domestic", svc.key_stats_arrest_domestic)


@router.get("/temporal/yearly")
def temporal_yearly():
    return provider.fetch("eda_temporal_yearly", svc.temporal_yearly)


@router.get("/temporal/monthly")
def temporal_monthly():
    return provider.fetch("eda_temporal_monthly", svc.temporal_monthly)


@router.get("/temporal/day-of-week")
def temporal_day_of_week():
    return provider.fetch("eda_temporal_day_of_week", svc.temporal_day_of_week)


@router.get("/temporal/hour-day-heatmap")
def temporal_hour_day_heatmap():
    return provider.fetch("eda_temporal_hour_day_heatmap", svc.temporal_hour_day_heatmap)


@router.get("/temporal/crime-types-yearly")
def temporal_crime_types_yearly(limit: str = Query(default="all", pattern=r"^(all|[1-9][0-9]*)$")):
    key = f"eda_temporal_crime_types_yearly_{limit}"
    return provider.fetch(key, lambda engine, table: svc.temporal_crime_types_yearly(engine, table, limit=limit))


@router.get("/geography/points")
def geography_points(year: int = Query(..., ge=2015, le=2024), limit: int = Query(default=20000, ge=1, le=200000)):
    key = f"eda_geo_points_{year}_{limit}"
    return provider.fetch(key, lambda engine, table: svc.geography_points(engine, table, year=year, limit=limit))


@router.get("/geography/community-choropleth")
def geography_community_choropleth(year: int = Query(..., ge=2015, le=2024)):
    key = f"eda_geo_choropleth_{year}"
    return provider.fetch(
        key,
        lambda engine, table: svc.geography_community_choropleth(engine, table, year=year),
    )


@router.get("/geography/community-geojson")
def geography_community_geojson():
    return provider.fetch("eda_geo_community_geojson", svc.geography_community_geojson)


@router.get("/geography/hardship-index")
def geography_hardship_index():
    return provider.fetch("eda_geo_hardship_index", svc.geography_hardship_index)


@router.get("/categorical/top-crime-types")
def categorical_top_crime_types(limit: int = Query(default=10, ge=1, le=50)):
    key = f"eda_categorical_top_crime_types_{limit}"
    return provider.fetch(
        key,
        lambda engine, table: svc.categorical_top_crime_types(engine, table, limit=limit),
    )


@router.get("/categorical/top-locations")
def categorical_top_locations(limit: int = Query(default=10, ge=1, le=50)):
    key = f"eda_categorical_top_locations_{limit}"
    return provider.fetch(
        key,
        lambda engine, table: svc.categorical_top_locations(engine, table, limit=limit),
    )


@router.get("/categorical/crime-location-heatmap")
def categorical_crime_location_heatmap(limit: int = Query(default=10, ge=1, le=50)):
    key = f"eda_categorical_crime_location_heatmap_{limit}"
    return provider.fetch(
        key,
        lambda engine, table: svc.categorical_crime_location_heatmap(engine, table, limit=limit),
    )

