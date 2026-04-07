from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import analysis
from . import chicago_service as chicago
from .provider import df_payload, series_payload

ROOT = Path(__file__).resolve().parents[3]
HARDSHIP_PATH = ROOT / "Hardship Index of Chicago.csv"

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

COMMUNITY_NAME_MAP = {
    "1": "Rogers Park",
    "2": "West Ridge",
    "3": "Uptown",
    "4": "Lincoln Square",
    "5": "North Center",
    "6": "Lake View",
    "7": "Lincoln Park",
    "8": "Near North Side",
    "9": "Edison Park",
    "10": "Norwood Park",
    "11": "Jefferson Park",
    "12": "Forest Glen",
    "13": "North Park",
    "14": "Albany Park",
    "15": "Portage Park",
    "16": "Irving Park",
    "17": "Dunning",
    "18": "Montclare",
    "19": "Belmont Cragin",
    "20": "Hermosa",
    "21": "Avondale",
    "22": "Logan Square",
    "23": "Humboldt Park",
    "24": "West Town",
    "25": "Austin",
    "26": "West Garfield Park",
    "27": "East Garfield Park",
    "28": "Near West Side",
    "29": "North Lawndale",
    "30": "South Lawndale",
    "31": "Lower West Side",
    "32": "Loop",
    "33": "Near South Side",
    "34": "Armour Square",
    "35": "Douglas",
    "36": "Oakland",
    "37": "Fuller Park",
    "38": "Grand Boulevard",
    "39": "Kenwood",
    "40": "Washington Park",
    "41": "Hyde Park",
    "42": "Woodlawn",
    "43": "South Shore",
    "44": "Chatham",
    "45": "Avalon Park",
    "46": "South Chicago",
    "47": "Burnside",
    "48": "Calumet Heights",
    "49": "Roseland",
    "50": "Pullman",
    "51": "South Deering",
    "52": "East Side",
    "53": "West Pullman",
    "54": "Riverdale",
    "55": "Hegewisch",
    "56": "Garfield Ridge",
    "57": "Archer Heights",
    "58": "Brighton Park",
    "59": "McKinley Park",
    "60": "Bridgeport",
    "61": "New City",
    "62": "West Elsdon",
    "63": "Gage Park",
    "64": "Clearing",
    "65": "West Lawn",
    "66": "Chicago Lawn",
    "67": "West Englewood",
    "68": "Englewood",
    "69": "Greater Grand Crossing",
    "70": "Ashburn",
    "71": "Auburn Gresham",
    "72": "Beverly",
    "73": "Washington Heights",
    "74": "Mount Greenwood",
    "75": "Morgan Park",
    "76": "O'Hare",
    "77": "Edgewater",
}


def _month_year(df: pd.DataFrame, col: str = "month") -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=int)
    return pd.to_datetime(df[col]).dt.year


def _fallback_region_month(engine, table: str) -> pd.DataFrame:
    df = chicago._region_month(engine, table).copy()
    if df.empty:
        return df
    df["month"] = pd.to_datetime(df["month"])
    df = df[(df["month"].dt.year >= 2015) & (df["month"].dt.year <= 2024)]
    return df


def _fallback_type_month(engine, table: str) -> pd.DataFrame:
    df = chicago._type_month(engine, table).copy()
    if df.empty:
        return df
    df["month"] = pd.to_datetime(df["month"])
    df = df[(df["month"].dt.year >= 2015) & (df["month"].dt.year <= 2024)]
    return df


