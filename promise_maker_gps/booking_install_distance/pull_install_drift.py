"""
Pull Stage B cohort: Delhi Dec-2025 installed mobiles with
    booking_lat/lng (at serviceability check)
    install_lat/lng (first wifi_connected_location_captured, post-install)
    install_drift_m (haversine, SQL-side)
    bdo_lead flag, booking_accuracy, time_bucket

Runs query_install_drift.txt and writes the raw result to
investigations/install_drift_raw.csv. NO filtering here -- Python-side
filters (bdo_lead = 0, missing-coord drops) happen in build_drift.py so
the funnel is fully visible.

Breadcrumbs printed:
    TOTAL ROWS, BDO-VS-NON-BDO MIX, COVERAGE OF EACH COLUMN (NULL counts),
    INSTALL_DRIFT_M SUMMARY (count + p50/p75/p95 + NULL count)

Run from: promise_maker_gps/booking_install_distance/
    python pull_install_drift.py
"""

from pathlib import Path

import pandas as pd

from db_connectors import get_snow_connection


HERE = Path(__file__).resolve().parent
INV = HERE / "investigations"
SQL = HERE / "query_install_drift.txt"
OUT = INV / "install_drift_raw.csv"


def main():
    INV.mkdir(exist_ok=True)

    with open(SQL) as f:
        query = f.read().strip().rstrip(";")

    conn = get_snow_connection()
    assert conn is not None, "Snowflake connection failed"

    print("=" * 70)
    print("PULL_INSTALL_DRIFT  --  Delhi Dec-2025 installed cohort")
    print("=" * 70)
    print("Executing query (may take ~30s) ...")
    a = pd.read_sql(query, conn)
    conn.close()

    a.columns = [c.lower() for c in a.columns]
    a["mobile"] = a["mobile"].astype(str).str.strip()
    for c in ("fee_captured_at", "installed_at", "booking_loc_time", "install_ping_time"):
        if c in a.columns:
            a[c] = pd.to_datetime(a[c])

    # ------------------------------------------------------------------
    # Breadcrumbs
    # ------------------------------------------------------------------
    print(f"\n=== RAW PULL ===")
    print(f"ROWS                      : {len(a):,}")
    print(f"UNIQUE MOBILES            : {a['mobile'].nunique():,}")
    print(f"  (expect rows == unique mobiles since cohort is keyed on mobile)")

    print(f"\n=== BDO MIX (Python-side filter will drop bdo_lead=1) ===")
    print(a["bdo_lead"].value_counts(dropna=False).rename_axis("bdo_lead").reset_index(name="n").to_string(index=False))

    non_bdo = a[a["bdo_lead"] == 0]
    print(f"\nNon-BDO rows              : {len(non_bdo):,}  "
          f"({len(non_bdo)/len(a):.1%} of cohort)")

    # ------------------------------------------------------------------
    # Column coverage: how many rows have each critical field
    # ------------------------------------------------------------------
    print(f"\n=== COLUMN COVERAGE (non-null counts, non-BDO cohort n={len(non_bdo):,}) ===")
    critical = [
        "fee_captured_at", "booking_lat", "booking_lng", "booking_accuracy",
        "installed_at", "install_lat", "install_lng", "install_ping_time",
        "install_drift_m", "time_bucket",
    ]
    rows = []
    for c in critical:
        nn = int(non_bdo[c].notna().sum())
        rows.append({
            "column": c,
            "non_null": nn,
            "null": len(non_bdo) - nn,
            "coverage": f"{nn/len(non_bdo):.1%}",
        })
    print(pd.DataFrame(rows).to_string(index=False))

    # ------------------------------------------------------------------
    # install_drift_m quick look (non-BDO, non-null)
    # ------------------------------------------------------------------
    d = non_bdo["install_drift_m"].dropna()
    print(f"\n=== install_drift_m quicklook (non-BDO, non-null rows = {len(d):,}) ===")
    print(f"  p50  : {d.quantile(0.50):>8.1f} m")
    print(f"  p75  : {d.quantile(0.75):>8.1f} m")
    print(f"  p90  : {d.quantile(0.90):>8.1f} m")
    print(f"  p95  : {d.quantile(0.95):>8.1f} m")
    print(f"  p99  : {d.quantile(0.99):>8.1f} m")
    print(f"  max  : {d.max():>8.1f} m")
    print(f"  Stage A p95 (jitter floor for subtraction): 154.8 m")
    within_155 = (d <= 154.76).sum()
    print(f"  drifts within Stage A p95 (=apparatus noise) : "
          f"{within_155:,} / {len(d):,} ({within_155/len(d):.1%})")
    within_25 = (d <= 25).sum()
    print(f"  drifts within 25m (Promise Maker gate)       : "
          f"{within_25:,} / {len(d):,} ({within_25/len(d):.1%})")

    a.to_csv(OUT, index=False)
    print(f"\nSAVED: {OUT.relative_to(HERE.parent.parent)}  ({len(a):,} rows)")


if __name__ == "__main__":
    main()
