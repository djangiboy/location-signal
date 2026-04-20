"""
Pull final task_logs event per (mobile, partner) and merge with pair_aggregated.

Input:
    query_final_event.txt
    investigative/pair_aggregated.csv
    investigative/pairs_with_alloc.csv

Output:
    investigative/final_events.csv          — raw query result (master cohort ~6,951)
    investigative/pair_aggregated_final.csv — pair_aggregated ⋈ final_event
    investigative/pairs_with_alloc_final.csv — pairs_with_alloc ⋈ final_event
    investigative/decline_remarks_distribution.csv
    investigative/final_event_by_address_friction.csv

Prints:
    - final_event distribution (by install outcome)
    - decline_remarks mix for the 380 non-installed address_not_clear pairs
    - cross-validation: does the transcript address_not_clear signal predict
      post-assign decline remarks also citing address?

Run from: partner_customer_calls/
    python pull_final_event.py
"""

from pathlib import Path
import re
import pandas as pd
from db_connectors import get_snow_connection


HERE   = Path(__file__).resolve().parent
INV    = HERE / "investigative"
SQL    = HERE / "query_final_event.txt"

OUT_RAW   = INV / "final_events.csv"
OUT_PAIR  = INV / "pair_aggregated_final.csv"
OUT_ALLOC = INV / "pairs_with_alloc_final.csv"
OUT_DECRX = INV / "decline_remarks_distribution.csv"
OUT_XTAB  = INV / "final_event_by_address_friction.csv"


# Address-decline regex (reused from location_accuracy — same bucketing).
ADDRESS_NOT_CLEAR_RX = re.compile(r"understand the address|पता समझ", re.I)
AREA_DECLINE_RX      = re.compile(
    r"feasible|fisible|fijebal|area|ariya|coverage|zone|outside|"
    r"location|serviceab|network|signal|line|cable|fiber|fibre|"
    r"range|reach|far|meters or more away", re.I)


def bucket_remarks(s):
    if not isinstance(s, str) or not s.strip():
        return "empty"
    if ADDRESS_NOT_CLEAR_RX.search(s): return "dropdown_address_not_clear"
    if AREA_DECLINE_RX.search(s):      return "dropdown_area_decline"
    return "other_remarks"


def main():
    conn = get_snow_connection()
    assert conn is not None

    with open(SQL) as f:
        query = f.read().strip().rstrip(";")

    print("PULLING final_event for master cohort (~6,951 pairs) ...")
    fe = pd.read_sql(query, conn)
    fe.columns = [c.lower() for c in fe.columns]
    fe["mobile"]     = fe["mobile"].astype(str)
    fe["partner_id"] = fe["partner_id"].astype(str)
    print(f"  rows: {len(fe):,}  unique pairs: {fe[['mobile','partner_id']].drop_duplicates().shape[0]:,}")
    fe.to_csv(OUT_RAW, index=False)
    conn.close()

    # final_event distribution
    print("\n=== FINAL EVENT DISTRIBUTION (master 6,951) ===")
    print(fe["final_event"].value_counts(dropna=False).to_string())

    # Post-assign DECLINE breakdown
    declined = fe[fe["decline_remarks"].notna()]
    print(f"\n=== POST-ASSIGN DECLINED pairs: {len(declined):,} ===")
    print(f"  with non-empty decline_remarks: {(declined['decline_remarks'].astype(str).str.strip()!='').sum():,}")

    # Bucket decline remarks
    fe["decline_bucket"] = fe["decline_remarks"].apply(bucket_remarks)
    print("\n=== decline_bucket distribution (all master pairs) ===")
    print(fe["decline_bucket"].value_counts(dropna=False).to_string())

    # Merge into pair_aggregated
    pa = pd.read_csv(INV / "pair_aggregated.csv")
    pa["mobile"]     = pa["mobile"].astype(str)
    pa["partner_id"] = pa["partner_id"].astype(str)
    m = pa.merge(
        fe[["mobile", "partner_id", "final_event", "final_remarks",
             "final_source", "final_time", "decline_remarks",
             "decline_source", "decline_time", "decline_bucket",
             "n_post_events", "n_otp_verified", "n_decline_post"]],
        on=["mobile", "partner_id"], how="left")
    m.to_csv(OUT_PAIR, index=False)
    print(f"\nMERGED pair_aggregated + final_event -> {OUT_PAIR}  ({len(m):,} rows)")

    # Same for pairs_with_alloc
    pw = pd.read_csv(INV / "pairs_with_alloc.csv")
    pw["mobile"]     = pw["mobile"].astype(str)
    pw["partner_id"] = pw["partner_id"].astype(str)
    mw = pw.merge(
        fe[["mobile", "partner_id", "final_event", "final_remarks",
             "final_source", "decline_remarks", "decline_source",
             "decline_bucket", "n_post_events", "n_otp_verified",
             "n_decline_post"]],
        on=["mobile", "partner_id"], how="left")
    mw.to_csv(OUT_ALLOC, index=False)
    print(f"MERGED pairs_with_alloc + final_event -> {OUT_ALLOC}  ({len(mw):,} rows)")

    # =============================================================
    # CORE QUESTION: among transcript-flagged address_not_clear NON-INSTALLS,
    # what does the post-assign decline remark look like?
    # =============================================================
    ni = m[m["installed"] == 0].copy()
    print(f"\n=== NON-INSTALLED PAIRS in cohort with call data: {len(ni):,} ===")

    print("\n--- final_event for non-installed pairs ---")
    print(ni["final_event"].value_counts(dropna=False).to_string())

    print("\n--- decline_bucket for non-installed pairs ---")
    print(ni["decline_bucket"].value_counts(dropna=False).to_string())

    # Crosstab: transcript primary_first × decline_bucket on non-installs
    xt = pd.crosstab(
        ni["primary_first"].fillna("__none__"),
        ni["decline_bucket"].fillna("__none__"),
        margins=True, margins_name="TOT")
    xt.to_csv(OUT_XTAB)
    print(f"\n=== CROSSTAB transcript primary_first × decline_bucket (non-installs) ===")
    print(xt.to_string())

    # The sharpest cut: address_not_clear transcripts that DIDN'T install
    anc = ni[ni["primary_first"] == "address_not_clear"]
    print(f"\n=== TRANSCRIPT address_not_clear + NOT INSTALLED: {len(anc):,} ===")
    print("--- their final_event distribution ---")
    print(anc["final_event"].value_counts(dropna=False).to_string())
    print("\n--- their decline_bucket distribution ---")
    print(anc["decline_bucket"].value_counts(dropna=False).to_string())
    print(f"\n--- decline_remarks (raw text, top 20) ---")
    print(anc["decline_remarks"].value_counts(dropna=False).head(20).to_string())

    # Save the decline remarks distribution across the whole cohort
    dec_dist = m["decline_remarks"].value_counts(dropna=False).head(50).reset_index()
    dec_dist.columns = ["decline_remarks", "n"]
    dec_dist.to_csv(OUT_DECRX, index=False)
    print(f"\nWROTE {OUT_DECRX}")


if __name__ == "__main__":
    main()
