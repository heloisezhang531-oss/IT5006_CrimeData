#!/usr/bin/env python3
"""Create state-month features and labels for NIBRS modeling."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

import geopandas as gpd
import libpysal
import numpy as np
import pandas as pd

FEATURE_COLS = [
    "hardship_index",
    "spatial_lag_hardship",
    "spatial_lag_crime_lag1",
    "count_lag1",
    "count_lag3",
    "count_lag6",
    "count_lag12",
    "roll_mean_3",
    "roll_mean_6",
    "roll_mean_12",
    "month_sin",
    "month_cos",
    "arrest_rate",
    "top_type_share",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="data_processed/NIBRS_panel_monthly_base.csv")
    parser.add_argument("--type-counts", default="data_processed/NIBRS_panel_monthly_type_counts.csv")
    parser.add_argument("--hardship", default="model/NIRBS/Hardship index-all states.csv")
    parser.add_argument("--geojson", default="model/NIRBS/tl_2024_us_state.zip")
    parser.add_argument("--out-data", default="model/NIRBS/NIBRS_model_dataset.csv")
    parser.add_argument("--out-meta", default="model/NIRBS/NIBRS_model_metadata.json")
    parser.add_argument(
        "--train-end-month",
        default="2024-08",
        help="Train split upper bound in YYYY-MM (based on target_month).",
    )
    parser.add_argument(
        "--val-end-month",
        default="2024-10",
        help="Validation split upper bound in YYYY-MM (based on target_month).",
    )
    return parser.parse_args()


def load_hardship(path: Path) -> pd.Series:
    hdx = pd.read_csv(path)
    hdx["State"] = hdx["State"].astype(str).str.strip().str.upper()
    hdx["Value"] = pd.to_numeric(hdx["Value"], errors="coerce")
    return hdx.set_index("State")["Value"]


def assign_split(
    target_month: pd.Series,
    train_end_month: str,
    val_end_month: str,
) -> pd.Series:
    train_end = pd.Period(train_end_month, freq="M").to_timestamp()
    val_end = pd.Period(val_end_month, freq="M").to_timestamp()
    if train_end >= val_end:
        raise ValueError("Expected train_end_month < val_end_month.")

    split = pd.Series(index=target_month.index, dtype="object")
    split[target_month <= train_end] = "train"
    split[(target_month > train_end) & (target_month <= val_end)] = "val"
    split[target_month > val_end] = "test"
    return split


def _lag_from_weights(
    month_df: pd.DataFrame,
    w: libpysal.weights.W,
    state_order: List[str],
    value_col: str,
) -> pd.Series:
    values = pd.Series(0.0, index=state_order, dtype=float)
    valid = month_df[["state_abbr", value_col]].dropna().copy()
    if not valid.empty:
        valid["state_abbr"] = valid["state_abbr"].astype(str).str.upper()
        valid = valid[valid["state_abbr"].isin(state_order)]
        values.loc[valid["state_abbr"].to_numpy()] = valid[value_col].to_numpy(dtype=float)

    lag_values = libpysal.weights.lag_spatial(w, values.to_numpy())
    lag_map = dict(zip(state_order, lag_values))
    return month_df["state_abbr"].map(lag_map).astype(float)


def _load_state_geometry(geo_path: Path) -> gpd.GeoDataFrame:
    path_str = str(geo_path)
    if geo_path.suffix.lower() == ".zip":
        return gpd.read_file(f"zip://{path_str}")
    return gpd.read_file(path_str)


def compute_state_spatial_features(df: pd.DataFrame, geo_path: Path) -> pd.DataFrame:
    print(f"Loading US state geometry: {geo_path}")
    gdf = _load_state_geometry(geo_path)

    excluded = {"AK", "HI", "PR", "GU", "VI", "AS", "MP"}
    gdf["STUSPS"] = gdf["STUSPS"].astype(str).str.upper()
    gdf = gdf[~gdf["STUSPS"].isin(excluded)].copy()
    gdf = gdf.sort_values("STUSPS").reset_index(drop=True)

    w = libpysal.weights.Queen.from_dataframe(gdf, ids="STUSPS")
    w.transform = "R"
    state_order = list(w.id_order)

    out_parts = []
    for month, month_df in df.groupby("month", sort=True):
        month_full = month_df.copy()
        month_full["state_abbr"] = month_full["state_abbr"].astype(str).str.upper()
        month_full = month_full[month_full["state_abbr"].isin(state_order)].copy()
        if month_full.empty:
            continue

        month_full["spatial_lag_hardship"] = _lag_from_weights(
            month_df=month_full,
            w=w,
            state_order=state_order,
            value_col="hardship_index",
        )
        month_full["spatial_lag_crime_lag1"] = _lag_from_weights(
            month_df=month_full,
            w=w,
            state_order=state_order,
            value_col="count_lag1",
        )
        out_parts.append(month_full)

    if not out_parts:
        raise ValueError("Spatial feature computation returned no rows.")
    return pd.concat(out_parts, ignore_index=True)


def main() -> None:
    args = parse_args()
    base_path = Path(args.base)
    type_counts_path = Path(args.type_counts)
    hardship_path = Path(args.hardship)

    for file_path in [base_path, type_counts_path, hardship_path]:
        if not file_path.exists():
            raise FileNotFoundError(f"Missing required file: {file_path}")

    base = pd.read_csv(base_path, parse_dates=["month"])
    base["state_abbr"] = base["state_abbr"].astype(str).str.upper()
    base = base.sort_values(["state_abbr", "month"]).reset_index(drop=True)

    type_counts = pd.read_csv(type_counts_path, parse_dates=["month"])
    type_counts["state_abbr"] = type_counts["state_abbr"].astype(str).str.upper()
    max_type = (
        type_counts.groupby(["state_abbr", "month"], observed=True)["type_count"]
        .max()
        .rename("top_type_count")
        .reset_index()
    )
    data = base.merge(max_type, on=["state_abbr", "month"], how="left")
    data["top_type_count"] = data["top_type_count"].fillna(0.0)

    data["top_type_share"] = 0.0
    nonzero = data["count_total"] > 0
    data.loc[nonzero, "top_type_share"] = (
        data.loc[nonzero, "top_type_count"] / data.loc[nonzero, "count_total"]
    )

    grp = data.groupby("state_abbr", observed=True)["count_total"]
    for lag in [1, 3, 6, 12]:
        data[f"count_lag{lag}"] = grp.shift(lag)
    for win in [3, 6, 12]:
        data[f"roll_mean_{win}"] = grp.transform(lambda s: s.shift(1).rolling(win, min_periods=win).mean())

    month_num = data["month"].dt.month
    data["month_sin"] = np.sin(2 * np.pi * month_num / 12)
    data["month_cos"] = np.cos(2 * np.pi * month_num / 12)

    h_map = load_hardship(hardship_path)
    data["hardship_index"] = data["state_abbr"].map(h_map)

    # Keep only rows with a real next-month target. Do not backfill the last month.
    data["count_t1"] = data.groupby("state_abbr", observed=True)["count_total"].shift(-1)
    data["target_month"] = data["month"] + pd.offsets.MonthBegin(1)
    data = data[data["count_t1"].notna()].copy()

    data["split"] = assign_split(
        target_month=data["target_month"],
        train_end_month=args.train_end_month,
        val_end_month=args.val_end_month,
    )

    if Path(args.geojson).exists():
        model_df = compute_state_spatial_features(data, Path(args.geojson))
    else:
        print("WARNING: Geo file not found, skipping spatial feature computation.")
        model_df = data.copy()
        model_df["spatial_lag_hardship"] = np.nan
        model_df["spatial_lag_crime_lag1"] = np.nan

    train_mask = model_df["split"] == "train"
    if not np.any(train_mask):
        raise ValueError("No training rows after split assignment.")
    q75_train = model_df.loc[train_mask, "count_t1"].quantile(0.75)
    model_df["label"] = (model_df["count_t1"] >= q75_train).astype(int)

    numeric_fill_cols = [
        "count_lag1",
        "count_lag3",
        "count_lag6",
        "count_lag12",
        "roll_mean_3",
        "roll_mean_6",
        "roll_mean_12",
        "spatial_lag_hardship",
        "spatial_lag_crime_lag1",
        "arrest_rate",
        "top_type_share",
    ]
    for col in numeric_fill_cols:
        if col in model_df.columns:
            model_df[col] = pd.to_numeric(model_df[col], errors="coerce").fillna(0.0)

    if "hardship_index" in model_df.columns:
        h_median = pd.to_numeric(model_df["hardship_index"], errors="coerce").median()
        fill_value = float(h_median) if np.isfinite(h_median) else 0.0
        model_df["hardship_index"] = pd.to_numeric(model_df["hardship_index"], errors="coerce").fillna(fill_value)

    keep_cols = [
        "state_abbr",
        "month",
        "target_month",
        "split",
        "count_total",
        "count_t1",
        "label",
        "count_arrest",
        "arrest_rate",
        "top_type_share",
        "hardship_index",
        "spatial_lag_hardship",
        "spatial_lag_crime_lag1",
        "count_lag1",
        "count_lag3",
        "count_lag6",
        "count_lag12",
        "roll_mean_3",
        "roll_mean_6",
        "roll_mean_12",
        "month_sin",
        "month_cos",
    ]
    model_df = model_df[keep_cols].sort_values(["state_abbr", "month"]).reset_index(drop=True)

    out_data = Path(args.out_data)
    out_meta = Path(args.out_meta)
    out_data.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)

    model_df.to_csv(out_data, index=False)

    counts = model_df.groupby("split")["label"].agg(["count", "mean"]).to_dict(orient="index")
    meta = {
        "q75_train": float(q75_train),
        "feature_columns": FEATURE_COLS,
        "split_label_distribution": counts,
        "n_rows": int(len(model_df)),
        "train_end_month": args.train_end_month,
        "val_end_month": args.val_end_month,
    }
    out_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Saved model dataset: {out_data} (rows={len(model_df)})")
    print(f"Saved metadata: {out_meta}")
    print(f"Q75_train = {q75_train:.4f}")


if __name__ == "__main__":
    main()
