#!/usr/bin/env python3
"""Refit best models on train+val and evaluate on external test set (2025)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
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


def build_model(model_name: str, params: Dict[str, object], seed: int, scale_pos_weight: float):
    if model_name == "logistic_regression":
        clf = LogisticRegression(
            random_state=seed,
            max_iter=2000,
            solver="liblinear",
            penalty="l2",
            class_weight="balanced",
            **params,
        )
        return Pipeline([("scaler", StandardScaler()), ("clf", clf)])

    if model_name == "random_forest":
        return RandomForestClassifier(
            random_state=seed,
            n_jobs=-1,
            class_weight="balanced_subsample",
            **params,
        )

    if model_name == "xgboost":
        return XGBClassifier(
            random_state=seed,
            objective="binary:logistic",
            tree_method="hist",
            eval_metric="auc",
            n_jobs=-1,
            scale_pos_weight=scale_pos_weight,
            **params,
        )

    raise ValueError(f"Unsupported model_name: {model_name}")


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
        coef = fitted_model.named_steps["clf"].coef_.ravel()
        values = np.abs(coef)
    else:
        values = fitted_model.feature_importances_

    fi = pd.DataFrame({"feature": feature_cols, "importance": values})
    return fi.sort_values("importance", ascending=False).reset_index(drop=True)


def main() -> None:
    args = parse_args()
    data_path = Path(args.data)
    models_dir = Path(args.models_dir)
    reports_dir = Path(args.reports_dir)

    if not data_path.exists():
        raise FileNotFoundError(f"Missing dataset: {data_path}")
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path, parse_dates=["month", "target_month"])
    df = df.dropna(subset=FEATURE_COLS + ["label"]).copy()

    train_val_df = df[df["split"].isin(["train", "val"])].copy()
    test_df = df[df["split"] == "test"].copy()

    X_train_val = train_val_df[FEATURE_COLS].to_numpy(dtype=float)
    y_train_val = train_val_df["label"].to_numpy(dtype=int)
    X_test = test_df[FEATURE_COLS].to_numpy(dtype=float)
    y_test = test_df["label"].to_numpy(dtype=int)

    pos = int(y_train_val.sum())
    neg = int(len(y_train_val) - pos)
    scale_pos_weight = (neg / pos) if pos > 0 else 1.0

    model_names = ["logistic_regression", "random_forest", "xgboost"]
    metrics_rows: List[Dict[str, object]] = []
    conf_rows: List[Dict[str, object]] = []

    for model_name in model_names:
        param_file = models_dir / f"{model_name}_best_params.json"
        if not param_file.exists():
            raise FileNotFoundError(f"Missing tuned parameters: {param_file}")

        payload = json.loads(param_file.read_text(encoding="utf-8"))
        params = payload["best_params"]
        threshold = float(payload["best_threshold"])

        model = build_model(model_name, params, args.seed, scale_pos_weight)
        model.fit(X_train_val, y_train_val)
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

        pred_df = test_df[["community_area", "month", "target_month", "label"]].copy()
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
        "# External Test Summary (2025)",
        "",
        metrics_df.to_string(index=False),
        "",
    ]
    (reports_dir / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"Saved test reports to: {reports_dir}")


if __name__ == "__main__":
    main()
