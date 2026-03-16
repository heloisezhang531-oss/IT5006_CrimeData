#!/usr/bin/env python3
"""Chicago->NIBRS zero-shot: population-normalized features + unsupervised covariate-shift reweighting."""
from __future__ import annotations

import argparse
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
import joblib
import numpy as np
import pandas as pd
import requests
from scipy.stats import ks_2samp
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

BASE = ["hardship_index", "spatial_lag_hardship", "spatial_lag_crime_lag1", "arrest_rate", "top_type_share"]
POPN = ["hardship_index", "spatial_lag_hardship", "spatial_lag_crime_lag1_pc100k_log1p", "arrest_rate", "top_type_share"]


@dataclass
class RoundCfg:
    rid: str
    desc: str
    use_pop: bool
    rw: Optional[str] = None
    clip_mode: Optional[str] = None
    clip_min: Optional[float] = None
    clip_max: Optional[float] = None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chicago-data", default="model/NIRBS/chicago_model_dataset.csv")
    p.add_argument("--nibrs-data", default="model/NIRBS/NIBRS_model_dataset.csv")
    p.add_argument("--chicago-pop-zip", default="model/NIRBS/population of Chicago.zip")
    p.add_argument("--state-pop-url", default="https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/totals/NST-EST2024-ALLDATA.csv")
    p.add_argument("--state-pop-cache", default="data_external/population/NST-EST2024-ALLDATA.csv")
    p.add_argument("--review-end-month", default="2024-11")
    p.add_argument("--holdout-start-month", default="2024-12")
    p.add_argument("--max-rounds", type=int, default=5)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out-dir", default="model/NIRBS/zero_shot_popnorm_reweight")
    return p.parse_args()


def metrics(y: np.ndarray, p: np.ndarray, t: float) -> Dict[str, float]:
    yhat = (p >= t).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "f1": float(f1_score(y, yhat, zero_division=0)),
        "recall": float(recall_score(y, yhat, zero_division=0)),
        "precision": float(precision_score(y, yhat, zero_division=0)),
        "accuracy": float(accuracy_score(y, yhat)),
    }


