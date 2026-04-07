from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text

from .provider import df_payload, series_payload

ROOT = Path(__file__).resolve().parents[3]
HARDSHIP_PATH = ROOT / "Hardship Index of Chicago.csv"


def _load_hardship() -> pd.DataFrame:
    if not HARDSHIP_PATH.exists():
        return pd.DataFrame(columns=["community_area", "community_name", "hardship_2015_2019", "hardship_2020_2024", "hardship_index"])
    raw = pd.read_csv(HARDSHIP_PATH)
    raw = raw[pd.to_numeric(raw.get("GEOID"), errors="coerce").notna()].copy()
    raw["community_area"] = raw["GEOID"].astype(int)
    raw["community_name"] = raw.get("Name", "").astype(str).str.strip()
    raw["community_name"] = raw["community_name"].replace("", np.nan)
    raw["hardship_2015_2019"] = pd.to_numeric(raw.get("HDX_2015-2019"), errors="coerce")
    raw["hardship_2020_2024"] = pd.to_numeric(raw.get("HDX_2020-2024"), errors="coerce")
    raw["hardship_index"] = raw[["hardship_2015_2019", "hardship_2020_2024"]].mean(axis=1)
    return raw[["community_area", "community_name", "hardship_2015_2019", "hardship_2020_2024", "hardship_index"]]


def _mock_region_month() -> pd.DataFrame:
    hardship = _load_hardship()
    if hardship.empty:
        hardship = pd.DataFrame({"community_area": np.arange(1, 78), "hardship_index": np.linspace(20, 80, 77)})
    months = pd.date_range("2019-01-01", "2025-12-01", freq="MS")
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(42)
    for _, h in hardship.iterrows():
        area = int(h["community_area"])
        hardship_idx = float(h.get("hardship_index", 50.0))
        base = 60 + hardship_idx * 1.2 + (area % 9) * 6
        for m in months:
            season = 1.0 + 0.18 * math.sin(2 * math.pi * m.month / 12)
            noise = rng.normal(0, 8)
            count = max(5, int(base * season + noise))
            domestic = max(1, int(count * (0.12 + hardship_idx / 500.0)))
            arrest = max(1, int(count * (0.16 - hardship_idx / 1200.0)))
            rows.append(
                {
                    "community_area": area,
                    "month": m,
                    "count_total": count,
                    "count_domestic": domestic,
                    "count_arrest": arrest,
                    "arrest_rate": arrest / count,
                    "domestic_rate": domestic / count,
                }
            )
    return pd.DataFrame(rows)


def _mock_type_month() -> pd.DataFrame:
    region_month = _mock_region_month()
    type_weights = [
        ("THEFT", 0.28),
        ("BATTERY", 0.22),
        ("CRIMINAL DAMAGE", 0.14),
        ("ASSAULT", 0.10),
        ("MOTOR VEHICLE THEFT", 0.08),
        ("ROBBERY", 0.06),
        ("BURGLARY", 0.06),
        ("OTHER OFFENSE", 0.06),
    ]
    hour_bias = np.array([0.6] * 6 + [0.9] * 6 + [1.1] * 6 + [1.4] * 6, dtype=float)
    hour_bias = hour_bias / hour_bias.sum()
    rng = np.random.default_rng(7)
    rows: list[dict[str, Any]] = []
    for rec in region_month.itertuples(index=False):
        total = int(rec.count_total)
        for crime_type, w in type_weights:
            type_total = max(0, int(total * w))
            if type_total == 0:
                continue
            sampled = rng.multinomial(type_total, hour_bias)
            for hour, cnt in enumerate(sampled):
                if cnt == 0:
                    continue
                rows.append(
                    {
                        "community_area": int(rec.community_area),
                        "month": rec.month,
                        "hour_of_day": int(hour),
                        "primary_type": crime_type,
                        "type_count": int(cnt),
                    }
                )
    return pd.DataFrame(rows)


