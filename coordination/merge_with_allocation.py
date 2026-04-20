"""
Merge reason classifications with allocation (distance + probability + nearest_type)
=====================================================================================
Works at BOTH call-level and pair-level:
    - Call-level input: investigative/calls_resolved.csv (one row per call_id,
      resolved to the correct partner via time-proximity in aggregate_per_pair.py).
      Use case: "among calls in distance decile D, what's the reason mix".
    - Pair-level input: investigative/pair_aggregated.csv (one row per
      mobile,partner_id with UNION of reasons across calls). Use case: "among
      pairs in D10, what fraction ever touched address_not_clear".

Deciles are computed over the FULL Jan-Mar 2026 Delhi non-BDO allocation cohort
(not just the calls subset), so decile ranks are apples-to-apples with
../location_accuracy/ methodology.

Run from: analyses/data/partner_customer_calls/
    python merge_with_allocation.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
from db_connectors import get_snow_connection


HERE      = Path(__file__).resolve().parent
OUT_DIR   = HERE / "investigative"
OUT_DIR.mkdir(exist_ok=True)

ALLOC_SQL        = HERE / "query_allocation.txt"
CALLS_RESOLVED   = OUT_DIR / "calls_resolved.csv"
PAIR_AGGREGATED  = OUT_DIR / "pair_aggregated.csv"

ALLOC_RAW_CSV    = OUT_DIR / "allocation_cohort.csv"
CALL_MERGED_CSV  = OUT_DIR / "calls_with_alloc.csv"
PAIR_MERGED_CSV  = OUT_DIR / "pairs_with_alloc.csv"
CALL_DIST_CSV    = OUT_DIR / "callLevel_reason_by_distance_decile.csv"
CALL_PROB_CSV    = OUT_DIR / "callLevel_reason_by_prob_decile.csv"
CALL_TYPE_CSV    = OUT_DIR / "callLevel_reason_by_nearest_type.csv"
PAIR_DIST_CSV    = OUT_DIR / "pairLevel_reason_by_distance_decile.csv"
PAIR_PROB_CSV    = OUT_DIR / "pairLevel_reason_by_prob_decile.csv"


def load_sql(path):
    with open(path) as f:
        return f.read().strip().rstrip(";")


def pct_crosstab(df, row, col, count_col=None):
    counts = pd.crosstab(df[row], df[col], dropna=False)
    pct = (counts.div(counts.sum(axis=1), axis=0) * 100).round(1)
    pct["_total"] = counts.sum(axis=1)
    return pct


def main():
    assert CALLS_RESOLVED.exists() and PAIR_AGGREGATED.exists(), \
        "Run aggregate_per_pair.py first"

    # ---- Pull allocation cohort ----
    conn = get_snow_connection()
    assert conn is not None
    print("PULLING allocation cohort (Jan-Mar 2026 Delhi non-BDO) ...")
    alloc = pd.read_sql(load_sql(ALLOC_SQL), conn)
    alloc.columns = [c.lower() for c in alloc.columns]
    print(f"  alloc rows: {len(alloc):,}  unique (mob,partner): {alloc[['mobile','partner_id']].drop_duplicates().shape[0]:,}")
    alloc.to_csv(ALLOC_RAW_CSV, index=False)
    conn.close()

    # Deduplicate to one row per (mobile, partner_id) at latest allocation
    alloc = alloc.sort_values("allocated_at").drop_duplicates(
        ["mobile", "partner_id"], keep="last")

    # ---- Compute deciles over the FULL allocation cohort ----
    alloc = alloc.dropna(subset=["nearest_distance"]).copy()
    alloc["distance_decile"] = pd.qcut(alloc["nearest_distance"], 10, labels=False,
                                        duplicates="drop") + 1
    if alloc["probability"].notna().sum() > 0:
        alloc_p = alloc.dropna(subset=["probability"]).copy()
        alloc_p["prob_decile"] = pd.qcut(alloc_p["probability"], 10, labels=False,
                                          duplicates="drop") + 1
        alloc = alloc.merge(
            alloc_p[["mobile", "partner_id", "prob_decile"]],
            on=["mobile", "partner_id"], how="left")
    else:
        alloc["prob_decile"] = np.nan

    alloc_cols = ["mobile", "partner_id", "nearest_distance", "nearest_type",
                  "probability", "distance_decile", "prob_decile"]
    for c in ["mobile", "partner_id"]:
        alloc[c] = alloc[c].astype(str)
    alloc_slim = alloc[alloc_cols]

    # ====================================================================
    # CALL-LEVEL MERGE
    # ====================================================================
    print("\n" + "=" * 70)
    print("CALL-LEVEL MERGE")
    print("=" * 70)
    calls = pd.read_csv(CALLS_RESOLVED)
    for c in ["mobile", "partner_id"]:
        calls[c] = calls[c].astype(str)
    call_m = calls.merge(alloc_slim, on=["mobile", "partner_id"], how="left")
    call_m.to_csv(CALL_MERGED_CSV, index=False)
    print(f"merged calls: {len(call_m):,}  with distance_decile: "
          f"{call_m['distance_decile'].notna().sum():,}")

    dist_x = pct_crosstab(call_m, "distance_decile", "primary_reason")
    dist_x.to_csv(CALL_DIST_CSV)
    print("\nCALL-LEVEL — reason % by distance decile:")
    print(dist_x.to_string())

    prob_x = pct_crosstab(call_m, "prob_decile", "primary_reason")
    prob_x.to_csv(CALL_PROB_CSV)
    print("\nCALL-LEVEL — reason % by prob decile:")
    print(prob_x.to_string())

    type_x = pct_crosstab(call_m, "nearest_type", "primary_reason")
    type_x.to_csv(CALL_TYPE_CSV)
    print("\nCALL-LEVEL — reason % by nearest_type:")
    print(type_x.to_string())

    # ====================================================================
    # PAIR-LEVEL MERGE (capture multi-call pairs)
    # ====================================================================
    print("\n" + "=" * 70)
    print("PAIR-LEVEL MERGE — union of reasons across calls for same (mob,partner)")
    print("=" * 70)
    pair = pd.read_csv(PAIR_AGGREGATED)
    for c in ["mobile", "partner_id"]:
        pair[c] = pair[c].astype(str)
    pair_m = pair.merge(alloc_slim, on=["mobile", "partner_id"], how="left")
    pair_m.to_csv(PAIR_MERGED_CSV, index=False)
    print(f"merged pairs: {len(pair_m):,}  with distance_decile: "
          f"{pair_m['distance_decile'].notna().sum():,}")

    # Explode so each row = (pair, reason). Tells us: "among pairs in decile D,
    # what fraction TOUCHED reason R at least once across calls?"
    pair_m["reasons_list"] = pair_m["reasons_union"].fillna("").str.split(",")
    exploded = pair_m.explode("reasons_list").rename(columns={"reasons_list": "reason"})
    exploded = exploded[exploded["reason"].astype(str).str.len() > 0]

    def touch_rate(row_col, row_name):
        # For each decile/bucket: fraction of pairs that touched each reason
        n_pairs_per_bucket = pair_m.groupby(row_col)["mobile"].count()
        touched = exploded.groupby([row_col, "reason"])["mobile"].count()
        out = (touched.unstack(fill_value=0).div(n_pairs_per_bucket, axis=0) * 100).round(1)
        out["_n_pairs"] = n_pairs_per_bucket
        return out

    d_pair = touch_rate("distance_decile", "distance_decile")
    d_pair.to_csv(PAIR_DIST_CSV)
    print("\nPAIR-LEVEL — % of pairs that TOUCHED each reason, by distance decile:")
    print(d_pair.to_string())

    p_pair = touch_rate("prob_decile", "prob_decile")
    p_pair.to_csv(PAIR_PROB_CSV)
    print("\nPAIR-LEVEL — % of pairs that TOUCHED each reason, by prob decile:")
    print(p_pair.to_string())

    print(f"\nWROTE:\n  {CALL_MERGED_CSV}\n  {PAIR_MERGED_CSV}\n"
          f"  {CALL_DIST_CSV}\n  {CALL_PROB_CSV}\n  {CALL_TYPE_CSV}\n"
          f"  {PAIR_DIST_CSV}\n  {PAIR_PROB_CSV}")


if __name__ == "__main__":
    main()