def best_t(y: np.ndarray, p: np.ndarray) -> float:
    best, best_f1 = 0.5, -1.0
    for t in np.linspace(0.05, 0.95, 181):
        f1 = f1_score(y, (p >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best, best_f1 = float(t), float(f1)
    return best


def load_chicago_pop(zip_path: Path) -> pd.DataFrame:
    if not zip_path.exists():
        raise FileNotFoundError(f"Missing {zip_path}")
    out: List[pd.DataFrame] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in sorted(zf.namelist()):
            if not name.lower().endswith(".csv"):
                continue
            stem = Path(name).stem
            yrs = [x for x in stem.split("_") if x.isdigit() and len(x) == 4]
            if not yrs:
                continue
            year = int(yrs[-1])
            with zf.open(name) as f:
                df = pd.read_csv(io.BytesIO(f.read()))
            id_col = "GEOID" if "GEOID" in df.columns else ("OBJECTID" if "OBJECTID" in df.columns else None)
            if id_col is None or "TOT_POP" not in df.columns:
                continue
            x = pd.DataFrame({
                "community_area": pd.to_numeric(df[id_col], errors="coerce"),
                "year": year,
                "population": pd.to_numeric(df["TOT_POP"], errors="coerce"),
            }).dropna(subset=["community_area", "population"])
            x["community_area"] = x["community_area"].astype(int)
            out.append(x)
    if not out:
        raise ValueError("No Chicago population rows loaded")
    pop = pd.concat(out, ignore_index=True)
    return pop.groupby(["community_area", "year"], as_index=False)["population"].median()


def load_state_pop_2024(url: str, cache: Path) -> pd.DataFrame:
    if cache.exists():
        raw = pd.read_csv(cache)
    else:
        cache.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        cache.write_bytes(r.content)
        raw = pd.read_csv(cache)
    if "SUMLEV" not in raw.columns or "STATE" not in raw.columns or "POPESTIMATE2024" not in raw.columns:
        raise ValueError("State population file missing required columns")
    st = raw[raw["SUMLEV"] == 40].copy()
    st["STATEFP"] = pd.to_numeric(st["STATE"], errors="coerce").astype("Int64").astype(str).str.zfill(2)
    shp = gpd.read_file("zip://model/NIRBS/tl_2024_us_state.zip")[["STATEFP", "STUSPS"]].drop_duplicates("STATEFP")
    st = st.merge(shp, on="STATEFP", how="left")
    st["population"] = pd.to_numeric(st["POPESTIMATE2024"], errors="coerce")
    st = st.dropna(subset=["STUSPS", "population"]).copy()
    st["state_abbr"] = st["STUSPS"].astype(str).str.upper()
    return st[["state_abbr", "population"]].drop_duplicates("state_abbr")


def add_population_and_popnorm(chi: pd.DataFrame, ni: pd.DataFrame, chi_pop: pd.DataFrame, st_pop: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    audit = []
    c = chi.copy()
    c["year"] = c["month"].dt.year
    c = c.merge(chi_pop, on=["community_area", "year"], how="left")
    cm = int(c["population"].isna().sum())
    cfill = float(np.nanmedian(pd.to_numeric(c["population"], errors="coerce"))) if len(c) else 1.0
    if not np.isfinite(cfill):
        cfill = 1.0
    c["population"] = pd.to_numeric(c["population"], errors="coerce").fillna(cfill)
    audit.append({"dataset": "chicago", "rows": int(len(c)), "missing_population_rows": cm, "missing_rate": float(cm / len(c)) if len(c) else 0.0, "fill_population": cfill})

    n = ni.copy()
    n["state_abbr"] = n["state_abbr"].astype(str).str.upper()
    n = n.merge(st_pop, on="state_abbr", how="left")
    nm = int(n["population"].isna().sum())
    nfill = float(np.nanmedian(pd.to_numeric(n["population"], errors="coerce"))) if len(n) else 1.0
    if not np.isfinite(nfill):
        nfill = 1.0
    n["population"] = pd.to_numeric(n["population"], errors="coerce").fillna(nfill)
    audit.append({"dataset": "nibrs", "rows": int(len(n)), "missing_population_rows": nm, "missing_rate": float(nm / len(n)) if len(n) else 0.0, "fill_population": nfill})

    for d in (c, n):
        x = pd.to_numeric(d["spatial_lag_crime_lag1"], errors="coerce")
        p = pd.to_numeric(d["population"], errors="coerce")
        rate = np.where(p > 0, x / p * 100000.0, np.nan)
        rate = pd.to_numeric(pd.Series(rate, index=d.index), errors="coerce")
        d["spatial_lag_crime_lag1_pc100k"] = rate
        d["spatial_lag_crime_lag1_pc100k_log1p"] = np.log1p(np.clip(rate.fillna(0.0).to_numpy(dtype=float), 0.0, None))

    return c, n, pd.DataFrame(audit)


def split_nibrs(ni: pd.DataFrame, review_end: str, holdout_start: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, object]]:
    d = ni.copy()
    d["target_month"] = pd.to_datetime(d["target_month"], errors="coerce")
    dirty = int((d.get("split").astype(str) == "0").sum()) if "split" in d.columns else 0
    if "split" in d.columns and (d["split"] == "test").any():
        d = d[d["split"] == "test"].copy()
    r_end = pd.Period(review_end, freq="M").to_timestamp()
    h_start = pd.Period(holdout_start, freq="M").to_timestamp()
    if r_end >= h_start:
        raise ValueError("review_end_month must be < holdout_start_month")
    rv = d[d["target_month"] <= r_end].copy()
    ho = d[d["target_month"] >= h_start].copy()
    if rv.empty or ho.empty:
        raise ValueError("Review or holdout partition is empty")
    meta = {
        "nibrs_rows_after_test_filter": int(len(d)),
        "nibrs_dirty_split_rows_dropped": dirty,
        "review_rows": int(len(rv)),
        "holdout_rows": int(len(ho)),
        "review_months": sorted(rv["target_month"].dropna().dt.strftime("%Y-%m").unique().tolist()),
        "holdout_months": sorted(ho["target_month"].dropna().dt.strftime("%Y-%m").unique().tolist()),
        "review_label_rate": float(pd.to_numeric(rv["label"], errors="coerce").mean()),
        "holdout_label_rate": float(pd.to_numeric(ho["label"], errors="coerce").mean()),
    }
    return rv, ho, meta


def fit_stats(train_df: pd.DataFrame, cols: List[str]) -> Tuple[Dict[str, float], StandardScaler]:
    X = train_df[cols].copy()
    med: Dict[str, float] = {}
    for c in cols:
        X[c] = pd.to_numeric(X[c], errors="coerce")
        m = X[c].median()
        med[c] = float(m) if np.isfinite(m) else 0.0
        X[c] = X[c].fillna(med[c])
    sc = StandardScaler()
    sc.fit(X.to_numpy(dtype=float))
    return med, sc


def tx(df: pd.DataFrame, cols: List[str], med: Dict[str, float], sc: StandardScaler) -> np.ndarray:
    X = df[cols].copy()
    for c in cols:
        X[c] = pd.to_numeric(X[c], errors="coerce").fillna(med[c])
    return sc.transform(X.to_numpy(dtype=float))


def build_models(seed: int, spw: float) -> Dict[str, object]:
    return {
        "logistic_regression": LogisticRegression(random_state=seed, max_iter=2000, solver="liblinear", class_weight="balanced", C=0.01),
        "random_forest": RandomForestClassifier(random_state=seed, n_jobs=-1, class_weight="balanced_subsample", n_estimators=300, max_depth=None, min_samples_leaf=5, max_features="sqrt"),
        "xgboost": XGBClassifier(random_state=seed, objective="binary:logistic", tree_method="hist", eval_metric="auc", n_jobs=-1, scale_pos_weight=spw, n_estimators=300, max_depth=3, learning_rate=0.1, subsample=1.0, colsample_bytree=0.8, reg_lambda=1.0),
    }


def domain_weights(xs: np.ndarray, xt: np.ndarray, cfg: RoundCfg, seed: int) -> Tuple[np.ndarray, Dict[str, object]]:
    if cfg.rw is None:
        return np.ones(xs.shape[0], dtype=float), {"round_id": cfg.rid, "reweight": "none"}
    if cfg.rw == "logistic":
        dom = LogisticRegression(random_state=seed, max_iter=2000, solver="lbfgs", class_weight="balanced")
    elif cfg.rw == "xgboost":
        dom = XGBClassifier(random_state=seed, objective="binary:logistic", eval_metric="auc", tree_method="hist", n_jobs=-1, n_estimators=300, max_depth=3, learning_rate=0.05, subsample=1.0, colsample_bytree=0.9, reg_lambda=1.0)
    else:
        raise ValueError(f"Unsupported reweight kind: {cfg.rw}")

    x = np.vstack([xs, xt])
    y = np.concatenate([np.zeros(xs.shape[0], dtype=int), np.ones(xt.shape[0], dtype=int)])
    dom.fit(x, y)
    p = np.clip(dom.predict_proba(xs)[:, 1], 1e-6, 1 - 1e-6)
    pis = xs.shape[0] / (xs.shape[0] + xt.shape[0])
    pit = xt.shape[0] / (xs.shape[0] + xt.shape[0])
    wr = (p / (1.0 - p)) * (pis / pit)

    if cfg.clip_mode == "fixed":
        lo = float(cfg.clip_min)
        hi = float(cfg.clip_max)
    elif cfg.clip_mode == "p1p99":
        lo = float(np.percentile(wr, 1))
        hi = float(np.percentile(wr, 99))
    else:
        lo = float(np.min(wr))
        hi = float(np.max(wr))

    wc = np.clip(wr, lo, hi)
    w = wc / np.mean(wc)
    diag = {
        "round_id": cfg.rid,
        "reweight": cfg.rw,
        "clip_mode": cfg.clip_mode,
        "clip_lower": lo,
        "clip_upper": hi,
        "raw_mean": float(np.mean(wr)),
        "raw_std": float(np.std(wr)),
        "raw_p1": float(np.percentile(wr, 1)),
        "raw_p50": float(np.percentile(wr, 50)),
        "raw_p99": float(np.percentile(wr, 99)),
        "pct_clipped_low": float(np.mean(wr < lo)),
        "pct_clipped_high": float(np.mean(wr > hi)),
        "final_mean": float(np.mean(w)),
        "final_std": float(np.std(w)),
        "final_min": float(np.min(w)),
        "final_max": float(np.max(w)),
        "n_source": int(xs.shape[0]),
        "n_target": int(xt.shape[0]),
    }
    return w, diag


def feature_diag(source: pd.DataFrame, target: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    rows = []
    for c in cols:
        a = pd.to_numeric(source[c], errors="coerce").dropna().to_numpy()
        b = pd.to_numeric(target[c], errors="coerce").dropna().to_numpy()
        if len(a) == 0 or len(b) == 0:
            continue
        ks, p = ks_2samp(a, b)
        p1, p99 = np.percentile(a, [1, 99])
        rows.append({
            "feature": c,
            "source_q01": float(np.percentile(a, 1)),
            "source_q50": float(np.percentile(a, 50)),
            "source_q99": float(np.percentile(a, 99)),
            "target_q01": float(np.percentile(b, 1)),
            "target_q50": float(np.percentile(b, 50)),
            "target_q99": float(np.percentile(b, 99)),
            "ks_stat": float(ks),
            "ks_pvalue": float(p),
            "pct_target_outside_source_p1_p99": float(np.mean((b < p1) | (b > p99))),
        })
    return pd.DataFrame(rows).sort_values("ks_stat", ascending=False)


def main() -> None:
    args = parse_args()
    np.random.seed(args.seed)
    if args.max_rounds < 1 or args.max_rounds > 5:
        raise ValueError("max_rounds must be between 1 and 5")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    cpath = Path(args.chicago_data)
    npath = Path(args.nibrs_data)
    if not cpath.exists() or not npath.exists():
        raise FileNotFoundError("Missing chicago-data or nibrs-data")

    chi = pd.read_csv(cpath)
    ni = pd.read_csv(npath)
    for col in ["month", "target_month"]:
        if col in chi.columns:
            chi[col] = pd.to_datetime(chi[col], errors="coerce")
        if col in ni.columns:
            ni[col] = pd.to_datetime(ni[col], errors="coerce")

    need_chi = BASE + ["split", "label", "community_area", "month", "target_month"]
    need_ni = BASE + ["label", "state_abbr", "target_month"]
    miss_chi = [c for c in need_chi if c not in chi.columns]
    miss_ni = [c for c in need_ni if c not in ni.columns]
    if miss_chi or miss_ni:
        raise ValueError(f"Missing columns: chicago={miss_chi}, nibrs={miss_ni}")

    chi_tr = chi[chi["split"] == "train"].copy()
    chi_va = chi[chi["split"] == "val"].copy()
    if chi_tr.empty or chi_va.empty:
        raise ValueError("Chicago train/val split empty")

    ni_review, ni_holdout, ni_meta = split_nibrs(ni, args.review_end_month, args.holdout_start_month)

    chi_pop = load_chicago_pop(Path(args.chicago_pop_zip))
    st_pop = load_state_pop_2024(args.state_pop_url, Path(args.state_pop_cache))
    chi2, ni2, pop_audit = add_population_and_popnorm(chi, ni, chi_pop, st_pop)
    pop_audit.to_csv(out / "population_join_audit.csv", index=False)

    chi2_tr = chi2[chi2["split"] == "train"].copy()
    chi2_va = chi2[chi2["split"] == "val"].copy()
    ni2_review, ni2_holdout, _ = split_nibrs(ni2, args.review_end_month, args.holdout_start_month)

    rounds = [
        RoundCfg("R0", "baseline_standardized", False),
        RoundCfg("R1", "population_norm_only", True),
        RoundCfg("R2", "population_norm_plus_reweight_logistic_clip_0.2_5", True, "logistic", "fixed", 0.2, 5.0),
        RoundCfg("R3", "population_norm_plus_reweight_logistic_clip_0.1_10", True, "logistic", "fixed", 0.1, 10.0),
        RoundCfg("R4", "population_norm_plus_reweight_xgboost_clip_p1p99", True, "xgboost", "p1p99"),
    ][: args.max_rounds]

    review_rows: List[Dict[str, object]] = []
    weight_rows: List[Dict[str, object]] = []
    store: Dict[Tuple[str, str], Dict[str, object]] = {}

    for rc in rounds:
        cols = POPN if rc.use_pop else BASE
        tr = chi2_tr if rc.use_pop else chi_tr
        va = chi2_va if rc.use_pop else chi_va
        rv = ni2_review if rc.use_pop else ni_review

        med, sc = fit_stats(tr, cols)
        xtr = tx(tr, cols, med, sc)
        xva = tx(va, cols, med, sc)
        xrv = tx(rv, cols, med, sc)

        ytr = pd.to_numeric(tr["label"], errors="coerce").fillna(0).to_numpy(dtype=int)
        yva = pd.to_numeric(va["label"], errors="coerce").fillna(0).to_numpy(dtype=int)
        yrv = pd.to_numeric(rv["label"], errors="coerce").fillna(0).to_numpy(dtype=int)

        spw = (len(ytr) - int(ytr.sum())) / int(ytr.sum()) if int(ytr.sum()) > 0 else 1.0
        models = build_models(args.seed, spw)

        w, wdiag = domain_weights(xtr, xrv, rc, args.seed)
        weight_rows.append(wdiag)

        for mname, m in models.items():
            if rc.rw is None:
                m.fit(xtr, ytr)
            else:
                m.fit(xtr, ytr, sample_weight=w)

            pva = m.predict_proba(xva)[:, 1]
            t = best_t(yva, pva)
            mva = metrics(yva, pva, t)
            prv = m.predict_proba(xrv)[:, 1]
            mrv = metrics(yrv, prv, t)

            review_rows.append({
                "round_id": rc.rid,
                "round_desc": rc.desc,
                "model": mname,
                "use_popnorm": rc.use_pop,
                "reweight_kind": rc.rw or "none",
                "clip_mode": rc.clip_mode or "none",
                "threshold_from_chicago_val": t,
                "chicago_val_roc_auc": mva["roc_auc"],
                "chicago_val_pr_auc": mva["pr_auc"],
                "nibrs_review_roc_auc": mrv["roc_auc"],
                "nibrs_review_pr_auc": mrv["pr_auc"],
                "nibrs_review_f1": mrv["f1"],
                "nibrs_review_recall": mrv["recall"],
                "nibrs_review_precision": mrv["precision"],
                "nibrs_review_accuracy": mrv["accuracy"],
            })

            pr = rv.copy()
            pr["pred_prob"] = prv
            pr["pred_label"] = (prv >= t).astype(int)
            keep = [c for c in ["state_abbr", "month", "target_month", "label", "pred_prob", "pred_label"] if c in pr.columns]
            pr[keep].to_csv(out / f"nibrs_review_predictions_{rc.rid}_{mname}.csv", index=False)

            store[(rc.rid, mname)] = {"model": m, "thr": t, "med": med, "sc": sc, "cols": cols, "use_pop": rc.use_pop}

        print(f"{rc.rid} done: {rc.desc}")

    rev = pd.DataFrame(review_rows).sort_values(["nibrs_review_roc_auc", "nibrs_review_pr_auc"], ascending=[False, False])
    rev.to_csv(out / "round_metrics_review.csv", index=False)
    pd.DataFrame(weight_rows).to_csv(out / "domain_weight_diagnostics.csv", index=False)
    if rev.empty:
        raise RuntimeError("No review metrics")

    champ = rev.iloc[0].to_dict()
    cr, cm = str(champ["round_id"]), str(champ["model"])
    cb = store[(cr, cm)]

    ho = ni2_holdout if cb["use_pop"] else ni_holdout
    xh = tx(ho, cb["cols"], cb["med"], cb["sc"])
    yh = pd.to_numeric(ho["label"], errors="coerce").fillna(0).to_numpy(dtype=int)
    ph = cb["model"].predict_proba(xh)[:, 1]
    chm = metrics(yh, ph, float(cb["thr"]))

    bb = store.get(("R0", cm))
    if bb is None:
        raise RuntimeError("Missing R0 baseline model for champion comparison")
    xhb = tx(ni_holdout, bb["cols"], bb["med"], bb["sc"])
    phb = bb["model"].predict_proba(xhb)[:, 1]
    bsm = metrics(yh, phb, float(bb["thr"]))

    pd.DataFrame([
        {"variant": "baseline_R0_same_model", "model": cm, "round_id": "R0", "threshold": float(bb["thr"]), "holdout_roc_auc": bsm["roc_auc"], "holdout_pr_auc": bsm["pr_auc"], "holdout_f1": bsm["f1"], "holdout_recall": bsm["recall"], "holdout_precision": bsm["precision"], "holdout_accuracy": bsm["accuracy"]},
        {"variant": "champion", "model": cm, "round_id": cr, "threshold": float(cb["thr"]), "holdout_roc_auc": chm["roc_auc"], "holdout_pr_auc": chm["pr_auc"], "holdout_f1": chm["f1"], "holdout_recall": chm["recall"], "holdout_precision": chm["precision"], "holdout_accuracy": chm["accuracy"]},
    ]).to_csv(out / "champion_metrics_holdout.csv", index=False)

    predh = ho.copy()
    predh["pred_prob"] = ph
    predh["pred_label"] = (ph >= float(cb["thr"])).astype(int)
    keep = [c for c in ["state_abbr", "month", "target_month", "label", "pred_prob", "pred_label"] if c in predh.columns]
    predh[keep].to_csv(out / "champion_holdout_predictions.csv", index=False)

    succ = bool(chm["roc_auc"] >= (bsm["roc_auc"] + 0.03) and chm["pr_auc"] >= bsm["pr_auc"])

    ref_path = Path("model/NIRBS/zero_shot_standardized_chi_ref/zero_shot_metrics.csv")
    aligns: List[Dict[str, object]] = []
    if ref_path.exists():
        ref = pd.read_csv(ref_path)
        ni_all = ni[ni["split"] == "test"].copy() if "split" in ni.columns and (ni["split"] == "test").any() else ni.copy()
        yall = pd.to_numeric(ni_all["label"], errors="coerce").fillna(0).to_numpy(dtype=int)
        for m in ["logistic_regression", "random_forest", "xgboost"]:
            b = store.get(("R0", m))
            if b is None:
                continue
            pall = b["model"].predict_proba(tx(ni_all, b["cols"], b["med"], b["sc"]))[:, 1]
            roc = float(roc_auc_score(yall, pall))
            pr = float(average_precision_score(yall, pall))
            r = ref[ref["model"] == m]
            if r.empty:
                continue
            aligns.append({"model": m, "baseline_r0_roc_auc": roc, "baseline_ref_roc_auc": float(r.iloc[0]["nibrs_roc_auc"]), "delta_roc_auc": roc - float(r.iloc[0]["nibrs_roc_auc"]), "baseline_r0_pr_auc": pr, "baseline_ref_pr_auc": float(r.iloc[0]["nibrs_pr_auc"]), "delta_pr_auc": pr - float(r.iloc[0]["nibrs_pr_auc"])})
    pd.DataFrame(aligns).to_csv(out / "baseline_alignment_check.csv", index=False)

    feature_diag(chi2_tr, ni2_review, POPN).to_csv(out / "feature_alignment_diagnostics.csv", index=False)

    (out / "champion_config.json").write_text(json.dumps({
        "champion_round_id": cr,
        "champion_model": cm,
        "champion_review_roc_auc": float(champ["nibrs_review_roc_auc"]),
        "champion_review_pr_auc": float(champ["nibrs_review_pr_auc"]),
        "holdout_baseline_roc_auc": bsm["roc_auc"],
        "holdout_baseline_pr_auc": bsm["pr_auc"],
        "holdout_champion_roc_auc": chm["roc_auc"],
        "holdout_champion_pr_auc": chm["pr_auc"],
        "success_by_locked_criteria": succ,
        "criteria": {"roc_auc_at_least_baseline_plus": 0.03, "pr_auc_not_lower_than_baseline": True},
    }, indent=2), encoding="utf-8")

    (out / "experiment_config.json").write_text(json.dumps({
        "args": vars(args),
        "rounds_executed": [r.rid for r in rounds],
        "nibrs_partition_stats": ni_meta,
        "baseline_feature_cols": BASE,
        "popnorm_feature_cols": POPN,
    }, indent=2), encoding="utf-8")

    joblib.dump(cb["model"], out / "champion_model.joblib")
    joblib.dump(cb["sc"], out / "champion_scaler.joblib")
    (out / "champion_medians.json").write_text(json.dumps(cb["med"], indent=2), encoding="utf-8")

    print("Saved outputs to", out)
    print("Champion", cr, cm)
    print("Holdout ROC/PR baseline->champion", f"{bsm['roc_auc']:.4f}/{bsm['pr_auc']:.4f}", "->", f"{chm['roc_auc']:.4f}/{chm['pr_auc']:.4f}")
    print("Success by locked criteria:", succ)


if __name__ == "__main__":
    main()
