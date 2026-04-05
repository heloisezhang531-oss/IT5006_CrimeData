from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tidb_utils import create_tidb_engine, resolve_chicago_table_name
HOLDOUT_PRED_PATH = ROOT_DIR / "experiment/new_cross_validation/reports/holdout_2025_predictions_xgboost.csv"
METRICS_PATH = ROOT_DIR / "experiment/new_ablation_shap/reports/with_hardship_metrics.csv"
FEATURE_IMPORTANCE_PATH = ROOT_DIR / "experiment/new_ablation_shap/reports/shap_global_importance.csv"

app = FastAPI(title="Predictive Policing API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_engine = None
_table = None


def _get_engine():
    global _engine
    if _engine is None:
        env_path = ROOT_DIR / ".env"
        _engine = create_tidb_engine(env_file=str(env_path) if env_path.exists() else None)
    return _engine


def _get_engine_and_table():
    global _table
    engine = _get_engine()
    if _table is None:
        _table = resolve_chicago_table_name(engine)
    return engine, _table


def _to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.replace({pd.NA: None})
    return clean.to_dict(orient="records")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(ValueError)
def value_error_handler(_, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/api/crime/current-month-community")
def current_month_community() -> dict[str, Any]:
    engine, table = _get_engine_and_table()
    query = text(
        f"""
        WITH latest_month AS (
          SELECT DATE_FORMAT(MAX(`DATE`), '%Y-%m-01') AS month_start
          FROM `{table}`
          WHERE `DATE` IS NOT NULL
        )
        SELECT
          CAST(`COMMUNITY_AREA` AS UNSIGNED) AS community_area,
          COUNT(*) AS crime_count,
          lm.month_start AS month_start
        FROM `{table}` t
        CROSS JOIN latest_month lm
        WHERE DATE_FORMAT(t.`DATE`, '%Y-%m-01') = lm.month_start
          AND t.`COMMUNITY_AREA` IS NOT NULL
          AND t.`COMMUNITY_AREA` REGEXP '^[0-9]+$'
        GROUP BY CAST(t.`COMMUNITY_AREA` AS UNSIGNED), lm.month_start
        ORDER BY crime_count DESC
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    month_start = df["month_start"].iloc[0] if not df.empty else None
    if not df.empty:
        df["community_area"] = df["community_area"].astype(int).astype(str)

    return {"month_start": month_start, "data": _to_records(df.drop(columns=["month_start"], errors="ignore"))}


@app.get("/api/crime/predicted-next-month-risk")
def predicted_next_month_risk() -> dict[str, Any]:
    pred_df = pd.read_csv(HOLDOUT_PRED_PATH)
    pred_df["target_month"] = pd.to_datetime(pred_df["target_month"], errors="coerce")
    latest_target = pred_df["target_month"].max()

    latest_df = pred_df[pred_df["target_month"] == latest_target].copy()
    latest_df = latest_df.sort_values("pred_prob", ascending=False)
    latest_df["risk_level"] = pd.qcut(
        latest_df["pred_prob"],
        q=5,
        labels=["Very Low", "Low", "Medium", "High", "Very High"],
        duplicates="drop",
    )
    latest_df["community_area"] = latest_df["community_area"].astype(int).astype(str)

    return {
        "target_month": latest_target.strftime("%Y-%m-01") if pd.notna(latest_target) else None,
        "data": _to_records(latest_df[["community_area", "pred_prob", "pred_label", "risk_level"]]),
    }


@app.get("/api/crime/ten-year-trend")
def ten_year_trend() -> dict[str, Any]:
    engine, table = _get_engine_and_table()
    query = text(
        f"""
        SELECT
            DATE_FORMAT(`DATE`, '%Y-%m-01') AS month,
            COUNT(*) AS crime_count
        FROM `{table}`
        WHERE `DATE` IS NOT NULL
        GROUP BY DATE_FORMAT(`DATE`, '%Y-%m-01')
        ORDER BY month
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return {"data": _to_records(df)}


@app.get("/api/crime/current-month-top10-primary-type")
def current_month_top10_primary_type() -> dict[str, Any]:
    engine, table = _get_engine_and_table()
    query = text(
        f"""
        WITH latest_month AS (
          SELECT DATE_FORMAT(MAX(`DATE`), '%Y-%m-01') AS month_start
          FROM `{table}`
          WHERE `DATE` IS NOT NULL
        )
        SELECT
          COALESCE(NULLIF(TRIM(`PRIMARY_TYPE`), ''), 'UNKNOWN') AS primary_type,
          COUNT(*) AS crime_count,
          lm.month_start AS month_start
        FROM `{table}` t
        CROSS JOIN latest_month lm
        WHERE DATE_FORMAT(t.`DATE`, '%Y-%m-01') = lm.month_start
        GROUP BY COALESCE(NULLIF(TRIM(`PRIMARY_TYPE`), ''), 'UNKNOWN'), lm.month_start
        ORDER BY crime_count DESC
        LIMIT 10
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    month_start = df["month_start"].iloc[0] if not df.empty else None
    return {"month_start": month_start, "data": _to_records(df.drop(columns=["month_start"], errors="ignore"))}


@app.get("/api/crime/raw-data")
def raw_data(limit: int = Query(default=200, ge=1, le=2000)) -> dict[str, Any]:
    engine = _get_engine()
    query = text(
        """
        SELECT
            `community_area` AS community_area,
            `month` AS month,
            `count_t1` AS count_t1,
            `arrest_rate` AS arrest_rate,
            `hardship_index` AS hardship_index,
            `spatial_lag_crime_lag1` AS spatial_lag_crime_lag1
        FROM `chicago_processed_data`
        ORDER BY `month` DESC, `community_area` ASC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"limit": limit})

    return {"limit": limit, "data": _to_records(df)}


@app.get("/api/model/metrics")
def model_metrics() -> dict[str, Any]:
    metrics_df = pd.read_csv(METRICS_PATH)
    return {"data": _to_records(metrics_df)}


@app.get("/api/model/feature-importance")
def model_feature_importance(top_n: int = Query(default=15, ge=5, le=30)) -> dict[str, Any]:
    fi_df = pd.read_csv(FEATURE_IMPORTANCE_PATH).sort_values("mean_abs_shap", ascending=False).head(top_n)
    return {"data": _to_records(fi_df)}
