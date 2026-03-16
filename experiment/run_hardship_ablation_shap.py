#!/usr/bin/env python3
"""Run hardship_index ablation and global SHAP analysis.

This script reproduces the current model pipeline using data from `data/`,
then compares model performance with and without `hardship_index`.
Finally, it runs a global SHAP analysis on the best model under the
`with_hardship` setting.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Tuple

import joblib
import matplotlib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tidb_utils import (  # noqa: E402
    create_tidb_engine,
    fetch_monthly_aggregates_from_tidb,
    resolve_chicago_table_name,
)


ALL_FEATURE_COLS = [
    "hardship_index",
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

ABLATION_FEATURES = {
    "with_hardship": ALL_FEATURE_COLS,
    "without_hardship": [c for c in ALL_FEATURE_COLS if c != "hardship_index"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--crime-source",
        choices=["tidb", "csv"],
        default="tidb",
        help="Crime data source. hardship index is always loaded from local CSV.",
    )
    parser.add_argument(
        "--crime-files",
        nargs="+",
        default=["data/crimes_2015_2024.csv", "data/crimes_2025_2026.csv"],
        help="Input crime CSV files (used when --crime-source=csv).",
    )
    parser.add_argument(
        "--tidb-table",
        default="chicago_crimes",
        help="TiDB source table name (used when --crime-source=tidb).",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file containing TiDB credentials.",
    )
    parser.add_argument(
        "--hardship",
        default="data/Hardship_Index_of_Chicago.csv",
        help="Hardship index CSV path.",
    )
    parser.add_argument(
        "--output-dir",
        default="experiment",
        help="Root output directory for experiment artifacts.",
    )
    parser.add_argument("--start-month", default="2015-01", help="Start month (YYYY-MM).")
    parser.add_argument("--end-month", default="2025-12", help="End month (YYYY-MM).")
    parser.add_argument("--min-area", type=int, default=1)
    parser.add_argument("--max-area", type=int, default=77)
    parser.add_argument("--chunksize", type=int, default=400_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--shap-background-size",
        type=int,
        default=1000,
        help="Max background samples for SHAP.",
    )
    parser.add_argument(
        "--shap-explain-size",
        type=int,
        default=0,
        help="Max explained test samples for SHAP (0 means all).",
    )
    return parser.parse_args()


def to_bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"1", "true", "t", "yes", "y"})
        .astype(int)
    )


def iterate_chunks(file_path: Path, chunksize: int) -> Iterable[pd.DataFrame]:
    usecols = ["date", "community_area", "arrest", "primary_type"]
    return pd.read_csv(file_path, usecols=usecols, chunksize=chunksize)


def build_aggregates(
    files: Iterable[Path],
    start_month: pd.Timestamp,
    end_month: pd.Timestamp,
    min_area: int,
    max_area: int,
    chunksize: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    base_acc: Dict[Tuple[int, pd.Timestamp], List[int]] = defaultdict(lambda: [0, 0])
    type_acc: Dict[Tuple[int, pd.Timestamp, str], int] = defaultdict(int)

    for file_path in files:
        print(f"Processing crime file: {file_path}")
        for chunk in iterate_chunks(file_path, chunksize):
            chunk["community_area"] = pd.to_numeric(chunk["community_area"], errors="coerce")
            chunk = chunk.dropna(subset=["community_area", "date"])
            chunk["community_area"] = chunk["community_area"].astype(int)
            chunk = chunk[(chunk["community_area"] >= min_area) & (chunk["community_area"] <= max_area)]

            chunk["month"] = pd.to_datetime(chunk["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
            chunk = chunk.dropna(subset=["month"])
            chunk = chunk[(chunk["month"] >= start_month) & (chunk["month"] <= end_month)]
            if chunk.empty:
                continue

            chunk["arrest_num"] = to_bool_series(chunk["arrest"])
            chunk["primary_type"] = chunk["primary_type"].fillna("UNKNOWN").astype(str)

            grouped = (
                chunk.groupby(["community_area", "month"], observed=True)
                .agg(count_total=("date", "size"), count_arrest=("arrest_num", "sum"))
                .reset_index()
            )
            for row in grouped.itertuples(index=False):
                key = (int(row.community_area), row.month)
                base_acc[key][0] += int(row.count_total)
                base_acc[key][1] += int(row.count_arrest)

            grouped_type = (
                chunk.groupby(["community_area", "month", "primary_type"], observed=True)
                .size()
                .reset_index(name="type_count")
            )
            for row in grouped_type.itertuples(index=False):
                key = (int(row.community_area), row.month, row.primary_type)
                type_acc[key] += int(row.type_count)

    base_df = pd.DataFrame(
        [
            {
                "community_area": area,
                "month": month,
                "count_total": vals[0],
                "count_arrest": vals[1],
            }
            for (area, month), vals in base_acc.items()
        ]
    )
    type_df = pd.DataFrame(
        [
            {
                "community_area": area,
                "month": month,
                "primary_type": ptype,
                "type_count": cnt,
            }
            for (area, month, ptype), cnt in type_acc.items()
        ]
    )
    return base_df, type_df


def build_panel(
    files: Iterable[Path],
    out_base: Path,
    out_type_counts: Path,
    start_month: pd.Timestamp,
    end_month: pd.Timestamp,
    min_area: int,
    max_area: int,
    chunksize: int,
) -> None:
    base_df, type_df = build_aggregates(
        files=files,
        start_month=start_month,
        end_month=end_month,
        min_area=min_area,
        max_area=max_area,
        chunksize=chunksize,
    )

    month_range = pd.date_range(start_month, end_month, freq="MS")
    full_index = pd.MultiIndex.from_product(
        [range(min_area, max_area + 1), month_range],
        names=["community_area", "month"],
    )
    full_df = full_index.to_frame(index=False)

    panel = full_df.merge(base_df, on=["community_area", "month"], how="left")
    panel["count_total"] = panel["count_total"].fillna(0).astype(int)
    panel["count_arrest"] = panel["count_arrest"].fillna(0).astype(int)
    panel["arrest_rate"] = 0.0
    nonzero = panel["count_total"] > 0
    panel.loc[nonzero, "arrest_rate"] = panel.loc[nonzero, "count_arrest"] / panel.loc[nonzero, "count_total"]

    panel = panel.sort_values(["community_area", "month"]).reset_index(drop=True)
    type_df = type_df.sort_values(["community_area", "month", "primary_type"]).reset_index(drop=True)

    out_base.parent.mkdir(parents=True, exist_ok=True)
    out_type_counts.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out_base, index=False)
    type_df.to_csv(out_type_counts, index=False)
    print(f"Saved base panel: {out_base} (rows={len(panel)})")
    print(f"Saved type counts: {out_type_counts} (rows={len(type_df)})")


def load_hardship(path: Path) -> Dict[str, pd.Series]:
    hdx = pd.read_csv(path)
    hdx = hdx[pd.to_numeric(hdx["GEOID"], errors="coerce").notna()].copy()
    hdx["community_area"] = hdx["GEOID"].astype(int)
    hdx["HDX_2015-2019"] = pd.to_numeric(hdx["HDX_2015-2019"], errors="coerce")
    hdx["HDX_2020-2024"] = pd.to_numeric(hdx["HDX_2020-2024"], errors="coerce")
    return {
        "2015_2019": hdx.set_index("community_area")["HDX_2015-2019"],
        "2020_2024": hdx.set_index("community_area")["HDX_2020-2024"],
    }


def assign_split(target_month: pd.Series) -> pd.Series:
    split = pd.Series(index=target_month.index, dtype="object")
    split[(target_month >= pd.Timestamp("2015-01-01")) & (target_month <= pd.Timestamp("2022-12-01"))] = "train"
    split[(target_month >= pd.Timestamp("2023-01-01")) & (target_month <= pd.Timestamp("2024-12-01"))] = "val"
    split[(target_month >= pd.Timestamp("2025-01-01")) & (target_month <= pd.Timestamp("2025-12-01"))] = "test"
    return split


def make_model_dataset(base_path: Path, type_counts_path: Path, hardship_path: Path, out_data: Path, out_meta: Path) -> None:
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

    out_data.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)
    model_df.to_csv(out_data, index=False)

    counts = model_df.groupby("split")["label"].agg(["count", "mean"]).to_dict(orient="index")
    meta = {
        "q75_train": float(q75_train),
        "feature_columns": ALL_FEATURE_COLS,
        "split_label_distribution": counts,
        "n_rows": int(len(model_df)),
    }
    out_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Saved model dataset: {out_data} (rows={len(model_df)})")
    print(f"Saved metadata: {out_meta}")


def metric_bundle(y_true: np.ndarray, prob: np.ndarray, threshold: float) -> Dict[str, float]:
    pred = (prob >= threshold).astype(int)
    return {
        "roc_auc": safe_roc_auc(y_true, prob),
        "pr_auc": float(average_precision_score(y_true, prob)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, pred)),
    }


def pick_best_threshold(y_true: np.ndarray, prob: np.ndarray) -> float:
    thresholds = np.linspace(0.05, 0.95, 181)
    if np.unique(y_true).size < 2:
        best_threshold = 0.5
        best_acc = -1.0
        for t in thresholds:
            acc = accuracy_score(y_true, (prob >= t).astype(int))
            if (acc > best_acc) or (acc == best_acc and t > best_threshold):
                best_acc = acc
                best_threshold = float(t)
        return best_threshold

    best_threshold = 0.5
    best_f1 = -1.0
    for t in thresholds:
        f1 = f1_score(y_true, (prob >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = float(t)
    return best_threshold


def safe_roc_auc(y_true: np.ndarray, prob: np.ndarray) -> float:
    if np.unique(y_true).size < 2:
        return float("nan")
    return float(roc_auc_score(y_true, prob))


def iter_param_grid(grid: Dict[str, Iterable]) -> Iterable[Dict[str, object]]:
    keys = list(grid.keys())
    values = [list(grid[k]) for k in keys]
    for combo in itertools.product(*values):
        yield dict(zip(keys, combo))


def build_lr(params: Dict[str, object], seed: int) -> Pipeline:
    clf = LogisticRegression(
        random_state=seed,
        max_iter=2000,
        solver="liblinear",
        class_weight="balanced",
        **params,
    )
    return Pipeline([("scaler", StandardScaler()), ("clf", clf)])


def build_rf(params: Dict[str, object], seed: int) -> RandomForestClassifier:
    return RandomForestClassifier(
        random_state=seed,
        n_jobs=-1,
        class_weight="balanced_subsample",
        **params,
    )


def build_xgb(params: Dict[str, object], seed: int, scale_pos_weight: float) -> XGBClassifier:
    return XGBClassifier(
        random_state=seed,
        objective="binary:logistic",
        tree_method="hist",
        eval_metric="auc",
        n_jobs=-1,
        scale_pos_weight=scale_pos_weight,
        **params,
    )


def build_model_specs(seed: int, scale_pos_weight: float) -> Dict[str, Dict[str, object]]:
    return {
        "logistic_regression": {
            "builder": lambda p: build_lr(p, seed),
            "params": {"C": [0.01, 0.05, 0.1, 0.5, 1.0, 2.0]},
        },
        "random_forest": {
            "builder": lambda p: build_rf(p, seed),
            "params": {
                "n_estimators": [300, 500],
                "max_depth": [6, 10, None],
                "min_samples_leaf": [1, 5],
                "max_features": ["sqrt", 0.7],
            },
        },
        "xgboost": {
            "builder": lambda p: build_xgb(p, seed, scale_pos_weight),
            "params": {
                "n_estimators": [300],
                "max_depth": [3, 5],
                "learning_rate": [0.05, 0.1],
                "subsample": [0.8, 1.0],
                "colsample_bytree": [0.8, 1.0],
                "reg_lambda": [1.0, 5.0],
            },
        },
    }


def _class_weight_ratio(y: np.ndarray) -> float:
    pos = int(y.sum())
    neg = int(len(y) - pos)
    return (neg / pos) if pos > 0 else 1.0


def run_ablation_setting(
    df: pd.DataFrame,
    setting: str,
    feature_cols: List[str],
    seed: int,
    setting_model_dir: Path,
    reports_dir: Path,
) -> pd.DataFrame:
    model_df = df.dropna(subset=feature_cols + ["label"]).copy()

    train_df = model_df[model_df["split"] == "train"].copy()
    val_df = model_df[model_df["split"] == "val"].copy()
    test_df = model_df[model_df["split"] == "test"].copy()
    train_val_df = model_df[model_df["split"].isin(["train", "val"])].copy()

    X_train = train_df[feature_cols].to_numpy(dtype=float)
    y_train = train_df["label"].to_numpy(dtype=int)
    X_val = val_df[feature_cols].to_numpy(dtype=float)
    y_val = val_df["label"].to_numpy(dtype=int)
    X_test = test_df[feature_cols].to_numpy(dtype=float)
    y_test = test_df["label"].to_numpy(dtype=int)
    X_train_val = train_val_df[feature_cols].to_numpy(dtype=float)
    y_train_val = train_val_df["label"].to_numpy(dtype=int)

    if len(np.unique(y_train)) < 2:
        raise ValueError(f"Training labels contain only one class for setting={setting}.")

    train_ratio = _class_weight_ratio(y_train)
    train_val_ratio = _class_weight_ratio(y_train_val)
    tune_specs = build_model_specs(seed=seed, scale_pos_weight=train_ratio)
    final_specs = build_model_specs(seed=seed, scale_pos_weight=train_val_ratio)

    search_rows: List[Dict[str, object]] = []
    metrics_rows: List[Dict[str, object]] = []

    setting_model_dir.mkdir(parents=True, exist_ok=True)

    for model_name, spec in tune_specs.items():
        print(f"[{setting}] Tuning {model_name}...")
        best_score = -np.inf
        best_score_metric = "roc_auc"
        best_params: Dict[str, object] = {}
        best_prob_val = None

        for params in iter_param_grid(spec["params"]):
            model = spec["builder"](params)
            model.fit(X_train, y_train)
            prob_val = model.predict_proba(X_val)[:, 1]

            auc = safe_roc_auc(y_val, prob_val)
            pr = average_precision_score(y_val, prob_val)
            if np.isfinite(auc):
                selection_metric = "roc_auc"
                selection_score = float(auc)
            else:
                selection_metric = "accuracy_fallback"
                selection_score = float(accuracy_score(y_val, (prob_val >= 0.5).astype(int)))

            search_rows.append(
                {
                    "setting": setting,
                    "model": model_name,
                    "params": json.dumps(params, sort_keys=True),
                    "val_roc_auc": float(auc),
                    "val_pr_auc": float(pr),
                    "selection_metric": selection_metric,
                    "selection_score": selection_score,
                }
            )
            if selection_score > best_score:
                best_score = selection_score
                best_score_metric = selection_metric
                best_params = dict(params)
                best_prob_val = prob_val

        if best_prob_val is None:
            raise RuntimeError(f"Failed to fit {model_name} for setting={setting}.")

        threshold = pick_best_threshold(y_val, best_prob_val)
        val_metrics = metric_bundle(y_val, best_prob_val, threshold)

        final_model = final_specs[model_name]["builder"](best_params)
        final_model.fit(X_train_val, y_train_val)
        prob_test = final_model.predict_proba(X_test)[:, 1]
        test_metrics = metric_bundle(y_test, prob_test, threshold)

        metrics_rows.append(
            {
                "setting": setting,
                "model": model_name,
                "n_features": len(feature_cols),
                "threshold": threshold,
                "val_roc_auc": val_metrics["roc_auc"],
                "val_pr_auc": val_metrics["pr_auc"],
                "val_f1": val_metrics["f1"],
                "val_recall": val_metrics["recall"],
                "val_precision": val_metrics["precision"],
                "val_accuracy": val_metrics["accuracy"],
                "test_roc_auc": test_metrics["roc_auc"],
                "test_pr_auc": test_metrics["pr_auc"],
                "test_f1": test_metrics["f1"],
                "test_recall": test_metrics["recall"],
                "test_precision": test_metrics["precision"],
                "test_accuracy": test_metrics["accuracy"],
            }
        )

        payload = {
            "setting": setting,
            "model": model_name,
            "seed": seed,
            "feature_columns": feature_cols,
            "best_params": best_params,
            "best_threshold": threshold,
            "selection_metric": best_score_metric,
            "selection_score": best_score,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
            "train_scale_pos_weight": train_ratio,
            "train_val_scale_pos_weight": train_val_ratio,
        }
        (setting_model_dir / f"{model_name}_best_params.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        joblib.dump(final_model, setting_model_dir / f"{model_name}_final_model.joblib")

        val_pred = val_df[["community_area", "month", "target_month", "label"]].copy()
        val_pred["pred_prob"] = best_prob_val
        val_pred["pred_label"] = (best_prob_val >= threshold).astype(int)
        val_pred.to_csv(reports_dir / f"{setting}_val_predictions_{model_name}.csv", index=False)

        pred_test = (prob_test >= threshold).astype(int)
        test_pred = test_df[["community_area", "month", "target_month", "label"]].copy()
        test_pred["pred_prob"] = prob_test
        test_pred["pred_label"] = pred_test
        test_pred.to_csv(reports_dir / f"{setting}_test_predictions_{model_name}.csv", index=False)

        print(
            f"[{setting}] {model_name}: "
            f"val ROC-AUC={val_metrics['roc_auc']:.4f}, "
            f"test ROC-AUC={test_metrics['roc_auc']:.4f}, "
            f"test F1={test_metrics['f1']:.4f}"
        )

    search_df = pd.DataFrame(search_rows).sort_values(
        ["setting", "model", "val_roc_auc"],
        ascending=[True, True, False],
    )
    search_df.to_csv(reports_dir / f"{setting}_validation_search_results.csv", index=False)

    metrics_df = pd.DataFrame(metrics_rows).sort_values("test_roc_auc", ascending=False)
    metrics_df.to_csv(reports_dir / f"{setting}_metrics.csv", index=False)
    return metrics_df


def _to_2d_shap(values: object) -> np.ndarray:
    if isinstance(values, list):
        arr = np.asarray(values[-1])
    else:
        arr = np.asarray(values)

    if arr.ndim == 3:
        if arr.shape[2] == 2:
            arr = arr[:, :, 1]
        elif arr.shape[0] == 2:
            arr = arr[1]
        else:
            raise ValueError(f"Unsupported SHAP shape: {arr.shape}")

    if arr.ndim != 2:
        raise ValueError(f"Expected 2D SHAP values, got shape {arr.shape}")
    return arr


def run_global_shap(
    df: pd.DataFrame,
    feature_cols: List[str],
    model_name: str,
    model_path: Path,
    reports_dir: Path,
    seed: int,
    shap_background_size: int,
    shap_explain_size: int,
) -> pd.DataFrame:
    model = joblib.load(model_path)
    model_df = df.dropna(subset=feature_cols + ["label"]).copy()
    train_val_df = model_df[model_df["split"].isin(["train", "val"])].copy()
    test_df = model_df[model_df["split"] == "test"].copy()

    rng = np.random.default_rng(seed)
    X_background = train_val_df[feature_cols].to_numpy(dtype=float)
    X_explain = test_df[feature_cols].to_numpy(dtype=float)

    if len(X_background) > shap_background_size:
        idx_bg = rng.choice(len(X_background), size=shap_background_size, replace=False)
        X_background = X_background[idx_bg]
    if shap_explain_size > 0 and len(X_explain) > shap_explain_size:
        idx_ex = rng.choice(len(X_explain), size=shap_explain_size, replace=False)
        X_explain = X_explain[idx_ex]

    if model_name in {"random_forest", "xgboost"}:
        explainer = shap.TreeExplainer(model)
        shap_values = _to_2d_shap(explainer.shap_values(X_explain))
    elif model_name == "logistic_regression":
        predict_fn = lambda data: model.predict_proba(data)[:, 1]
        explainer = shap.Explainer(predict_fn, X_background, algorithm="permutation")
        shap_values = _to_2d_shap(explainer(X_explain, max_evals=2 * len(feature_cols) + 1).values)
    else:
        raise ValueError(f"Unsupported model for SHAP: {model_name}")

    X_explain_df = pd.DataFrame(X_explain, columns=feature_cols)
    mean_abs = np.abs(shap_values).mean(axis=0)
    shap_df = (
        pd.DataFrame({"feature": feature_cols, "mean_abs_shap": mean_abs})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    shap_df.to_csv(reports_dir / "shap_global_importance.csv", index=False)

    plt.figure(figsize=(8, 5))
    shap.summary_plot(shap_values, X_explain_df, plot_type="bar", show=False)
    plt.tight_layout()
    plt.savefig(reports_dir / "shap_summary_bar.png", dpi=200, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(8, 6))
    shap.summary_plot(shap_values, X_explain_df, show=False)
    plt.tight_layout()
    plt.savefig(reports_dir / "shap_summary_beeswarm.png", dpi=200, bbox_inches="tight")
    plt.close()

    return shap_df


def build_summary_markdown(
    out_path: Path,
    with_metrics: pd.DataFrame,
    without_metrics: pd.DataFrame,
    delta_df: pd.DataFrame,
    shap_df: pd.DataFrame,
    shap_model_name: str,
) -> None:
    lines = [
        "# Hardship Index Ablation + SHAP Summary",
        "",
        "## With Hardship Metrics",
        with_metrics.to_string(index=False),
        "",
        "## Without Hardship Metrics",
        without_metrics.to_string(index=False),
        "",
        "## Ablation Delta (with - without)",
        delta_df.to_string(index=False),
        "",
        f"## Global SHAP (model: {shap_model_name})",
        shap_df.head(12).to_string(index=False),
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    np.random.seed(args.seed)

    crime_files = [Path(p) for p in args.crime_files]
    hardship_path = Path(args.hardship)
    paths_to_check = [hardship_path]
    if args.crime_source == "csv":
        paths_to_check.extend(crime_files)

    for p in paths_to_check:
        if not p.exists():
            raise FileNotFoundError(f"Missing required file: {p}")

    output_root = Path(args.output_dir)
    data_dir = output_root / "data_processed"
    models_dir = output_root / "models"
    reports_dir = output_root / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    panel_base = data_dir / "panel_monthly_base.csv"
    panel_type_counts = data_dir / "panel_monthly_type_counts.csv"
    model_data = data_dir / "model_dataset.csv"
    model_meta = data_dir / "model_metadata.json"

    start_month = pd.Period(args.start_month, freq="M").to_timestamp()
    end_month = pd.Period(args.end_month, freq="M").to_timestamp()

    print("=== Step 1/4: Build monthly panel ===")
    if args.crime_source == "csv":
        build_panel(
            files=crime_files,
            out_base=panel_base,
            out_type_counts=panel_type_counts,
            start_month=start_month,
            end_month=end_month,
            min_area=args.min_area,
            max_area=args.max_area,
            chunksize=args.chunksize,
        )
    else:
        engine = create_tidb_engine(env_file=args.env_file)
        table_name = resolve_chicago_table_name(engine, preferred=args.tidb_table)
        print(f"Using TiDB table: {table_name}")
        base_df, type_df = fetch_monthly_aggregates_from_tidb(
            engine=engine,
            table_name=table_name,
            start_month=start_month,
            end_month=end_month,
            min_area=args.min_area,
            max_area=args.max_area,
        )

        month_range = pd.date_range(start_month, end_month, freq="MS")
        full_index = pd.MultiIndex.from_product(
            [range(args.min_area, args.max_area + 1), month_range],
            names=["community_area", "month"],
        )
        full_df = full_index.to_frame(index=False)

        panel = full_df.merge(base_df, on=["community_area", "month"], how="left")
        panel["count_total"] = panel["count_total"].fillna(0).astype(int)
        panel["count_arrest"] = panel["count_arrest"].fillna(0).astype(int)
        panel["arrest_rate"] = 0.0
        nonzero = panel["count_total"] > 0
        panel.loc[nonzero, "arrest_rate"] = panel.loc[nonzero, "count_arrest"] / panel.loc[nonzero, "count_total"]

        type_df = type_df.sort_values(["community_area", "month", "primary_type"]).reset_index(drop=True)
        panel = panel.sort_values(["community_area", "month"]).reset_index(drop=True)
        panel.to_csv(panel_base, index=False)
        type_df.to_csv(panel_type_counts, index=False)
        print(f"Saved base panel: {panel_base} (rows={len(panel)})")
        print(f"Saved type counts: {panel_type_counts} (rows={len(type_df)})")

    print("=== Step 2/4: Build model dataset ===")
    make_model_dataset(
        base_path=panel_base,
        type_counts_path=panel_type_counts,
        hardship_path=hardship_path,
        out_data=model_data,
        out_meta=model_meta,
    )

    df = pd.read_csv(model_data, parse_dates=["month", "target_month"])

    print("=== Step 3/4: Hardship ablation ===")
    metrics_by_setting: Dict[str, pd.DataFrame] = {}
    for setting, feature_cols in ABLATION_FEATURES.items():
        metrics_df = run_ablation_setting(
            df=df,
            setting=setting,
            feature_cols=feature_cols,
            seed=args.seed,
            setting_model_dir=models_dir / setting,
            reports_dir=reports_dir,
        )
        metrics_by_setting[setting] = metrics_df

    with_metrics = metrics_by_setting["with_hardship"].copy()
    without_metrics = metrics_by_setting["without_hardship"].copy()

    metric_cols = [
        "test_roc_auc",
        "test_pr_auc",
        "test_f1",
        "test_recall",
        "test_precision",
        "test_accuracy",
        "val_roc_auc",
        "val_pr_auc",
    ]
    delta_df = with_metrics[["model"] + metric_cols].merge(
        without_metrics[["model"] + metric_cols],
        on="model",
        suffixes=("_with", "_without"),
    )
    for m in metric_cols:
        delta_df[f"delta_{m}"] = delta_df[f"{m}_with"] - delta_df[f"{m}_without"]
    delta_df = delta_df.sort_values("delta_test_roc_auc", ascending=False).reset_index(drop=True)
    delta_df.to_csv(reports_dir / "hardship_ablation_delta.csv", index=False)

    print("=== Step 4/4: Global SHAP on best with_hardship model ===")
    shap_target_row = with_metrics.sort_values("test_roc_auc", ascending=False).iloc[0]
    shap_model_name = str(shap_target_row["model"])
    shap_model_path = models_dir / "with_hardship" / f"{shap_model_name}_final_model.joblib"
    shap_df = run_global_shap(
        df=df,
        feature_cols=ABLATION_FEATURES["with_hardship"],
        model_name=shap_model_name,
        model_path=shap_model_path,
        reports_dir=reports_dir,
        seed=args.seed,
        shap_background_size=args.shap_background_size,
        shap_explain_size=args.shap_explain_size,
    )

    with_metrics.to_csv(reports_dir / "with_hardship_metrics.csv", index=False)
    without_metrics.to_csv(reports_dir / "without_hardship_metrics.csv", index=False)
    build_summary_markdown(
        out_path=reports_dir / "summary.md",
        with_metrics=with_metrics,
        without_metrics=without_metrics,
        delta_df=delta_df,
        shap_df=shap_df,
        shap_model_name=shap_model_name,
    )

    print(f"All experiment outputs saved under: {output_root}")


if __name__ == "__main__":
    main()
