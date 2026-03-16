#!/usr/bin/env python3
"""Reproduce the STCP paper pipeline on Chicago crime data from TiDB.

Paper:
Catlett et al., "Spatio-temporal crime predictions in smart cities: A data-driven approach and experiments"
(Pervasive and Mobile Computing, 2019)

Pipeline implemented here:
1) Detect crime dense regions (hotspots) via weighted DBSCAN on train data.
2) Build weekly crime-count time series for whole area + top-K hotspot regions.
3) Train seasonal ARIMA (SARIMA) predictors per region.
4) Evaluate on holdout years with MAE, MAPE, ME, RMSE.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull, QhullError
from sklearn.cluster import DBSCAN
from sklearn.neighbors import BallTree
from statsmodels.tsa.statespace.sarimax import SARIMAX

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tidb_utils import (  # noqa: E402
    create_tidb_engine,
    fetch_crime_points_from_tidb,
    resolve_chicago_table_name,
)

EARTH_RADIUS_M = 6_371_000.0


@dataclass
class SearchConfig:
    max_p: int
    max_q: int
    max_P: int
    max_Q: int
    d: int
    D: int
    season_period: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--tidb-table", default="chicago_crimes")
    parser.add_argument("--start-date", default="2015-01-01")
    parser.add_argument("--end-date", default="2025-12-31")
    parser.add_argument(
        "--train-end-date",
        default="2022-12-31",
        help="Train period end date (inclusive). Test starts the next day.",
    )
    parser.add_argument(
        "--eps-meters",
        type=float,
        default=83.25,
        help="DBSCAN epsilon in meters (paper CHI value: 83.25m).",
    )
    parser.add_argument("--min-samples", type=int, default=20, help="DBSCAN min samples.")
    parser.add_argument(
        "--decay-factor",
        type=float,
        default=0.998,
        help="Temporal decay factor for weighted DBSCAN.",
    )
    parser.add_argument("--top-k", type=int, default=3, help="Number of largest dense regions to model.")
    parser.add_argument("--season-period", type=int, default=52, help="Seasonality period for SARIMA.")
    parser.add_argument("--max-p", type=int, default=2)
    parser.add_argument("--max-q", type=int, default=2)
    parser.add_argument("--max-P", type=int, default=1)
    parser.add_argument("--max-Q", type=int, default=1)
    parser.add_argument("--d", type=int, default=1)
    parser.add_argument("--D", type=int, default=1)
    parser.add_argument("--output-dir", default="experiment/paper_stcp_reproduction")
    return parser.parse_args()


def _to_radians(df: pd.DataFrame) -> np.ndarray:
    return np.radians(df[["latitude", "longitude"]].to_numpy(dtype=float))


def _compute_decay_weights(dates: pd.Series, decay_factor: float) -> np.ndarray:
    t_max = dates.max()
    weeks_diff = (t_max - dates).dt.total_seconds().to_numpy() / (7 * 24 * 3600)
    weeks_diff = np.clip(weeks_diff, 0, None)
    return np.power(decay_factor, weeks_diff)


def _convex_hull_area_km2(lat_lon: np.ndarray) -> float:
    if lat_lon.shape[0] < 3:
        return 0.0
    lat_rad = np.radians(lat_lon[:, 0])
    lon_rad = np.radians(lat_lon[:, 1])
    lat0 = np.mean(lat_rad)
    x = EARTH_RADIUS_M * lon_rad * np.cos(lat0)
    y = EARTH_RADIUS_M * lat_rad
    pts = np.column_stack([x, y])
    try:
        hull = ConvexHull(pts)
        return float(hull.volume / 1_000_000.0)
    except QhullError:
        return 0.0


def detect_crime_dense_regions(
    train_df: pd.DataFrame,
    eps_meters: float,
    min_samples: int,
    decay_factor: float,
) -> Tuple[pd.DataFrame, float]:
    coords_rad = _to_radians(train_df)
    weights = _compute_decay_weights(train_df["event_date"], decay_factor)
    eps_rad = eps_meters / EARTH_RADIUS_M
    dbscan = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine", algorithm="ball_tree")
    labels = dbscan.fit_predict(coords_rad, sample_weight=weights)
    out = train_df.copy()
    out["cluster_label"] = labels
    return out, eps_rad


def assign_points_to_regions(
    all_df: pd.DataFrame,
    train_cluster_df: pd.DataFrame,
    top_labels: List[int],
    eps_rad: float,
) -> pd.Series:
    all_coords_rad = _to_radians(all_df)
    best_dist = np.full(len(all_df), np.inf, dtype=float)
    best_label = np.full(len(all_df), -1, dtype=int)

    for label in top_labels:
        cluster_points = train_cluster_df[train_cluster_df["cluster_label"] == label][["latitude", "longitude"]]
        if cluster_points.empty:
            continue
        tree = BallTree(np.radians(cluster_points.to_numpy(dtype=float)), metric="haversine")
        dist, _ = tree.query(all_coords_rad, k=1)
        dist = dist[:, 0]
        update_mask = dist < best_dist
        best_dist[update_mask] = dist[update_mask]
        best_label[update_mask] = label

    best_label[best_dist > eps_rad] = -1
    return pd.Series(best_label, index=all_df.index, name="assigned_region")


def build_weekly_series(
    df: pd.DataFrame,
    mask: pd.Series,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.Series:
    weekly = (
        df.loc[mask]
        .set_index("event_date")
        .resample("W-SUN")
        .size()
        .rename("count")
    )
    full_idx = pd.date_range(start=start_date, end=end_date, freq="W-SUN")
    return weekly.reindex(full_idx, fill_value=0).astype(float)


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = y_true.copy()
    nz = denom != 0
    if not np.any(nz):
        return float("nan")
    return float(np.mean(np.abs((y_true[nz] - y_pred[nz]) / denom[nz])) * 100.0)


def calc_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    err = y_true - y_pred
    return {
        "MAE": float(np.mean(np.abs(err))),
        "MAPE": mape(y_true, y_pred),
        "ME": float(np.mean(err)),
        "RMSE": float(np.sqrt(np.mean(np.square(err)))),
    }


def fit_best_sarima(series_train: pd.Series, cfg: SearchConfig):
    best_fit = None
    best_order = None
    best_seasonal_order = None
    best_aic = np.inf

    y = series_train.astype(float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p in range(cfg.max_p + 1):
            for q in range(cfg.max_q + 1):
                for P in range(cfg.max_P + 1):
                    for Q in range(cfg.max_Q + 1):
                        order = (p, cfg.d, q)
                        seasonal_order = (P, cfg.D, Q, cfg.season_period)
                        try:
                            model = SARIMAX(
                                y,
                                order=order,
                                seasonal_order=seasonal_order,
                                trend="c",
                                enforce_stationarity=False,
                                enforce_invertibility=False,
                            )
                            fit = model.fit(disp=False)
                            if np.isfinite(fit.aic) and fit.aic < best_aic:
                                best_aic = float(fit.aic)
                                best_fit = fit
                                best_order = order
                                best_seasonal_order = seasonal_order
                        except Exception:
                            continue

    if best_fit is None:
        raise RuntimeError("SARIMA search failed: no valid model configuration.")
    return best_fit, best_order, best_seasonal_order, best_aic


def evaluate_series(
    name: str,
    series: pd.Series,
    train_end_date: pd.Timestamp,
    cfg: SearchConfig,
) -> Tuple[Dict[str, object], pd.DataFrame, pd.DataFrame]:
    train = series[series.index <= train_end_date]
    test = series[series.index > train_end_date]
    if train.empty or test.empty:
        raise ValueError(f"{name}: train/test split is empty.")

    fit, order, seasonal_order, aic = fit_best_sarima(train, cfg)
    pred = fit.get_forecast(steps=len(test)).predicted_mean
    pred = pd.Series(np.clip(pred.to_numpy(dtype=float), 0, None), index=test.index, name="pred")

    overall = calc_metrics(test.to_numpy(dtype=float), pred.to_numpy(dtype=float))
    overall_row = {"series": name, **overall}

    yearly_rows = []
    for year in sorted(test.index.year.unique()):
        mask = test.index.year == year
        ym = calc_metrics(test.loc[mask].to_numpy(dtype=float), pred.loc[mask].to_numpy(dtype=float))
        yearly_rows.append({"series": name, "year": int(year), **ym})

    pred_df = pd.DataFrame(
        {
            "week_end": test.index,
            "series": name,
            "observed": test.to_numpy(dtype=float),
            "predicted": pred.to_numpy(dtype=float),
        }
    )
    model_info = {
        "series": name,
        "order": order,
        "seasonal_order": seasonal_order,
        "aic": aic,
        "train_points": int(len(train)),
        "test_points": int(len(test)),
    }
    return model_info, pred_df, pd.DataFrame([overall_row]), pd.DataFrame(yearly_rows)


def plot_predictions(pred_df: pd.DataFrame, out_path: Path) -> None:
    series_names = pred_df["series"].drop_duplicates().tolist()
    n = len(series_names)
    fig, axes = plt.subplots(n, 1, figsize=(12, 3.3 * n), sharex=False)
    if n == 1:
        axes = [axes]

    for ax, name in zip(axes, series_names):
        d = pred_df[pred_df["series"] == name].copy()
        d = d.sort_values("week_end")
        ax.plot(d["week_end"], d["observed"], label="observed", linewidth=1.6)
        ax.plot(d["week_end"], d["predicted"], label="forecast", linewidth=1.6)
        ax.set_title(name)
        ax.grid(alpha=0.3)
        ax.legend(loc="upper right")

    plt.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    start_date = pd.Timestamp(args.start_date)
    end_date = pd.Timestamp(args.end_date)
    train_end_date = pd.Timestamp(args.train_end_date)
    if not (start_date < train_end_date < end_date):
        raise ValueError("Expected start_date < train_end_date < end_date.")

    cfg = SearchConfig(
        max_p=args.max_p,
        max_q=args.max_q,
        max_P=args.max_P,
        max_Q=args.max_Q,
        d=args.d,
        D=args.D,
        season_period=args.season_period,
    )

    print("Loading crime points from TiDB...")
    engine = create_tidb_engine(env_file=args.env_file)
    table_name = resolve_chicago_table_name(engine, preferred=args.tidb_table)
    all_df = fetch_crime_points_from_tidb(
        engine=engine,
        table_name=table_name,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    if all_df.empty:
        raise RuntimeError("No rows fetched from TiDB for the requested date range.")

    all_df = all_df.sort_values("event_date").reset_index(drop=True)
    train_df = all_df[all_df["event_date"] <= train_end_date].copy()
    if train_df.empty:
        raise RuntimeError("Training set is empty after date filtering.")

    print("Detecting crime dense regions with weighted DBSCAN...")
    train_cluster_df, eps_rad = detect_crime_dense_regions(
        train_df=train_df,
        eps_meters=args.eps_meters,
        min_samples=args.min_samples,
        decay_factor=args.decay_factor,
    )

    cluster_stats = (
        train_cluster_df[train_cluster_df["cluster_label"] >= 0]
        .groupby("cluster_label")
        .size()
        .reset_index(name="crime_count_train")
        .sort_values("crime_count_train", ascending=False)
        .reset_index(drop=True)
    )
    if cluster_stats.empty:
        raise RuntimeError("DBSCAN did not detect any non-noise cluster. Try increasing eps_meters.")

    top_stats = cluster_stats.head(args.top_k).copy()
    top_labels = top_stats["cluster_label"].astype(int).tolist()

    print("Assigning all points to discovered top regions...")
    all_df["assigned_region"] = assign_points_to_regions(
        all_df=all_df,
        train_cluster_df=train_cluster_df,
        top_labels=top_labels,
        eps_rad=eps_rad,
    )

    whole_area_km2 = _convex_hull_area_km2(train_df[["latitude", "longitude"]].to_numpy(dtype=float))
    region_rows = []
    for rank, label in enumerate(top_labels, start=1):
        reg_train = train_cluster_df[train_cluster_df["cluster_label"] == label]
        reg_area_km2 = _convex_hull_area_km2(reg_train[["latitude", "longitude"]].to_numpy(dtype=float))
        reg_count = int(len(reg_train))
        region_rows.append(
            {
                "rank": rank,
                "cluster_label": int(label),
                "crime_count_train": reg_count,
                "crime_pct_train": (reg_count / len(train_df)) * 100.0,
                "region_area_km2": reg_area_km2,
                "region_area_pct_train_hull": (reg_area_km2 / whole_area_km2 * 100.0) if whole_area_km2 > 0 else np.nan,
                "centroid_lat": float(reg_train["latitude"].mean()),
                "centroid_lon": float(reg_train["longitude"].mean()),
            }
        )
    region_summary_df = pd.DataFrame(region_rows)
    region_summary_df.to_csv(output_dir / "region_summary.csv", index=False)

    print("Building weekly time series and fitting SARIMA models...")
    series_map: Dict[str, pd.Series] = {
        "Area": build_weekly_series(all_df, pd.Series(True, index=all_df.index), start_date, end_date),
    }
    for i, label in enumerate(top_labels, start=1):
        mask = all_df["assigned_region"] == label
        series_map[f"CDR{i}"] = build_weekly_series(all_df, mask, start_date, end_date)

    model_infos = []
    pred_parts = []
    overall_parts = []
    yearly_parts = []

    for name, series in series_map.items():
        print(f"  Fitting {name} ...")
        info, pred_df, overall_df, yearly_df = evaluate_series(
            name=name,
            series=series,
            train_end_date=train_end_date,
            cfg=cfg,
        )
        model_infos.append(info)
        pred_parts.append(pred_df)
        overall_parts.append(overall_df)
        yearly_parts.append(yearly_df)

    pred_all = pd.concat(pred_parts, ignore_index=True)
    overall_all = pd.concat(overall_parts, ignore_index=True)
    yearly_all = pd.concat(yearly_parts, ignore_index=True).sort_values(["series", "year"]).reset_index(drop=True)

    pred_all.to_csv(output_dir / "weekly_test_predictions.csv", index=False)
    overall_all.to_csv(output_dir / "test_metrics_overall.csv", index=False)
    yearly_all.to_csv(output_dir / "test_metrics_by_year.csv", index=False)
    (output_dir / "model_configs.json").write_text(json.dumps(model_infos, indent=2), encoding="utf-8")
    plot_predictions(pred_all, output_dir / "forecast_vs_observed.png")

    summary_lines = [
        "# STCP Paper Reproduction (Chicago / TiDB)",
        "",
        "## Configuration",
        f"- Data range: {args.start_date} to {args.end_date}",
        f"- Train end date: {args.train_end_date}",
        f"- DBSCAN eps(m): {args.eps_meters}, min_samples: {args.min_samples}, decay_factor: {args.decay_factor}",
        f"- SARIMA search: max_p={args.max_p}, max_q={args.max_q}, max_P={args.max_P}, max_Q={args.max_Q}, d={args.d}, D={args.D}, m={args.season_period}",
        "",
        "## Region Summary",
        region_summary_df.to_string(index=False),
        "",
        "## Overall Test Metrics",
        overall_all.to_string(index=False),
        "",
        "## Yearly Test Metrics",
        yearly_all.to_string(index=False),
        "",
        "## Notes",
        "- This reproduces the paper's methodology (weighted DBSCAN + SARIMA) on available TiDB Chicago data.",
        "- Exact numeric parity with the paper is not expected because the paper used a specific bounded CHI area and 2001-2016 window.",
        "",
    ]
    (output_dir / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"Saved reproduction outputs to: {output_dir}")


if __name__ == "__main__":
    main()
