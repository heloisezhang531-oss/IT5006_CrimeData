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
    "spatial_lag_hardship",     # spatial lag of hardship index
    "spatial_lag_crime_lag1",  # spatial lag of crime count 
    # "count_lag1",
    # "count_lag3",
    # "count_lag6",
    # "count_lag12",
    # "roll_mean_3",
    # "roll_mean_6",
    # "roll_mean_12",
    # "month_sin",
    # "month_cos",
    "arrest_rate",
    "top_type_share",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data_processed/geo_model_dataset.csv")
    parser.add_argument("--models-dir", default="models")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def safe_roc_auc(y_true: np.ndarray, prob: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, prob))


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
        "roc_auc": safe_roc_auc(y_true, prob),
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

    train_df = df[df["split"] == "train"].copy()
    val_df = df[df["split"] == "val"].copy()
    train_val_df = df[df["split"].isin(["train", "val"])].copy()
    test_df = df[df["split"] == "test"].copy()

    X_train_val = train_val_df[FEATURE_COLS].to_numpy(dtype=float)
    y_train_val = train_val_df["label"].to_numpy(dtype=int)
    split_frames = {
        "train": train_df,
        "val": val_df,
        "test": test_df,
    }

    pos = int(y_train_val.sum())
    neg = int(len(y_train_val) - pos)
    scale_pos_weight = (neg / pos) if pos > 0 else 1.0

    model_names = ["logistic_regression", "random_forest", "xgboost"]
    split_metrics_rows: List[Dict[str, object]] = []
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
        for split_name, split_df in split_frames.items():
            X_split = split_df[FEATURE_COLS].to_numpy(dtype=float)
            y_split = split_df["label"].to_numpy(dtype=int)
            prob_split = model.predict_proba(X_split)[:, 1]
            pred_split = (prob_split >= threshold).astype(int)
            metrics = metrics_with_threshold(y_split, prob_split, threshold)
            split_metrics_rows.append(
                {
                    "model": model_name,
                    "split": split_name,
                    "threshold": threshold,
                    "roc_auc": metrics["roc_auc"],
                    "pr_auc": metrics["pr_auc"],
                    "f1": metrics["f1"],
                    "recall": metrics["recall"],
                    "precision": metrics["precision"],
                    "accuracy": metrics["accuracy"],
                }
            )

            pred_df = split_df[["community_area", "month", "target_month", "label"]].copy()
            pred_df["pred_prob"] = prob_split
            pred_df["pred_label"] = pred_split
            pred_df.to_csv(reports_dir / f"{split_name}_predictions_{model_name}.csv", index=False)

        # Keep test confusion matrix for compatibility.
        X_test = test_df[FEATURE_COLS].to_numpy(dtype=float)
        y_test = test_df["label"].to_numpy(dtype=int)
        prob_test = model.predict_proba(X_test)[:, 1]
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

        fi = feature_importance_df(model_name, model, FEATURE_COLS)
        fi.to_csv(reports_dir / f"feature_importance_{model_name}.csv", index=False)

        test_metrics = metrics_with_threshold(y_test, prob_test, threshold)
        print(
            f"{model_name}: TEST ROC-AUC={test_metrics['roc_auc']:.4f}, "
            f"F1={test_metrics['f1']:.4f}, Recall={test_metrics['recall']:.4f}"
        )

    split_metrics_df = pd.DataFrame(split_metrics_rows).sort_values(["split", "roc_auc"], ascending=[True, False])
    test_metrics_df = (
        split_metrics_df[split_metrics_df["split"] == "test"]
        .drop(columns=["split"])
        .rename(
            columns={
                "roc_auc": "test_roc_auc",
                "pr_auc": "test_pr_auc",
                "f1": "test_f1",
                "recall": "test_recall",
                "precision": "test_precision",
                "accuracy": "test_accuracy",
            }
        )
        .sort_values("test_roc_auc", ascending=False)
        .reset_index(drop=True)
    )
    conf_df = pd.DataFrame(conf_rows)

    split_metrics_df.to_csv(reports_dir / "split_metrics.csv", index=False)
    test_metrics_df.to_csv(reports_dir / "test_metrics.csv", index=False)
    conf_df.to_csv(reports_dir / "test_confusion_matrix.csv", index=False)

    summary_lines = [
        "# Split Metrics Summary (Train / Val / Test)",
        "",
        split_metrics_df.to_string(index=False),
        "",
    ]
    (reports_dir / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"Saved test reports to: {reports_dir}")


if __name__ == "__main__":
    main()