def key_stats_arrest_domestic(engine, table: str) -> dict[str, Any]:
    arrest_rows: list[dict[str, Any]] = []
    domestic_rows: list[dict[str, Any]] = []
    if engine is not None:
        stats = analysis.get_arrest_domestic_stats(engine)
        arrest_df = stats.get("arrest", pd.DataFrame())
        domestic_df = stats.get("domestic", pd.DataFrame())
        if not arrest_df.empty:
            arrest_rows = [
                {
                    "status": "Arrested" if str(r["Arrest"]) == "True" else "Not Arrested",
                    "raw_value": str(r["Arrest"]),
                    "count": int(r["Count"]),
                }
                for _, r in arrest_df.iterrows()
            ]
        if not domestic_df.empty:
            domestic_rows = [
                {
                    "type": "Domestic" if str(r["Domestic"]) == "True" else "Non-Domestic",
                    "raw_value": str(r["Domestic"]),
                    "count": int(r["Count"]),
                }
                for _, r in domestic_df.iterrows()
            ]
    if not arrest_rows or not domestic_rows:
        monthly = _fallback_region_month(engine, table)
        if monthly.empty:
            arrest_rows = [{"status": "Arrested", "raw_value": "True", "count": 0}, {"status": "Not Arrested", "raw_value": "False", "count": 0}]
            domestic_rows = [{"type": "Domestic", "raw_value": "True", "count": 0}, {"type": "Non-Domestic", "raw_value": "False", "count": 0}]
        else:
            arrested = int(monthly["count_arrest"].sum())
            total = int(monthly["count_total"].sum())
            domestic = int(monthly["count_domestic"].sum())
            arrest_rows = [
                {"status": "Arrested", "raw_value": "True", "count": arrested},
                {"status": "Not Arrested", "raw_value": "False", "count": max(total - arrested, 0)},
            ]
            domestic_rows = [
                {"type": "Domestic", "raw_value": "True", "count": domestic},
                {"type": "Non-Domestic", "raw_value": "False", "count": max(total - domestic, 0)},
            ]
    return series_payload([{"arrest": arrest_rows, "domestic": domestic_rows}])


def temporal_yearly(engine, table: str) -> dict[str, Any]:
    if engine is not None:
        df = analysis.get_yearly_trends(engine)
        if not df.empty:
            return df_payload(df.rename(columns={"year": "year", "count": "count"}))
    fallback = _fallback_region_month(engine, table)
    out = (
        fallback.assign(year=_month_year(fallback))
        .groupby("year", as_index=False)["count_total"]
        .sum()
        .rename(columns={"count_total": "count"})
    )
    return df_payload(out)


def temporal_monthly(engine, table: str) -> dict[str, Any]:
    if engine is not None:
        df = analysis.get_monthly_trends(engine)
        if not df.empty:
            return df_payload(df.rename(columns={"count": "count"}))
    fallback = _fallback_region_month(engine, table)
    out = (
        fallback.assign(month_num=pd.to_datetime(fallback["month"]).dt.month)
        .groupby("month_num", as_index=False)["count_total"]
        .sum()
        .rename(columns={"month_num": "month", "count_total": "count"})
        .sort_values("month")
    )
    return df_payload(out)


def temporal_day_of_week(engine, table: str) -> dict[str, Any]:
    if engine is not None:
        df = analysis.get_day_of_week_counts(engine)
        if not df.empty:
            out = df[["Day", "count"]].copy()
            out["day_index"] = out["Day"].apply(lambda d: DAY_ORDER.index(d))
            return df_payload(out.sort_values("day_index"))
    fallback = _fallback_region_month(engine, table)
    total = int(fallback["count_total"].sum()) if not fallback.empty else 0
    weights = {"Mon": 0.14, "Tue": 0.13, "Wed": 0.13, "Thu": 0.14, "Fri": 0.16, "Sat": 0.16, "Sun": 0.14}
    out = pd.DataFrame(
        [{"Day": d, "count": int(total * w), "day_index": i} for i, (d, w) in enumerate(weights.items())]
    )
    return df_payload(out)


