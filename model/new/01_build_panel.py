#!/usr/bin/env python3
"""Build community_area-month panel from raw Chicago crime CSV files."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, Tuple

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--crime-files",
        nargs="+",
        default=["crimes_2015_2024.csv", "crimes_2025_2026.csv"],
        help="Input crime CSV files.",
    )
    parser.add_argument(
        "--out-base",
        default="data_processed/panel_monthly_base.csv",
        help="Output path for monthly area panel with totals/arrest rate.",
    )
    parser.add_argument(
        "--out-type-counts",
        default="data_processed/panel_monthly_type_counts.csv",
        help="Output path for monthly area x type counts.",
    )
    parser.add_argument("--start-month", default="2015-01", help="Start month (YYYY-MM).")
    parser.add_argument("--end-month", default="2025-12", help="End month (YYYY-MM).")
    parser.add_argument("--min-area", type=int, default=1)
    parser.add_argument("--max-area", type=int, default=77)
    parser.add_argument("--chunksize", type=int, default=400_000)
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
    base_acc: Dict[Tuple[int, pd.Timestamp], list] = defaultdict(lambda: [0, 0])
    type_acc: Dict[Tuple[int, pd.Timestamp, str], int] = defaultdict(int)

    for file_path in files:
        print(f"Processing: {file_path}")
        for chunk in iterate_chunks(file_path, chunksize=chunksize):
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

    base_rows = [
        {
            "community_area": area,
            "month": month,
            "count_total": vals[0],
            "count_arrest": vals[1],
        }
        for (area, month), vals in base_acc.items()
    ]
    base_df = pd.DataFrame(base_rows)

    type_rows = [
        {
            "community_area": area,
            "month": month,
            "primary_type": ptype,
            "type_count": cnt,
        }
        for (area, month, ptype), cnt in type_acc.items()
    ]
    type_df = pd.DataFrame(type_rows)

    return base_df, type_df


def main() -> None:
    args = parse_args()

    files = [Path(p) for p in args.crime_files]
    for file_path in files:
        if not file_path.exists():
            raise FileNotFoundError(f"Missing input file: {file_path}")

    out_base = Path(args.out_base)
    out_type = Path(args.out_type_counts)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    out_type.parent.mkdir(parents=True, exist_ok=True)

    start_month = pd.Period(args.start_month, freq="M").to_timestamp()
    end_month = pd.Period(args.end_month, freq="M").to_timestamp()

    base_df, type_df = build_aggregates(
        files=files,
        start_month=start_month,
        end_month=end_month,
        min_area=args.min_area,
        max_area=args.max_area,
        chunksize=args.chunksize,
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

    panel.to_csv(out_base, index=False)
    type_df.to_csv(out_type, index=False)

    print(f"Saved base panel: {out_base} (rows={len(panel)})")
    print(f"Saved type counts: {out_type} (rows={len(type_df)})")


if __name__ == "__main__":
    main()
