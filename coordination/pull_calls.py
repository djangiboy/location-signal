"""
Pull Partner -> Customer Call Recordings -- Delhi / Dec 2025 (non-BDO)
=======================================================================
Executes query_pcalls.txt and writes a recordings manifest to
investigative/calls_manifest.csv.

One row = one call, scoped to a (mobile, partner_id) assignment window.
Each row carries the decision_event + decision_reason from task_logs so the
transcript-level classification (downstream) can be cross-validated against
the existing address-not-clear / area-decline regex analysis in
../location_accuracy/.

Run from: analyses/data/partner_customer_calls/
    python pull_calls.py
"""

from pathlib import Path
import pandas as pd
from db_connectors import get_snow_connection


HERE     = Path(__file__).resolve().parent
OUT_DIR  = HERE / "investigative"
OUT_DIR.mkdir(exist_ok=True)

QUERY_FILE = HERE / "query_pcalls.txt"
OUT_CSV    = OUT_DIR / "calls_manifest.csv"


def load_query(path):
    """Read a SQL file, strip trailing semicolon (Snowflake single-stmt rule)."""
    with open(path, "r") as f:
        return f.read().strip().rstrip(";")


def main():
    print("=" * 70)
    print("PULL_CALLS — extract recording URLs for non-BDO Delhi Dec-2025")
    print("=" * 70)

    conn = get_snow_connection()
    assert conn is not None, "Snowflake connection failed"

    query = load_query(QUERY_FILE)

    print("EXECUTING QUERY ...")
    df = pd.read_sql(query, conn)
    df.columns = [c.lower() for c in df.columns]
    print(f"ROWS RETURNED: {len(df):,}")

    # Quick descriptives before writing
    print("\nCOHORT DESCRIPTIVES")
    print(f"  unique mobiles      : {df['mobile'].nunique():,}")
    print(f"  unique (mob,partner): {df[['mobile','partner_id']].drop_duplicates().shape[0]:,}")
    print(f"  unique call_ids     : {df['call_id'].nunique():,}")
    print(f"  recording_url != null: {df['recording_url'].notna().sum():,}")

    print("\nCALL STATUS MIX")
    print(df["call_status"].value_counts(dropna=False).to_string())

    print("\nDECISION EVENT MIX (per call row)")
    print(df["decision_event"].value_counts(dropna=False).to_string())

    print("\nINSTALLED MIX (per call row)")
    print(df["installed"].value_counts(dropna=False).to_string())

    df.to_csv(OUT_CSV, index=False)
    print(f"\nWROTE: {OUT_CSV} ({len(df):,} rows)")

    conn.close()


if __name__ == "__main__":
    main()
