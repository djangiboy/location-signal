"""
Pull wifi_connected_location_captured events for Stage A (GPS jitter baseline).

Runs query_getlatlong.txt against Snowflake, writes the raw result to
investigations/wifi_pings_raw.csv. NO filtering here -- every row returned by
the query lands in the CSV. Filtering (15-min dedup, 250m cap, >=3 pings)
happens in build_jitter.py so each step's attrition is visible.

Breadcrumbs printed:
    ROWS, UNIQUE MOBILES, DATE RANGE, PINGS-PER-MOBILE DISTRIBUTION

Run from: promise_maker_gps/gps_jitter/
    python pull_wifi_pings.py
"""

from pathlib import Path

import pandas as pd

from db_connectors import get_snow_connection


HERE = Path(__file__).resolve().parent
INV = HERE / "investigations"
SQL = HERE / "query_getlatlong.txt"
OUT_RAW = INV / "wifi_pings_raw.csv"


def main():
    INV.mkdir(exist_ok=True)

    with open(SQL) as f:
        query = f.read().strip().rstrip(";")

    conn = get_snow_connection()
    assert conn is not None, "Snowflake connection failed"

    print("PULLING wifi_connected_location_captured (2025-09-01 to 2026-01-26) ...")
    a = pd.read_sql(query, conn)
    conn.close()

    a.columns = [c.lower() for c in a.columns]
    a["mobile"] = a["mobile"].astype(str).str.strip()
    a["added_time"] = pd.to_datetime(a["added_time"])

    print(f"\n=== RAW PULL ===")
    print(f"ROWS              : {len(a):,}")
    print(f"UNIQUE MOBILES    : {a['mobile'].nunique():,}")
    print(f"DATE RANGE        : {a['added_time'].min()}  ->  {a['added_time'].max()}")
    print(f"NULL lat/lng rows : {a[['install_lat','install_lng']].isna().any(axis=1).sum():,}")

    # Pings-per-mobile distribution -- ties back to the "mobiles with >=3 pings" filter
    b = a.groupby("mobile").size().rename("n_pings").reset_index()
    print(f"\n=== PINGS PER MOBILE ===")
    print(f"MIN / MEDIAN / MAX: {b['n_pings'].min()} / {b['n_pings'].median():.0f} / {b['n_pings'].max()}")
    c = b["n_pings"].value_counts().sort_index().head(10)
    print(f"HISTOGRAM (n_pings -> n_mobiles, top 10):")
    for n, m in c.items():
        print(f"  {int(n):>3} pings : {m:>7,} mobiles")
    print(f"  ...")
    print(f"  >=3 pings  : {(b['n_pings'] >= 3).sum():>7,} mobiles "
          f"({(b['n_pings'] >= 3).sum() / len(b):.1%} of raw)")

    a.to_csv(OUT_RAW, index=False)
    print(f"\nSAVED: {OUT_RAW.relative_to(HERE.parent.parent)}  ({len(a):,} rows)")


if __name__ == "__main__":
    main()
