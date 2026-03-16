#!/usr/bin/env python3
"""Evaluate tuned NIBRS models on the held-out test split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

FEATURE_COLS = [
    "hardship_index",
    "spatial_lag_hardship",
    "spatial_lag_crime_lag1",
    "arrest_rate",
    "top_type_share",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="model/NIRBS/NIBRS_model_dataset.csv")
    parser.add_argument("--models-dir", default="model/NIRBS/models")
    parser.add_argument("--reports-dir", default="model/NIRBS/reports")
    return parser.parse_args()


def metrics_with_threshold(y_true: np.ndarray, prob: np.ndarray, threshold: float) -> Dict[str, float]:
    pred = (prob >= threshold).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y_true, prob)),
        "pr_auc": float(average_precision_score(y_true, prob)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, pred)),
    }


def feature_importance_df(model_name: str, fitted_model, feature_cols: List[str]) -> pd.DataFrame:
    if model_name == "logistic_regression":
        # Handle both bare LogisticRegression and Pipeline-wrapped models.
        if hasattr(fitted_model, "coef_"):
            coef = fitted_model.coef_.ravel()
        else:
            coef = fitted_model.named_steps["clf"].coef_.ravel()
        values = np.abs(coef)
    else:
        values = fitted_model.feature_importances_

    fi = pd.DataFrame({"feature": feature_cols, "importance": values})
    return fi.sort_values("importance", ascending=False).reset_index(drop=True)


def _prediction_base_cols(df: pd.DataFrame) -> List[str]:
    cols = []
    for c in ["state_abbr", "community_area", "month", "target_month", "label"]:
        if c in df.columns:
            cols.append(c)
    return cols


def main() -> None:
    args = parse_args()
    data_path = Path(args.data)
    models_dir = Path(args.models_dir)
    reports_dir = Path(args.reports_dir)

    if not data_path.exists():
        raise FileNotFoundError(f"Missing dataset: {data_path}")
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path, parse_dates=["month", "target_month"])
    required_cols = FEATURE_COLS + ["split", "label"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df[FEATURE_COLS] = df[FEATURE_COLS].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    test_df = df[df["split"] == "test"].copy()
    if test_df.empty:
        raise ValueError("No rows found for split=='test'.")

    X_test = test_df[FEATURE_COLS].to_numpy(dtype=float)
    y_test = test_df["label"].to_numpy(dtype=int)
    id_cols = _prediction_base_cols(test_df)

    model_names = ["logistic_regression", "random_forest", "xgboost"]
    metrics_rows: List[Dict[str, object]] = []
    conf_rows: List[Dict[str, object]] = []

    for model_name in model_names:
        param_file = models_dir / f"{model_name}_best_params.json"
        model_file = models_dir / f"{model_name}_best_train_model.joblib"
        if not param_file.exists():
            raise FileNotFoundError(f"Missing tuned parameters: {param_file}")
        if not model_file.exists():
            raise FileNotFoundError(f"Missing trained model: {model_file}")

        payload = json.loads(param_file.read_text(encoding="utf-8"))
        payload_features = payload.get("feature_columns")
        if payload_features is not None and list(payload_features) != FEATURE_COLS:
            raise ValueError(
                f"{model_name} feature mismatch. "
                f"Expected {FEATURE_COLS}, got {payload_features}. "
                "Retrain with NIBRS03_train_tune.py before testing."
            )
        threshold = float(payload["best_threshold"])

        model = joblib.load(model_file)
        prob_test = model.predict_proba(X_test)[:, 1]

        metrics = metrics_with_threshold(y_test, prob_test, threshold)
        metrics_rows.append(
            {
                "model": model_name,
                "threshold": threshold,
                "test_roc_auc": metrics["roc_auc"],
                "test_pr_auc": metrics["pr_auc"],
                "test_f1": metrics["f1"],
                "test_recall": metrics["recall"],
                "test_precision": metrics["precision"],
                "test_accuracy": metrics["accuracy"],
            }
        )

        pred_test = (prob_test >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, pred_test, labels=[0, 1]).ravel()
        conf_rows.append(
            {
                "model": model_name,
                "tn": int(tn),
                "fp": int(fp),
                "fn": int(fn),
                "tp": int(tp),
            }
        )

        pred_df = test_df[id_cols].copy()
        pred_df["pred_prob"] = prob_test
        pred_df["pred_label"] = pred_test
        pred_df.to_csv(reports_dir / f"test_predictions_{model_name}.csv", index=False)

        fi = feature_importance_df(model_name, model, FEATURE_COLS)
        fi.to_csv(reports_dir / f"feature_importance_{model_name}.csv", index=False)

        print(
            f"{model_name}: ROC-AUC={metrics['roc_auc']:.4f}, "
            f"F1={metrics['f1']:.4f}, Recall={metrics['recall']:.4f}"
        )

    metrics_df = pd.DataFrame(metrics_rows).sort_values("test_roc_auc", ascending=False)
    conf_df = pd.DataFrame(conf_rows)

    metrics_df.to_csv(reports_dir / "test_metrics.csv", index=False)
    conf_df.to_csv(reports_dir / "test_confusion_matrix.csv", index=False)

    summary_lines = [
        "# NIBRS Test Summary",
        "",
        metrics_df.to_string(index=False),
        "",
    ]
    (reports_dir / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"Saved test reports to: {reports_dir}")


if __name__ == "__main__":
    main()