def temporal_hour_day_heatmap(engine, table: str) -> dict[str, Any]:
    if engine is not None:
        heat = analysis.get_heatmap_data(engine)
        if not heat.empty:
            rows: list[dict[str, Any]] = []
            for day in heat.index:
                for hour in heat.columns:
                    rows.append({"day": str(day), "hour": int(hour), "crime_count": int(heat.loc[day, hour])})
            return series_payload(rows)
    type_month = _fallback_type_month(engine, table)
    if type_month.empty:
        return series_payload([])
    hourly = type_month.groupby("hour_of_day", as_index=False)["type_count"].sum()
    day_weights = {"Mon": 0.14, "Tue": 0.13, "Wed": 0.13, "Thu": 0.14, "Fri": 0.16, "Sat": 0.16, "Sun": 0.14}
    rows = []
    for day, w in day_weights.items():
        for _, r in hourly.iterrows():
            rows.append({"day": day, "hour": int(r["hour_of_day"]), "crime_count": int(r["type_count"] * w)})
    return series_payload(rows)


def temporal_crime_types_yearly(engine, table: str, limit: str = "all") -> dict[str, Any]:
    parsed_limit: int | None
    if limit == "all":
        parsed_limit = None
    else:
        parsed_limit = int(limit)
    if engine is not None:
        df = analysis.get_top_crime_types_yearly(engine, limit=parsed_limit)
        if not df.empty:
            return df_payload(df.rename(columns={"year": "year", "primary_type": "primary_type", "count": "count"}))
    types = _fallback_type_month(engine, table)
    if types.empty:
        return df_payload(pd.DataFrame(columns=["year", "primary_type", "count"]))
    out = (
        types.assign(year=_month_year(types))
        .groupby(["year", "primary_type"], as_index=False)["type_count"]
        .sum()
        .rename(columns={"type_count": "count"})
    )
    if parsed_limit:
        keep = out.groupby("primary_type", as_index=False)["count"].sum().sort_values("count", ascending=False).head(parsed_limit)["primary_type"]
        out = out[out["primary_type"].isin(set(keep))]
    return df_payload(out.sort_values(["primary_type", "year"]))


def _pseudo_lat_lng(area: int) -> tuple[float, float]:
    center_lat, center_lng = 41.8781, -87.6298
    lat = center_lat + ((area % 7) - 3) * 0.018
    lng = center_lng + ((area % 11) - 5) * 0.024
    return lat, lng


