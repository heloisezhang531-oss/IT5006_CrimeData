#!/usr/bin/env python3
"""Chicago -> NIBRS zero-shot transfer with Chicago-fitted standardization.

Workflow:
1) Fit imputation values and StandardScaler on Chicago train split only.
2) Train models on Chicago train split only.
3) Pick thresholds on Chicago val split only.
4) Apply unchanged scaler/models/thresholds to NIBRS (no NIBRS retraining/tuning).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

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
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

FEATURE_COLS = [
    "hardship_index",
    "spatial_lag_hardship",
    "spatial_lag_crime_lag1",
    "arrest_rate",
    "top_type_share",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chicago-data", default="data_processed/geo_model_dataset.csv")
    parser.add_argument("--nibrs-data", default="model/NIRBS/NIBRS_model_dataset.csv")
    parser.add_argument("--out-dir", default="model/NIRBS/zero_shot_standardized")
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
    best_t = 0.5
    best_f1 = -1.0
    for t in thresholds:
        f1 = f1_score(y_true, (prob >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = float(t)
    return best_t


def _prepare_nibrs_for_eval(df: pd.DataFrame) -> pd.DataFrame:
    # Keep the intended test split rows when present; this also removes known dirty split='0' rows.
    if "split" in df.columns and (df["split"] == "test").any():
        out = df[df["split"] == "test"].copy()
    else:
        out = df.copy()
    return out


def _fit_scaler_from_chicago_train(chicago_train: pd.DataFrame):
    medians = {}
    X = chicago_train[FEATURE_COLS].copy()
    for col in FEATURE_COLS:
        X[col] = pd.to_numeric(X[col], errors="coerce")
        med = X[col].median()
        medians[col] = float(med) if np.isfinite(med) else 0.0
        X[col] = X[col].fillna(medians[col])

    scaler = StandardScaler()
    scaler.fit(X.to_numpy(dtype=float))
    return medians, scaler


def _transform_with_chicago_stats(df: pd.DataFrame, medians: Dict[str, float], scaler: StandardScaler) -> np.ndarray:
    X = df[FEATURE_COLS].copy()
    for col in FEATURE_COLS:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(medians[col])
    return scaler.transform(X.to_numpy(dtype=float))


def main() -> None:
    args = parse_args()
    np.random.seed(args.seed)

    chicago_path = Path(args.chicago_data)
    nibrs_path = Path(args.nibrs_data)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not chicago_path.exists():
        raise FileNotFoundError(f"Missing Chicago dataset: {chicago_path}")
    if not nibrs_path.exists():
        raise FileNotFoundError(f"Missing NIBRS dataset: {nibrs_path}")

    chi = pd.read_csv(chicago_path, parse_dates=["month", "target_month"])
    ni = pd.read_csv(nibrs_path)
    if "month" in ni.columns:
        ni["month"] = pd.to_datetime(ni["month"], errors="coerce")
    if "target_month" in ni.columns:
        ni["target_month"] = pd.to_datetime(ni["target_month"], errors="coerce")

    required = FEATURE_COLS + ["split", "label"]
    missing = [c for c in required if c not in chi.columns]
    if missing:
        raise ValueError(f"Chicago dataset missing required columns: {missing}")
    missing_ni = [c for c in FEATURE_COLS + ["label"] if c not in ni.columns]
    if missing_ni:
        raise ValueError(f"NIBRS dataset missing required columns: {missing_ni}")

    chi_train = chi[chi["split"] == "train"].copy()
    chi_val = chi[chi["split"] == "val"].copy()
    if chi_train.empty or chi_val.empty:
        raise ValueError("Chicago train/val split empty.")

    ni_eval = _prepare_nibrs_for_eval(ni)
    if ni_eval.empty:
        raise ValueError("NIBRS eval set is empty.")

    medians, scaler = _fit_scaler_from_chicago_train(chi_train)
    X_train = _transform_with_chicago_stats(chi_train, medians, scaler)
    X_val = _transform_with_chicago_stats(chi_val, medians, scaler)
    X_ni = _transform_with_chicago_stats(ni_eval, medians, scaler)

    y_train = chi_train["label"].to_numpy(dtype=int)
    y_val = chi_val["label"].to_numpy(dtype=int)
    y_ni = pd.to_numeric(ni_eval["label"], errors="coerce").fillna(0).to_numpy(dtype=int)

    if len(np.unique(y_train)) < 2:
        raise ValueError("Chicago train label has only one class.")
    if len(np.unique(y_val)) < 2:
        raise ValueError("Chicago val label has only one class.")
    if len(np.unique(y_ni)) < 2:
        raise ValueError("NIBRS eval label has only one class; ROC is undefined.")

    pos = int(y_train.sum())
    neg = int(len(y_train) - pos)
    scale_pos_weight = (neg / pos) if pos > 0 else 1.0

    models = {
        "logistic_regression": LogisticRegression(
            random_state=args.seed,
            max_iter=2000,
            solver="liblinear",
            class_weight="balanced",
            C=0.01,
        ),
        "random_forest": RandomForestClassifier(
            random_state=args.seed,
            n_jobs=-1,
            class_weight="balanced_subsample",
            n_estimators=300,
            max_depth=None,
            min_samples_leaf=5,
            max_features="sqrt",
        ),
        "xgboost": XGBClassifier(
            random_state=args.seed,
            objective="binary:logistic",
            tree_method="hist",
            eval_metric="auc",
            n_jobs=-1,
            scale_pos_weight=scale_pos_weight,
            n_estimators=300,
            max_depth=3,
            learning_rate=0.1,
            subsample=1.0,
            colsample_bytree=0.8,
            reg_lambda=1.0,
        ),
    }

    metrics_rows: List[Dict[str, object]] = []
    thresholds: Dict[str, float] = {}

    for model_name, model in models.items():
        model.fit(X_train, y_train)
        prob_val = model.predict_proba(X_val)[:, 1]
        threshold = pick_best_threshold(y_val, prob_val)
        thresholds[model_name] = threshold

        val_metrics = metric_bundle(y_val, prob_val, threshold)
        prob_ni = model.predict_proba(X_ni)[:, 1]
        ni_metrics = metric_bundle(y_ni, prob_ni, threshold)

        metrics_rows.append(
            {
                "model": model_name,
                "threshold_from_chicago_val": threshold,
                "chicago_val_roc_auc": val_metrics["roc_auc"],
                "chicago_val_pr_auc": val_metrics["pr_auc"],
                "nibrs_roc_auc": ni_metrics["roc_auc"],
                "nibrs_pr_auc": ni_metrics["pr_auc"],
                "nibrs_f1": ni_metrics["f1"],
                "nibrs_recall": ni_metrics["recall"],
                "nibrs_precision": ni_metrics["precision"],
                "nibrs_accuracy": ni_metrics["accuracy"],
            }
        )

        pred_df = ni_eval.copy()
        pred_df["pred_prob"] = prob_ni
        pred_df["pred_label"] = (prob_ni >= threshold).astype(int)
        pred_keep = [c for c in ["state_abbr", "month", "target_month", "label", "pred_prob", "pred_label"] if c in pred_df.columns]
        pred_df[pred_keep].to_csv(out_dir / f"nibrs_zero_shot_predictions_{model_name}.csv", index=False)

        joblib.dump(model, out_dir / f"chicago_standardized_{model_name}.joblib")

        print(
            f"{model_name}: Chicago val ROC-AUC={val_metrics['roc_auc']:.4f}; "
            f"NIBRS ROC-AUC={ni_metrics['roc_auc']:.4f}"
        )

    metrics_df = pd.DataFrame(metrics_rows).sort_values("nibrs_roc_auc", ascending=False)
    metrics_df.to_csv(out_dir / "zero_shot_metrics.csv", index=False)

    payload = {
        "feature_columns": FEATURE_COLS,
        "impute_medians_from_chicago_train": medians,
        "thresholds_from_chicago_val": thresholds,
        "chicago_data": str(chicago_path),
        "nibrs_data": str(nibrs_path),
    }
    (out_dir / "zero_shot_config.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    joblib.dump(scaler, out_dir / "chicago_train_standard_scaler.joblib")

    print(f"Saved zero-shot outputs to: {out_dir}")


if __name__ == "__main__":
    main()