def _load_region_month(engine, table: str) -> pd.DataFrame:
    query = text(
        f"""
        SELECT
          CAST(community_area AS UNSIGNED) AS community_area,
          DATE_FORMAT(date, '%Y-%m-01') AS month,
          COUNT(*) AS count_total,
          SUM(CASE WHEN domestic IN (1, TRUE, '1', 'true', 'TRUE') THEN 1 ELSE 0 END) AS count_domestic,
          SUM(CASE WHEN arrest IN (1, TRUE, '1', 'true', 'TRUE') THEN 1 ELSE 0 END) AS count_arrest
        FROM `{table}`
        WHERE date >= '2015-01-01' AND date < '2026-01-01'
          AND community_area IS NOT NULL
          AND community_area REGEXP '^[0-9]+$'
        GROUP BY CAST(community_area AS UNSIGNED), DATE_FORMAT(date, '%Y-%m-01')
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    if df.empty:
        return df
    df["month"] = pd.to_datetime(df["month"])
    for c in ["community_area", "count_total", "count_domestic", "count_arrest"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["community_area"] = df["community_area"].astype(int)
    df["arrest_rate"] = np.where(df["count_total"] > 0, df["count_arrest"] / df["count_total"], 0.0)
    df["domestic_rate"] = np.where(df["count_total"] > 0, df["count_domestic"] / df["count_total"], 0.0)
    return df.sort_values(["community_area", "month"]).reset_index(drop=True)


def _load_type_month(engine, table: str) -> pd.DataFrame:
    query = text(
        f"""
        SELECT
          CAST(community_area AS UNSIGNED) AS community_area,
          DATE_FORMAT(date, '%Y-%m-01') AS month,
          HOUR(date) AS hour_of_day,
          COALESCE(NULLIF(TRIM(primary_type), ''), 'UNKNOWN') AS primary_type,
          COUNT(*) AS type_count
        FROM `{table}`
        WHERE date >= '2015-01-01' AND date < '2026-01-01'
          AND community_area IS NOT NULL
          AND community_area REGEXP '^[0-9]+$'
        GROUP BY CAST(community_area AS UNSIGNED), DATE_FORMAT(date, '%Y-%m-01'), HOUR(date), COALESCE(NULLIF(TRIM(primary_type), ''), 'UNKNOWN')
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    if df.empty:
        return df
    df["month"] = pd.to_datetime(df["month"])
    df["community_area"] = pd.to_numeric(df["community_area"], errors="coerce").fillna(0).astype(int)
    df["hour_of_day"] = pd.to_numeric(df["hour_of_day"], errors="coerce").fillna(0).astype(int)
    df["type_count"] = pd.to_numeric(df["type_count"], errors="coerce").fillna(0).astype(int)
    return df


def _region_month(engine, table: str) -> pd.DataFrame:
    if engine is None:
        return _mock_region_month()
    try:
        df = _load_region_month(engine, table)
        return df if not df.empty else _mock_region_month()
    except Exception:
        return _mock_region_month()


def _type_month(engine, table: str) -> pd.DataFrame:
    if engine is None:
        return _mock_type_month()
    try:
        df = _load_type_month(engine, table)
        return df if not df.empty else _mock_type_month()
    except Exception:
        return _mock_type_month()


def get_meta_filters(engine, table: str) -> dict[str, Any]:
    region_month = _region_month(engine, table)
    if region_month.empty:
        return {"meta": {"rows": 0}, "data": []}
    years = sorted(region_month["month"].dt.year.unique().tolist())
    regions = sorted(region_month["community_area"].unique().tolist())

    type_month = _type_month(engine, table)
    top_types = []
    if not type_month.empty:
        top_types = (
            type_month.groupby("primary_type", as_index=False)["type_count"].sum().sort_values("type_count", ascending=False).head(20)["primary_type"].tolist()
        )

    return {
        "meta": {"rows": len(regions), "source": "derived"},
        "data": [
            {
                "years": years,
                "regions": regions,
                "crime_types": top_types,
                "hours": list(range(24)),
            }
        ],
    }


def strategic_crime_count_year(engine, table: str) -> dict[str, Any]:
    df = _region_month(engine, table)
    out = df.assign(year=df["month"].dt.year).groupby(["year", "community_area"], as_index=False)["count_total"].sum()
    return df_payload(out)


def strategic_type_year_by_region(engine, table: str) -> dict[str, Any]:
    types = _type_month(engine, table)
    if types.empty:
        return {"meta": {"rows": 0}, "data": []}
    top = types.groupby("primary_type", as_index=False)["type_count"].sum().sort_values("type_count", ascending=False).head(10)
    keep = set(top["primary_type"])
    out = types[types["primary_type"].isin(keep)].assign(year=types["month"].dt.year).groupby(["year", "community_area", "primary_type"], as_index=False)["type_count"].sum()
    return df_payload(out)


def strategic_count_year_by_type(engine, table: str) -> dict[str, Any]:
    types = _type_month(engine, table)
    if types.empty:
        return {"meta": {"rows": 0}, "data": []}
    out = types.assign(year=types["month"].dt.year).groupby(["year", "primary_type"], as_index=False)["type_count"].sum()
    out = out.sort_values(["year", "type_count"], ascending=[True, False])
    return df_payload(out)


def operations_hour_year_region(engine, table: str) -> dict[str, Any]:
    types = _type_month(engine, table)
    if types.empty:
        return {"meta": {"rows": 0}, "data": []}
    out = types.assign(year=types["month"].dt.year).groupby(["year", "community_area", "hour_of_day"], as_index=False)["type_count"].sum()
    out = out.rename(columns={"type_count": "count_total"})
    return df_payload(out)


def operations_hour_count_type(engine, table: str) -> dict[str, Any]:
    types = _type_month(engine, table)
    if types.empty:
        return {"meta": {"rows": 0}, "data": []}
    out = types.groupby(["hour_of_day", "primary_type"], as_index=False)["type_count"].sum()
    return df_payload(out)


def _risk_forecast_from_monthly(region_month: pd.DataFrame) -> pd.DataFrame:
    df = region_month.copy().sort_values(["community_area", "month"])
    hardship = _load_hardship()
    df = df.merge(hardship[["community_area", "community_name", "hardship_index"]], on="community_area", how="left")
    df["community_name"] = df["community_name"].fillna(df["community_area"].apply(lambda area: f"Community {int(area)}"))
    df["hardship_index"] = df["hardship_index"].fillna(df["hardship_index"].median() if df["hardship_index"].notna().any() else 50)

    grp = df.groupby("community_area", observed=True)["count_total"]
    df["count_lag1"] = grp.shift(1)
    df["count_lag3"] = grp.shift(3)
    df["roll_mean_3"] = grp.transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    df = df.dropna(subset=["count_lag1"]).copy()

    for c in ["count_lag1", "count_lag3", "roll_mean_3", "hardship_index"]:
        s = df[c]
        std = s.std(ddof=0)
        df[f"z_{c}"] = 0 if std == 0 or np.isnan(std) else (s - s.mean()) / std

    score = (
        0.45 * df["z_count_lag1"]
        + 0.20 * df["z_count_lag3"].fillna(0)
        + 0.20 * df["z_roll_mean_3"]
        + 0.15 * df["z_hardship_index"]
    )
    df["pred_prob"] = 1 / (1 + np.exp(-score))
    df["pred_month"] = df["month"] + pd.offsets.MonthBegin(1)

    tgt = df[["community_area", "month", "count_total"]].rename(columns={"month": "pred_month", "count_total": "actual_count"})
    pred = df[["community_area", "community_name", "month", "pred_month", "pred_prob", "hardship_index"]].merge(
        tgt, on=["community_area", "pred_month"], how="left"
    )
    pred = pred.dropna(subset=["actual_count"]).copy()

    q75 = pred["actual_count"].quantile(0.75)
    pred["actual_label"] = (pred["actual_count"] >= q75).astype(int)
    pred["pred_label"] = (pred["pred_prob"] >= pred["pred_prob"].quantile(0.75)).astype(int)
    pred["risk_level"] = pd.cut(pred["pred_prob"], bins=[-1, 0.4, 0.7, 2], labels=["low", "medium", "high"])
    return pred


def model_predict_next_month(engine, table: str, target_month: str | None = None) -> dict[str, Any]:
    region_month = _region_month(engine, table)
    pred = _risk_forecast_from_monthly(region_month)
    if pred.empty:
        return {"meta": {"rows": 0}, "data": []}

    if target_month:
        tm = pd.Period(target_month, freq="M").to_timestamp()
    else:
        tm = pred["pred_month"].max()
    out = pred[pred["pred_month"] == tm][
        ["community_area", "community_name", "pred_month", "pred_prob", "pred_label", "risk_level", "hardship_index"]
    ].copy()
    out = out.sort_values("pred_prob", ascending=False).reset_index(drop=True)

    # Re-bin risk segments for map display by month-level ranking:
    # top 25% -> high, top 50% -> medium, remaining -> low.
    n = len(out)
    if n > 0:
        top25 = max(1, math.ceil(n * 0.25))
        top50 = max(top25, math.ceil(n * 0.50))

        out["pred_label"] = 0
        out.loc[: top25 - 1, "pred_label"] = 1

        out["risk_level"] = "low"
        out.loc[: top25 - 1, "risk_level"] = "high"
        if top50 > top25:
            out.loc[top25 : top50 - 1, "risk_level"] = "medium"

    out["pred_month"] = out["pred_month"].dt.strftime("%Y-%m")
    return df_payload(out, target_month=str(tm.date()))


def crime_action_dominant_type_region(engine, table: str) -> dict[str, Any]:
    types = _type_month(engine, table)
    if types.empty:
        return {"meta": {"rows": 0}, "data": []}
    recent_cut = types[types["month"] >= (types["month"].max() - pd.DateOffset(months=12))]
    top = (
        recent_cut.groupby(["community_area", "primary_type"], as_index=False)["type_count"].sum()
        .sort_values(["community_area", "type_count"], ascending=[True, False])
        .drop_duplicates(subset=["community_area"])
    )
    top = top.rename(columns={"type_count": "count_total", "primary_type": "dominant_type"})
    return df_payload(top)


def crime_action_dominant_type_hour(engine, table: str) -> dict[str, Any]:
    types = _type_month(engine, table)
    if types.empty:
        return {"meta": {"rows": 0}, "data": []}
    out = (
        types.groupby(["hour_of_day", "primary_type"], as_index=False)["type_count"].sum()
        .sort_values(["hour_of_day", "type_count"], ascending=[True, False])
        .drop_duplicates(subset=["hour_of_day"])
        .rename(columns={"type_count": "count_total", "primary_type": "dominant_type"})
    )
    return df_payload(out)


def crime_action_domestic_trend(engine, table: str) -> dict[str, Any]:
    df = _region_month(engine, table)
    out = df[["community_area", "month", "count_domestic", "domestic_rate"]].copy()
    out["month"] = out["month"].dt.strftime("%Y-%m")
    return df_payload(out)


def anomaly_mom_count_change(engine, table: str) -> dict[str, Any]:
    df = _region_month(engine, table).sort_values(["community_area", "month"]) 
    df["prev_count"] = df.groupby("community_area", observed=True)["count_total"].shift(1)
    df["mom_change"] = df["count_total"] - df["prev_count"]
    out = df.dropna(subset=["mom_change"])[["community_area", "month", "count_total", "mom_change"]].copy()
    out["month"] = out["month"].dt.strftime("%Y-%m")
    return df_payload(out)


def anomaly_mom_composition_change(engine, table: str) -> dict[str, Any]:
    types = _type_month(engine, table)
    if types.empty:
        return {"meta": {"rows": 0}, "data": []}
    # Aggregate to city-level monthly composition and keep only 2025 top-10 crime types.
    monthly = types.groupby(["month", "primary_type"], as_index=False)["type_count"].sum()
    monthly_2025 = monthly[monthly["month"].dt.year == 2025].copy()
    if monthly_2025.empty:
        return {"meta": {"rows": 0, "year": 2025}, "data": []}

    top_types = (
        monthly_2025.groupby("primary_type", as_index=False)["type_count"]
        .sum()
        .sort_values("type_count", ascending=False)
        .head(10)["primary_type"]
        .tolist()
    )
    monthly_top = monthly_2025[monthly_2025["primary_type"].isin(top_types)].copy()

    month_totals = monthly_2025.groupby("month", as_index=False)["type_count"].sum().rename(columns={"type_count": "month_total"})
    monthly_top = monthly_top.merge(month_totals, on="month", how="left")
    monthly_top["type_share"] = np.where(monthly_top["month_total"] > 0, monthly_top["type_count"] / monthly_top["month_total"], 0.0)
    monthly_top = monthly_top.sort_values(["primary_type", "month"])
    monthly_top["prev_share"] = monthly_top.groupby("primary_type", observed=True)["type_share"].shift(1)
    monthly_top["mom_share_change"] = monthly_top["type_share"] - monthly_top["prev_share"]

    out = monthly_top.dropna(subset=["mom_share_change"])[["month", "primary_type", "type_count", "type_share", "mom_share_change"]].copy()
    out["month"] = out["month"].dt.strftime("%Y-%m")
    out = out.sort_values(["month", "primary_type"]).reset_index(drop=True)
    return df_payload(out, year=2025, top_types=top_types)


def anomaly_observed_vs_predicted(engine, table: str) -> dict[str, Any]:
    pred = _risk_forecast_from_monthly(_region_month(engine, table))
    if pred.empty:
        return {"meta": {"rows": 0}, "data": []}
    out = pred[["community_area", "pred_month", "actual_count", "pred_prob", "pred_label", "actual_label"]].copy()
    out["pred_month"] = out["pred_month"].dt.strftime("%Y-%m")
    return df_payload(out)


def socio_risk_vs_hardship(engine, table: str) -> dict[str, Any]:
    pred = _risk_forecast_from_monthly(_region_month(engine, table))
    out = pred.groupby("community_area", as_index=False).agg(pred_prob=("pred_prob", "mean"), hardship_index=("hardship_index", "mean"), actual_rate=("actual_label", "mean"))
    return df_payload(out)


def socio_predicted_risk_hardship_map(engine, table: str) -> dict[str, Any]:
    return model_predict_next_month(engine, table)


def socio_region_risk_hardship_trend(engine, table: str) -> dict[str, Any]:
    pred = _risk_forecast_from_monthly(_region_month(engine, table))
    out = pred[["community_area", "pred_month", "pred_prob", "hardship_index"]].copy()
    out["pred_month"] = out["pred_month"].dt.strftime("%Y-%m")
    return df_payload(out)


def performance_hotspot_hit(engine, table: str) -> dict[str, Any]:
    pred = _risk_forecast_from_monthly(_region_month(engine, table))
    if pred.empty:
        return {"meta": {"rows": 0}, "data": []}
    grp = pred.groupby("pred_month", as_index=False).apply(lambda x: pd.Series({"hotspot_precision": float((x["pred_label"] & x["actual_label"]).sum() / max(int(x["pred_label"].sum()), 1)), "hotspot_recall": float((x["pred_label"] & x["actual_label"]).sum() / max(int(x["actual_label"].sum()), 1))}))
    grp["pred_month"] = grp["pred_month"].dt.strftime("%Y-%m")
    return df_payload(grp)


def performance_by_region(engine, table: str) -> dict[str, Any]:
    pred = _risk_forecast_from_monthly(_region_month(engine, table))
    out = pred.groupby("community_area", as_index=False).apply(lambda x: pd.Series({"accuracy": float((x["pred_label"] == x["actual_label"]).mean()), "precision": float((x["pred_label"] & x["actual_label"]).sum() / max(int(x["pred_label"].sum()), 1)), "recall": float((x["pred_label"] & x["actual_label"]).sum() / max(int(x["actual_label"].sum()), 1)), "support": int(len(x))}))
    return df_payload(out)


def performance_by_crime_type(engine, table: str) -> dict[str, Any]:
    dom = crime_action_dominant_type_region(engine, table).get("data", [])
    if not dom:
        return {"meta": {"rows": 0}, "data": []}
    region_perf = performance_by_region(engine, table).get("data", [])
    ddf = pd.DataFrame(dom)
    pdf = pd.DataFrame(region_perf)
    out = ddf.merge(pdf, on="community_area", how="left").groupby("dominant_type", as_index=False).agg(accuracy=("accuracy", "mean"), precision=("precision", "mean"), recall=("recall", "mean"), communities=("community_area", "nunique"))
    return df_payload(out)


def dashboard_command_center(engine, table: str) -> dict[str, Any]:
    pred = model_predict_next_month(engine, table).get("data", [])
    trend = strategic_crime_count_year(engine, table).get("data", [])
    heat = operations_hour_year_region(engine, table).get("data", [])
    type_dist = strategic_count_year_by_type(engine, table).get("data", [])
    alerts = anomaly_mom_count_change(engine, table).get("data", [])
    top_alerts = sorted(alerts, key=lambda r: r.get("mom_change", 0), reverse=True)[:10]
    return {
        "meta": {"source": "aggregated"},
        "data": [
            {
                "predicted_risk_map": pred,
                "yearly_trend": trend,
                "hour_region_heatmap": heat,
                "crime_type_distribution": type_dist,
                "alerts": top_alerts,
            }
        ],
    }