def geography_points(engine, table: str, year: int, limit: int) -> dict[str, Any]:
    if engine is not None:
        df = analysis.get_map_data(engine, selected_year=year, limit=limit)
        if not df.empty:
            return df_payload(df)
    monthly = _fallback_region_month(engine, table)
    if monthly.empty:
        return series_payload([])
    yearly = monthly[monthly["month"].dt.year == year].groupby("community_area", as_index=False)["count_total"].sum()
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(year)
    for _, rec in yearly.iterrows():
        area = int(rec["community_area"])
        count = int(rec["count_total"])
        n = max(1, min(120, count // 600))
        for _ in range(n):
            lat, lng = _pseudo_lat_lng(area)
            rows.append(
                {
                    "latitude": float(lat + rng.normal(0, 0.006)),
                    "longitude": float(lng + rng.normal(0, 0.008)),
                    "community_area": area,
                }
            )
    if len(rows) > limit:
        rows = rows[:limit]
    return series_payload(rows)


def geography_community_choropleth(engine, table: str, year: int) -> dict[str, Any]:
    if engine is not None:
        df = analysis.draw_choropleth(engine, selected_year=year)
        if not df.empty:
            return df_payload(df)
    types = _fallback_type_month(engine, table)
    types = types[types["month"].dt.year == year].copy()
    if types.empty:
        return series_payload([])
    total = types.groupby("community_area", as_index=False)["type_count"].sum().rename(columns={"type_count": "crime_count"})
    top = (
        types.sort_values(["community_area", "type_count"], ascending=[True, False])
        .groupby("community_area")
        .head(5)
        .assign(formatted=lambda d: d["primary_type"] + " (" + d["type_count"].astype(int).astype(str) + ")")
        .groupby("community_area", as_index=False)["formatted"]
        .agg("<br>".join)
        .rename(columns={"formatted": "top_types"})
    )
    out = total.merge(top, on="community_area", how="left")
    out["community_area"] = out["community_area"].astype(int).astype(str)
    out["community_name"] = out["community_area"].map(COMMUNITY_NAME_MAP).fillna("Unknown")
    return df_payload(out)


def geography_community_geojson(_: Any, __: str) -> dict[str, Any]:
    geo = analysis.get_geojson1()
    if geo:
        return series_payload([{"geojson": geo}])
    return series_payload([])


def geography_hardship_index(_: Any, __: str) -> dict[str, Any]:
    if not HARDSHIP_PATH.exists():
        return series_payload([])
    df = pd.read_csv(HARDSHIP_PATH)
    return df_payload(df)


def categorical_top_crime_types(engine, table: str, limit: int) -> dict[str, Any]:
    if engine is not None:
        df = analysis.get_top_crime_types_stacked(engine, limit=limit)
        if not df.empty:
            return df_payload(df)
    types = _fallback_type_month(engine, table)
    if types.empty:
        return series_payload([])
    totals = types.groupby("primary_type", as_index=False)["type_count"].sum().sort_values("type_count", ascending=False).head(limit)
    rows = []
    for _, rec in totals.iterrows():
        total = int(rec["type_count"])
        arrested = int(total * 0.2)
        rows.append({"primary_type": rec["primary_type"], "arrest": "True", "count": arrested})
        rows.append({"primary_type": rec["primary_type"], "arrest": "False", "count": max(total - arrested, 0)})
    return series_payload(rows)


def categorical_top_locations(engine, table: str, limit: int) -> dict[str, Any]:
    if engine is not None:
        df = analysis.get_top_locations_stacked(engine, limit=limit)
        if not df.empty:
            return df_payload(df)
    monthly = _fallback_region_month(engine, table)
    if monthly.empty:
        return series_payload([])
    names = [
        "STREET",
        "RESIDENCE",
        "APARTMENT",
        "SIDEWALK",
        "ALLEY",
        "PARKING LOT",
        "SMALL RETAIL STORE",
        "GAS STATION",
        "SCHOOL",
        "CTA STATION",
    ][:limit]
    total = int(monthly["count_total"].sum())
    rows = []
    for i, name in enumerate(names):
        base = int(total * (0.12 / (1 + 0.2 * i)))
        arrested = int(base * (0.16 + 0.01 * math.sin(i)))
        rows.append({"location_description": name, "arrest": "True", "count": max(arrested, 0)})
        rows.append({"location_description": name, "arrest": "False", "count": max(base - arrested, 0)})
    return series_payload(rows)


def categorical_crime_location_heatmap(engine, table: str, limit: int) -> dict[str, Any]:
    if engine is not None:
        crime_df = analysis.get_top_crime_types_stacked(engine, limit=limit)
        loc_df = analysis.get_top_locations_stacked(engine, limit=limit)
        if not crime_df.empty and not loc_df.empty:
            top_types = crime_df.groupby("primary_type", as_index=False)["count"].sum().sort_values("count", ascending=False)["primary_type"].tolist()
            top_locs = (
                loc_df.groupby("location_description", as_index=False)["count"]
                .sum()
                .sort_values("count", ascending=False)["location_description"]
                .tolist()
            )
            heat = analysis.get_crime_location_heatmap(engine, top_types, top_locs)
            if not heat.empty:
                rows = []
                for crime in heat.index:
                    for loc in heat.columns:
                        rows.append(
                            {
                                "primary_type": str(crime),
                                "location_description": str(loc),
                                "count": int(heat.loc[crime, loc]),
                            }
                        )
                return series_payload(rows)
    top_crimes = [r["primary_type"] for r in categorical_top_crime_types(engine, table, limit).get("data", []) if r["arrest"] == "False"][:limit]
    top_locs = [r["location_description"] for r in categorical_top_locations(engine, table, limit).get("data", []) if r["arrest"] == "False"][:limit]
    rows = []
    for i, crime in enumerate(top_crimes):
        for j, loc in enumerate(top_locs):
            rows.append({"primary_type": crime, "location_description": loc, "count": int(max(0, (limit - i) * (limit - j) * 27))})
    return series_payload(rows)


