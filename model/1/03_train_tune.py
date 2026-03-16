#!/usr/bin/env python3
"""Train and tune Logistic Regression, Random Forest, and XGBoost on train/val splits."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import joblib
import numpy as np
import pandas as pd
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


FEATURE_COLS = [
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data_processed/model_dataset.csv")
    parser.add_argument("--models-dir", default="models")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def metric_bundle(y_true: np.ndarray, prob: np.ndarray, threshold: float) -> Dict[str, float]:
    pred = (prob >= threshold).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y_true, prob)),
        "pr_auc": float(average_precision_score(y_true, prob)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, pred)),
    }


def pick_best_threshold(y_true: np.ndarray, prob: np.ndarray) -> float:
    thresholds = np.linspace(0.05, 0.95, 181)
    best_threshold = 0.5
    best_f1 = -1.0
    for t in thresholds:
        f1 = f1_score(y_true, (prob >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = float(t)
    return best_threshold


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
        penalty="l2",
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


def main() -> None:
    args = parse_args()
    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(f"Missing dataset: {data_path}")

    models_dir = Path(args.models_dir)
    reports_dir = Path(args.reports_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path, parse_dates=["month", "target_month"])

    required = FEATURE_COLS + ["split", "label"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column in dataset: {col}")

    model_df = df.dropna(subset=FEATURE_COLS + ["label"]).copy()

    train_df = model_df[model_df["split"] == "train"].copy()
    val_df = model_df[model_df["split"] == "val"].copy()

    X_train = train_df[FEATURE_COLS].to_numpy(dtype=float)
    y_train = train_df["label"].to_numpy(dtype=int)
    X_val = val_df[FEATURE_COLS].to_numpy(dtype=float)
    y_val = val_df["label"].to_numpy(dtype=int)

    if len(np.unique(y_train)) < 2:
        raise ValueError("Training label has only one class after preprocessing.")

    pos = int(y_train.sum())
    neg = int(len(y_train) - pos)
    scale_pos_weight = (neg / pos) if pos > 0 else 1.0

    grids = {
        "logistic_regression": {
            "builder": lambda p: build_lr(p, args.seed),
            "params": {"C": [0.01, 0.05, 0.1, 0.5, 1.0, 2.0]},
        },
        "random_forest": {
            "builder": lambda p: build_rf(p, args.seed),
            "params": {
                "n_estimators": [300, 500],
                "max_depth": [6, 10, None],
                "min_samples_leaf": [1, 5],
                "max_features": ["sqrt", 0.7],
            },
        },
        "xgboost": {
            "builder": lambda p: build_xgb(p, args.seed, scale_pos_weight),
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

    search_rows: List[Dict[str, object]] = []
    best_rows: List[Dict[str, object]] = []

    for model_name, spec in grids.items():
        print(f"Tuning {model_name}...")
        best_auc = -np.inf
        best_model = None
        best_params: Dict[str, object] = {}
        best_prob_val = None

        for params in iter_param_grid(spec["params"]):
            model = spec["builder"](params)
            model.fit(X_train, y_train)
            prob_val = model.predict_proba(X_val)[:, 1]

            auc = roc_auc_score(y_val, prob_val)
            pr = average_precision_score(y_val, prob_val)
            search_rows.append(
                {
                    "model": model_name,
                    "params": json.dumps(params, sort_keys=True),
                    "val_roc_auc": float(auc),
                    "val_pr_auc": float(pr),
                }
            )

            if auc > best_auc:
                best_auc = float(auc)
                best_model = model
                best_params = dict(params)
                best_prob_val = prob_val

        if best_model is None or best_prob_val is None:
            raise RuntimeError(f"No model was fitted for {model_name}")

        best_threshold = pick_best_threshold(y_val, best_prob_val)
        metrics = metric_bundle(y_val, best_prob_val, best_threshold)

        best_rows.append(
            {
                "model": model_name,
                "threshold": best_threshold,
                "val_roc_auc": metrics["roc_auc"],
                "val_pr_auc": metrics["pr_auc"],
                "val_f1": metrics["f1"],
                "val_recall": metrics["recall"],
                "val_precision": metrics["precision"],
                "val_accuracy": metrics["accuracy"],
            }
        )

        params_payload = {
            "model": model_name,
            "seed": args.seed,
            "feature_columns": FEATURE_COLS,
            "best_params": best_params,
            "best_threshold": best_threshold,
            "val_metrics": metrics,
            "scale_pos_weight": scale_pos_weight,
        }
        (models_dir / f"{model_name}_best_params.json").write_text(
            json.dumps(params_payload, indent=2),
            encoding="utf-8",
        )
        joblib.dump(best_model, models_dir / f"{model_name}_best_train_model.joblib")

        val_pred = val_df[["community_area", "month", "target_month", "label"]].copy()
        val_pred["pred_prob"] = best_prob_val
        val_pred["pred_label"] = (best_prob_val >= best_threshold).astype(int)
        val_pred.to_csv(reports_dir / f"val_predictions_{model_name}.csv", index=False)

        print(
            f"  best ROC-AUC={metrics['roc_auc']:.4f}, "
            f"F1={metrics['f1']:.4f}, threshold={best_threshold:.2f}"
        )

    pd.DataFrame(search_rows).sort_values(["model", "val_roc_auc"], ascending=[True, False]).to_csv(
        reports_dir / "validation_search_results.csv", index=False
    )
    pd.DataFrame(best_rows).sort_values("val_roc_auc", ascending=False).to_csv(
        reports_dir / "validation_metrics.csv", index=False
    )

    print(f"Saved validation results to: {reports_dir}")


if __name__ == "__main__":
    main()
