#Data preprocessing- NIBRS incident data in 2024 filtered by agency type = 'County'
from __future__ import annotations
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine
import urllib.parse
from collections import defaultdict
from typing import Dict, Iterable, Tuple
import pandas as pd
import argparse


# Set up database connection
CONFIG = {
    'user': 'root',
    'password': '***', 
    'host': 'localhost',
    'port': '3306',
    'database': 'crime_data',   
    'charset': 'utf8'   
}

table_name = 'incidents_in_counties'
safe_password = urllib.parse.quote_plus(CONFIG['password'])
def connection_to_mysql(safe_password):
    url = f"mysql+pymysql://{CONFIG['user']}:{safe_password}@{CONFIG['host']}:{CONFIG['port']}/{CONFIG['database']}?charset={CONFIG['charset']}"
    engine = create_engine(url)
    return engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    # parser.add_argument(
    #     "--crime-files",
    #     nargs="+",
    #     default=["crimes_2015_2024.csv", "crimes_2025_2026.csv"],
    #     help="Input crime CSV files.",
    # )
    parser.add_argument(
        "--out-base",
        default="data_processed/NIBRS_panel_monthly_base.csv",
        help="Output path for monthly area panel with totals/arrest rate.",
    )
    parser.add_argument(
        "--out-type-counts",
        default="data_processed/NIBRS_panel_monthly_type_counts.csv",
        help="Output path for monthly area x type counts.",
    )
    parser.add_argument("--start-month", default="2024-01", help="Start month (YYYY-MM).")
    parser.add_argument("--end-month", default="2024-12", help="End month (YYYY-MM).")
    # parser.add_argument("--min-area", type=int, default=1)
    # parser.add_argument("--max-area", type=int, default=77)
    parser.add_argument("--chunksize", type=int, default=400_000)
    return parser.parse_args()

def to_bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .notna()
        .astype(int)
    )

#arrestee_id 列中非空值表示被逮捕，空值表示未被逮捕，因此可以使用 notna() 来判断是否被逮捕，并将结果转换为整数类型（1 表示被逮捕，0 表示未被逮捕）。
def iterate_chunks(engine,chunksize=400000) -> Iterable[pd.DataFrame]:
    usecols = ["INCIDENT_DATE", "state_abbr", "arrested", "chicago_primary_type","INCIDENT_ID"]
    query = f"SELECT {', '.join(usecols)} FROM {table_name}" 
    return pd.read_sql(query, con=engine, chunksize=chunksize)



def build_aggregates(
    start_month: pd.Timestamp,
    end_month: pd.Timestamp,
    chunksize: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    base_acc: Dict[Tuple[int, pd.Timestamp], list] = defaultdict(lambda: [0, 0])
    type_acc: Dict[Tuple[int, pd.Timestamp, str], int] = defaultdict(int)
    for chunk in iterate_chunks(connection_to_mysql(safe_password), chunksize=chunksize):
        chunk = chunk.dropna(subset=["state_abbr", "INCIDENT_DATE"])
        chunk["state_abbr"] = chunk["state_abbr"].astype(str)
    
        chunk["month"] = pd.to_datetime(chunk["INCIDENT_DATE"], errors="coerce").dt.to_period("M").dt.to_timestamp()
        chunk = chunk.dropna(subset=["month"])
        chunk = chunk[(chunk["month"] >= start_month) & (chunk["month"] <= end_month)]
        if chunk.empty:
            continue


        # chunk["arrest_num"] = to_bool_series(chunk["arrested"])
        chunk["arrest_num"] = chunk["arrested"].astype(int)
        chunk["primary_type"] = chunk["chicago_primary_type"].fillna("UNKNOWN").astype(str)

        grouped = (
            chunk.groupby(["state_abbr", "month"], observed=True)
            .agg(count_total=("INCIDENT_ID", "size"), count_arrest=("arrest_num", "sum"))
            .reset_index()
        )
        for row in grouped.itertuples(index=False):
            key = (row.state_abbr, row.month)
            base_acc[key][0] += int(row.count_total)
            base_acc[key][1] += int(row.count_arrest)


        grouped_type = (
            chunk.groupby(["state_abbr", "month", "primary_type"], observed=True)
            .size()
            .reset_index(name="type_count")
        )
        for row in grouped_type.itertuples(index=False):
            key = (row.state_abbr, row.month, row.primary_type)
            type_acc[key] += int(row.type_count)



    base_rows = [
        {
            "state_abbr": area,
            "month": month,
            "count_total": vals[0],
            "count_arrest": vals[1],
        }
        for (area, month), vals in base_acc.items()
    ]
    base_df = pd.DataFrame(base_rows)



    type_rows = [
        {
            "state_abbr": area,
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
    out_base = Path(args.out_base)
    out_type = Path(args.out_type_counts)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    out_type.parent.mkdir(parents=True, exist_ok=True)

    start_month = pd.Period(args.start_month, freq="M").to_timestamp()
    end_month = pd.Period(args.end_month, freq="M").to_timestamp()

    base_df, type_df = build_aggregates(
        start_month=start_month,
        end_month=end_month,
        chunksize=args.chunksize,
    )

    month_range = pd.date_range(start_month, end_month, freq="MS")
    full_index = pd.MultiIndex.from_product(
        [[row["state_abbr"] for _, row in base_df[["state_abbr"]].drop_duplicates().iterrows()], month_range],
        names=["state_abbr", "month"],
    )
    full_df = full_index.to_frame(index=False)

    panel = full_df.merge(base_df, on=["state_abbr", "month"], how="left")
    panel["count_total"] = panel["count_total"].fillna(0).astype(int)
    panel["count_arrest"] = panel["count_arrest"].fillna(0).astype(int)
    panel["arrest_rate"] = 0.0
    nonzero = panel["count_total"] > 0
    panel.loc[nonzero, "arrest_rate"] = panel.loc[nonzero, "count_arrest"] / panel.loc[nonzero, "count_total"]

    type_df = type_df.sort_values(["state_abbr", "month", "primary_type"]).reset_index(drop=True)
    panel = panel.sort_values(["state_abbr", "month"]).reset_index(drop=True)

    panel.to_csv(out_base, index=False)
    type_df.to_csv(out_type, index=False)

    print(f"Saved base panel: {out_base} (rows={len(panel)})")
    print(f"Saved type counts: {out_type} (rows={len(type_df)})")


if __name__ == "__main__":
    main()


