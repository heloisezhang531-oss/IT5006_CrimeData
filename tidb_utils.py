"""Shared TiDB helpers for chicago_crimes model pipelines."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Tuple

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL


def _clean_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    cleaned = value.strip()
    # Vercel env values piped via stdin may accidentally persist literal "\r\n" suffixes.
    for token in ("\\r\\n", "\\n", "\\r"):
        while cleaned.endswith(token):
            cleaned = cleaned[: -len(token)].strip()
    return cleaned or None


def _resolve_ca_path(ca_path: str | None) -> str | None:
    if not ca_path:
        return None
    raw = ca_path.strip()
    if not raw:
        return None

    candidate = Path(raw)
    candidates = [
        candidate,
        Path.cwd() / candidate,
        Path(__file__).resolve().parent / candidate,
    ]
    for path in candidates:
        try:
            if path.is_file():
                return str(path.resolve())
        except Exception:
            continue
    return raw


def create_tidb_engine(env_file: str | None = None, pool_recycle: int = 3600) -> Engine:
    """Create a SQLAlchemy engine from TiDB credentials in env variables."""
    if env_file:
        load_dotenv(dotenv_path=env_file, override=False)
    else:
        load_dotenv(override=False)

    user = _clean_env("TIDB_USER")
    password = _clean_env("TIDB_PASSWORD")
    host = _clean_env("TIDB_HOST")
    port = _clean_env("TIDB_PORT")
    db_name = _clean_env("TIDB_DB_NAME") or "Chicago_data"
    ca_path = _resolve_ca_path(_clean_env("TID_CA_PATH"))

    missing = [k for k, v in {
        "TIDB_USER": user,
        "TIDB_PASSWORD": password,
        "TIDB_HOST": host,
        "TIDB_PORT": port,
    }.items() if not v]
    if missing:
        raise ValueError(f"Missing TiDB env vars: {', '.join(missing)}")

    query = {}
    if ca_path:
        query = {
            "ssl_ca": ca_path,
            "ssl_verify_cert": "true",
            "ssl_verify_identity": "true",
        }

    url = URL.create(
        drivername="mysql+pymysql",
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=db_name,
        query=query,
    )
    return create_engine(url, pool_recycle=pool_recycle)


def _validate_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Unsafe identifier: {name}")
    return name


def resolve_chicago_table_name(engine: Engine, preferred: str = "chicago_crimes") -> str:
    """Resolve usable table name from common chicago crime table variants."""
    candidates = [preferred, "chicago_crimes", "chicago_crime"]
    candidates = [c for c in candidates if c]

    with engine.connect() as conn:
        rows = conn.execute(text("SHOW TABLES")).fetchall()
    table_map = {str(r[0]).lower(): str(r[0]) for r in rows}

    for name in candidates:
        key = name.lower()
        if key in table_map:
            return _validate_identifier(table_map[key])

    raise ValueError(
        "Unable to find chicago crime table. "
        f"Tried: {', '.join(candidates)}; available: {', '.join(sorted(table_map.values()))}"
    )


def fetch_monthly_aggregates_from_tidb(
    engine: Engine,
    table_name: str,
    start_month: pd.Timestamp,
    end_month: pd.Timestamp,
    min_area: int,
    max_area: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch monthly base + type aggregates from TiDB chicago crime table."""
    table = _validate_identifier(table_name)
    start_date = pd.Timestamp(start_month).normalize()
    end_exclusive = (pd.Timestamp(end_month).normalize() + pd.offsets.MonthBegin(1))

    params = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_exclusive": end_exclusive.strftime("%Y-%m-%d"),
        "min_area": int(min_area),
        "max_area": int(max_area),
    }

    base_query = text(
        f"""
        SELECT
            CAST(`COMMUNITY_AREA` AS UNSIGNED) AS community_area,
            DATE_FORMAT(`DATE`, '%Y-%m-01') AS month,
            COUNT(*) AS count_total,
            SUM(CASE WHEN `ARREST` IN (1, TRUE, '1', 'true', 'TRUE') THEN 1 ELSE 0 END) AS count_arrest
        FROM `{table}`
        WHERE `DATE` >= :start_date
          AND `DATE` < :end_exclusive
          AND `COMMUNITY_AREA` IS NOT NULL
          AND `COMMUNITY_AREA` REGEXP '^[0-9]+$'
          AND CAST(`COMMUNITY_AREA` AS UNSIGNED) BETWEEN :min_area AND :max_area
        GROUP BY CAST(`COMMUNITY_AREA` AS UNSIGNED), DATE_FORMAT(`DATE`, '%Y-%m-01')
        """
    )

    type_query = text(
        f"""
        SELECT
            CAST(`COMMUNITY_AREA` AS UNSIGNED) AS community_area,
            DATE_FORMAT(`DATE`, '%Y-%m-01') AS month,
            COALESCE(NULLIF(TRIM(`PRIMARY_TYPE`), ''), 'UNKNOWN') AS primary_type,
            COUNT(*) AS type_count
        FROM `{table}`
        WHERE `DATE` >= :start_date
          AND `DATE` < :end_exclusive
          AND `COMMUNITY_AREA` IS NOT NULL
          AND `COMMUNITY_AREA` REGEXP '^[0-9]+$'
          AND CAST(`COMMUNITY_AREA` AS UNSIGNED) BETWEEN :min_area AND :max_area
        GROUP BY
            CAST(`COMMUNITY_AREA` AS UNSIGNED),
            DATE_FORMAT(`DATE`, '%Y-%m-01'),
            COALESCE(NULLIF(TRIM(`PRIMARY_TYPE`), ''), 'UNKNOWN')
        """
    )

    with engine.connect() as conn:
        base_df = pd.read_sql(base_query, conn, params=params)
        type_df = pd.read_sql(type_query, conn, params=params)

    for df in [base_df, type_df]:
        if df.empty:
            continue
        df["community_area"] = pd.to_numeric(df["community_area"], errors="coerce").astype(int)
        df["month"] = pd.to_datetime(df["month"], errors="coerce").dt.to_period("M").dt.to_timestamp()

    if not base_df.empty:
        base_df["count_total"] = pd.to_numeric(base_df["count_total"], errors="coerce").fillna(0).astype(int)
        base_df["count_arrest"] = pd.to_numeric(base_df["count_arrest"], errors="coerce").fillna(0).astype(int)

    if not type_df.empty:
        type_df["primary_type"] = type_df["primary_type"].fillna("UNKNOWN").astype(str)
        type_df["type_count"] = pd.to_numeric(type_df["type_count"], errors="coerce").fillna(0).astype(int)

    return base_df, type_df


def fetch_crime_points_from_tidb(
    engine: Engine,
    table_name: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch raw crime points with valid date/lat/lon from TiDB."""
    table = _validate_identifier(table_name)
    query = text(
        f"""
        SELECT
            `DATE` AS event_date,
            `LATITUDE` AS latitude,
            `LONGITUDE` AS longitude
        FROM `{table}`
        WHERE `DATE` >= :start_date
          AND `DATE` <= :end_date
          AND `LATITUDE` IS NOT NULL
          AND `LONGITUDE` IS NOT NULL
          AND `LATITUDE` REGEXP '^-?[0-9]+(\\\\.[0-9]+)?$'
          AND `LONGITUDE` REGEXP '^-?[0-9]+(\\\\.[0-9]+)?$'
        """
    )

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"start_date": start_date, "end_date": end_date})

    if df.empty:
        return df

    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df.dropna(subset=["event_date", "latitude", "longitude"]).reset_index(drop=True)
    return df
