#!/usr/bin/env python3
"""Create model features and labels at community_area-month level."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import libpysal
import numpy as np
import pandas as pd
import geopandas as gpd
from libpysal.weights import Queen

FEATURE_COLS = [
    "hardship_index",
    "spatial_lag_hardship",     # spatial lag of hardship index
    "count_lag1",
    "spatial_lag_crime_lag1",  # spatial lag of crime count
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
    parser.add_argument("--base", default="data_processed/panel_monthly_base.csv")
    parser.add_argument("--type-counts", default="data_processed/panel_monthly_type_counts.csv")
    parser.add_argument("--hardship", default="Hardship Index of Chicago.csv")
    parser.add_argument("--geojson", default="Boundaries_-_Community_Areas_20260312.geojson")   # GeoJSON file for potential future use (e.g., spatial features)
    parser.add_argument("--out-data", default="data_processed/geo_model_dataset.csv")
    parser.add_argument("--out-meta", default="data_processed/geo_model_metadata.json")
    return parser.parse_args()


def load_hardship(path: Path) -> Dict[str, pd.Series]:
    hdx = pd.read_csv(path)
    hdx = hdx[pd.to_numeric(hdx["GEOID"], errors="coerce").notna()].copy()
    hdx["community_area"] = hdx["GEOID"].astype(int)
    hdx["HDX_2015-2019"] = pd.to_numeric(hdx["HDX_2015-2019"], errors="coerce")
    hdx["HDX_2020-2024"] = pd.to_numeric(hdx["HDX_2020-2024"], errors="coerce")

    m15 = hdx.set_index("community_area")["HDX_2015-2019"]
    m20 = hdx.set_index("community_area")["HDX_2020-2024"]
    return {"2015_2019": m15, "2020_2024": m20}


def assign_split(target_month: pd.Series) -> pd.Series:
    split = pd.Series(index=target_month.index, dtype="object")
    split[(target_month >= pd.Timestamp("2015-01-01")) & (target_month <= pd.Timestamp("2022-12-01"))] = "train"
    split[(target_month >= pd.Timestamp("2023-01-01")) & (target_month <= pd.Timestamp("2024-12-01"))] = "val"
    split[(target_month >= pd.Timestamp("2025-01-01")) & (target_month <= pd.Timestamp("2025-12-01"))] = "test"
    return split

def compute_spatial_features(df: pd.DataFrame, geo_path: Path) -> pd.DataFrame:

    print(f"loading Geo data: {geo_path}")
    

    gdf = gpd.read_file(geo_path)
  
    gdf["community_area"] = gdf["area_numbe"].astype(int)
    gdf = gdf.sort_values("community_area").reset_index(drop=True)

    w = libpysal.weights.Queen.from_dataframe(gdf)
    w.transform = 'R'  # 行归一化：计算出的滞后项即为邻居的平均值

    # 准备存储空间特征
    all_spatial_dfs = []

    # 按月份循环，计算每个时间截面的空间滞后
    for month, month_df in df.groupby("month"):
        month_full = month_df.copy().sort_values("community_area")
        
        # 确保该月的社区列表与地理数据一致
        if len(month_full) != len(gdf):
            # 如果某些月数据缺失社区，可以 merge 补全，这里假设数据是完整的
            pass
            
        # 修复 2: 使用 libpysal.weights.lag_spatial 替代 w.lag()
        # 计算 Hardship Index 的空间滞后（邻居的平均贫困程度）
        month_full["spatial_lag_hardship"] = libpysal.weights.lag_spatial(w, month_full["hardship_index"].values)
        
        # 计算犯罪数量的空间滞后（邻居上个月的犯罪水平）
        month_full["spatial_lag_crime_lag1"] = libpysal.weights.lag_spatial(w, month_full["count_lag1"].values)
        
        all_spatial_dfs.append(month_full)

    return pd.concat(all_spatial_dfs).reset_index(drop=True)


def main() -> None:
    args = parse_args()
    base_path = Path(args.base)
    type_counts_path = Path(args.type_counts)
    hardship_path = Path(args.hardship)

    for file_path in [base_path, type_counts_path, hardship_path]:
        if not file_path.exists():
            raise FileNotFoundError(f"Missing required file: {file_path}")

    base = pd.read_csv(base_path, parse_dates=["month"])
    base = base.sort_values(["community_area", "month"]).reset_index(drop=True)

    type_counts = pd.read_csv(type_counts_path, parse_dates=["month"])
    max_type = (
        type_counts.groupby(["community_area", "month"], observed=True)["type_count"]
        .max()
        .rename("top_type_count")
        .reset_index()
    )
    data = base.merge(max_type, on=["community_area", "month"], how="left")
    data["top_type_count"] = data["top_type_count"].fillna(0)

    data["top_type_share"] = 0.0
    nonzero = data["count_total"] > 0
    data.loc[nonzero, "top_type_share"] = data.loc[nonzero, "top_type_count"] / data.loc[nonzero, "count_total"]

    grp = data.groupby("community_area", observed=True)["count_total"]
    for lag in [1, 3, 6, 12]:
        data[f"count_lag{lag}"] = grp.shift(lag)
    for win in [3, 6, 12]:
        data[f"roll_mean_{win}"] = grp.transform(lambda s: s.shift(1).rolling(win, min_periods=win).mean())

    month_num = data["month"].dt.month
    data["month_sin"] = np.sin(2 * np.pi * month_num / 12)
    data["month_cos"] = np.cos(2 * np.pi * month_num / 12)

    h_maps = load_hardship(hardship_path)
    year = data["month"].dt.year
    data["hardship_index"] = np.where(
        year <= 2019,
        data["community_area"].map(h_maps["2015_2019"]),
        data["community_area"].map(h_maps["2020_2024"]),
    )

    data["count_t1"] = data.groupby("community_area", observed=True)["count_total"].shift(-1)
    data["target_month"] = data["month"] + pd.offsets.MonthBegin(1)
    data["split"] = assign_split(data["target_month"])

    model_df = data[data["split"].notna()].copy()
    model_df = model_df[model_df["count_t1"].notna()].copy()

    # 4. 空间特征计算 (核心新增)
    if Path(args.geojson).exists():
        model_df = compute_spatial_features(model_df, Path(args.geojson))
    else:
        print("WARNING: GeoJSON file not found, skipping spatial feature computation.")

    q75_train = model_df.loc[model_df["split"] == "train", "count_t1"].quantile(0.75)
    model_df["label"] = (model_df["count_t1"] >= q75_train).astype(int)

    keep_cols = [
        "community_area",
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
        "spatial_lag_hardship",     # spatial lag of hardship index
        "spatial_lag_crime_lag1",  # spatial lag of crime count 
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

    model_df = model_df[keep_cols].sort_values(["community_area", "month"]).reset_index(drop=True)

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
    }
    out_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Saved model dataset: {out_data} (rows={len(model_df)})")
    print(f"Saved metadata: {out_meta}")
    print(f"Q75_train = {q75_train:.4f}")


if __name__ == "__main__":
    main()
