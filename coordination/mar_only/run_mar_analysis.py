"""
March-only pair-level decile analysis
======================================
Filters the parent's pair_aggregated.csv to March-2026-assigned pairs, pulls
a March-only allocation cohort (so deciles are computed on a consistent March
distribution), recomputes pair-level reason touch-rates by distance and prob
deciles, and writes a side-by-side comparison vs the full Jan-Mar result.

Run from: partner_customer_calls/mar_only/
    python run_mar_analysis.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
from db_connectors import get_snow_connection


HERE   = Path(__file__).resolve().parent
PARENT = HERE.parent
INV    = HERE / "investigative"
INV.mkdir(exist_ok=True)

PARENT_PAIRS = PARENT / "investigative" / "pair_aggregated.csv"
PARENT_PAIR_DIST = PARENT / "investigative" / "pairLevel_reason_by_distance_decile.csv"
PARENT_PAIR_PROB = PARENT / "investigative" / "pairLevel_reason_by_prob_decile.csv"
PARENT_CALLS_RESOLVED = PARENT / "investigative" / "calls_resolved.csv"


# March-only allocation query — same structure as ../query_allocation.txt but
# bounded to March 2026.
MAR_ALLOC_SQL = """
WITH
delhi_mobiles AS (
    SELECT DISTINCT mobile FROM booking_logs
    WHERE added_time >= '2026-03-01' AND added_time < '2026-04-01'
      AND ( LOWER(PARSE_JSON(data):city::STRING)='delhi'
         OR LOWER(PARSE_JSON(data):zone::STRING)='delhi'
         OR LOWER(PARSE_JSON(data):state::STRING) LIKE '%delhi%')
),
bdo_mobiles AS (
    SELECT DISTINCT mobile FROM booking_logs
    WHERE event_name='prospect_identified'
      AND added_time >= '2026-03-01' AND added_time < '2026-04-01'
),
booking_location AS (
    SELECT mobile FROM (
        SELECT mobile, ROW_NUMBER() OVER (PARTITION BY mobile ORDER BY created_at DESC) rn
        FROM prod_db.mysql_rds_genie_genie1.t_serviceability_logs
        WHERE PARSE_JSON(response):serviceable::BOOLEAN=TRUE
          AND created_at >= '2026-02-19' AND created_at < '2026-04-01'
    ) WHERE rn=1
),
allocation AS (
    SELECT mobile, partner_id, nearest_distance, nearest_type, probability, created_at AS allocated_at
    FROM (
        SELECT mobile,
               ns.value:partner_id::STRING AS partner_id,
               ns.value:reason:nearest_type::STRING AS nearest_type,
               TRY_CAST(NULLIF(ns.value:reason:nearest_distance::STRING,'') AS DOUBLE) AS nearest_distance,
               TRY_CAST(NULLIF(ns.value:reason:probability::STRING,'') AS DOUBLE) AS probability,
               created_at,
               ROW_NUMBER() OVER (PARTITION BY mobile, ns.value:partner_id::STRING ORDER BY created_at DESC) rn
        FROM prod_db.mysql_rds_genie_genie2.t_allocation_logs,
        LATERAL FLATTEN(input => PARSE_JSON(data):notification_schedule) ns
        WHERE created_at >= '2026-03-01' AND created_at < '2026-04-15'
    ) WHERE rn=1
)
SELECT al.mobile, al.partner_id, al.nearest_distance, al.nearest_type,
       al.probability, al.allocated_at
FROM delhi_mobiles dm
INNER JOIN booking_location bl ON dm.mobile::STRING = bl.mobile::STRING
INNER JOIN allocation       al ON dm.mobile::STRING = al.mobile::STRING
LEFT  JOIN bdo_mobiles       b ON al.mobile::STRING = b.mobile::STRING
WHERE b.mobile IS NULL
"""


def pct_crosstab(df, row_col, col):
    counts = pd.crosstab(df[row_col], df[col], dropna=False)
    pct = (counts.div(counts.sum(axis=1), axis=0) * 100).round(1)
    pct["_total"] = counts.sum(axis=1)
    return pct


def touch_rate(exploded, row_col):
    n_pairs = exploded.groupby(row_col)[row_col].apply(lambda s: s.name).shape[0]
    denom = exploded.drop_duplicates(["mobile","partner_id"]).groupby(row_col).size()
    touched = exploded.groupby([row_col, "reason"]).size().unstack(fill_value=0)
    out = (touched.div(denom, axis=0) * 100).round(1)
    out["_n_pairs"] = denom
    return out


def main():
    print("=" * 70)
    print("MAR-ONLY PAIR-LEVEL ANALYSIS")
    print("=" * 70)

    # ---- Load parent's pair_aggregated, filter to March ----
    pa = pd.read_csv(PARENT_PAIRS)
    pa["assigned_time"] = pd.to_datetime(pa["assigned_time"])
    mask = (pa["assigned_time"] >= "2026-03-01") & (pa["assigned_time"] < "2026-04-01")
    pa_mar = pa[mask].copy()
    print(f"\nParent pair_aggregated rows      : {len(pa):,}")
    print(f"March-only pair_aggregated rows  : {len(pa_mar):,}")
    print(f"  installed                      : {(pa_mar['installed']==1).sum():,} "
          f"({pa_mar['installed'].mean()*100:.1f}%)")

    pa_mar.to_csv(INV / "mar_pairs_aggregated.csv", index=False)

    # ---- Pull March-only allocation cohort ----
    conn = get_snow_connection()
    assert conn is not None
    print("\nPulling March-only allocation cohort ...")
    alloc = pd.read_sql(MAR_ALLOC_SQL, conn)
    alloc.columns = [c.lower() for c in alloc.columns]
    print(f"  alloc rows: {len(alloc):,}  unique (mob,partner): "
          f"{alloc[['mobile','partner_id']].drop_duplicates().shape[0]:,}")
    alloc.to_csv(INV / "mar_allocation_cohort.csv", index=False)
    conn.close()

    # Dedup to one row per (mobile, partner_id), latest allocation
    alloc = alloc.sort_values("allocated_at").drop_duplicates(["mobile","partner_id"], keep="last")

    # ---- Compute deciles on March-only distribution ----
    alloc = alloc.dropna(subset=["nearest_distance"]).copy()
    alloc["distance_decile"] = pd.qcut(alloc["nearest_distance"], 10, labels=False, duplicates="drop") + 1
    if alloc["probability"].notna().any():
        a_p = alloc.dropna(subset=["probability"]).copy()
        a_p["prob_decile"] = pd.qcut(a_p["probability"], 10, labels=False, duplicates="drop") + 1
        alloc = alloc.merge(a_p[["mobile","partner_id","prob_decile"]],
                             on=["mobile","partner_id"], how="left")
    else:
        alloc["prob_decile"] = np.nan

    for c in ["mobile","partner_id"]:
        alloc[c] = alloc[c].astype(str)
        pa_mar[c] = pa_mar[c].astype(str)

    alloc_slim = alloc[["mobile","partner_id","nearest_distance","nearest_type",
                         "probability","distance_decile","prob_decile"]]

    # ---- Merge ----
    m_pairs = pa_mar.merge(alloc_slim, on=["mobile","partner_id"], how="left")
    m_pairs.to_csv(INV / "mar_pairs_with_alloc.csv", index=False)
    print(f"\nMar pairs merged with alloc: {len(m_pairs):,}  "
          f"with distance_decile: {m_pairs['distance_decile'].notna().sum():,}  "
          f"with prob_decile: {m_pairs['prob_decile'].notna().sum():,}")

    # ---- Pair-level touch rate crosstabs ----
    m_pairs["reasons_list"] = m_pairs["reasons_union"].fillna("").str.split(",")
    exploded = m_pairs.explode("reasons_list").rename(columns={"reasons_list":"reason"})
    exploded = exploded[exploded["reason"].astype(str).str.len() > 0]

    def tr(row_col):
        denom = m_pairs.groupby(row_col)["mobile"].count()
        touched = exploded.groupby([row_col, "reason"]).size().unstack(fill_value=0)
        out = (touched.div(denom, axis=0) * 100).round(1)
        out["_n_pairs"] = denom
        return out

    pair_dist = tr("distance_decile")
    pair_prob = tr("prob_decile")
    pair_dist.to_csv(INV / "mar_pairLevel_reason_by_distance_decile.csv")
    pair_prob.to_csv(INV / "mar_pairLevel_reason_by_prob_decile.csv")

    print("\n=== MAR-ONLY pair-level address_not_clear % by distance decile ===")
    print(pair_dist[["address_not_clear","partner_reached_cant_find","_n_pairs"]].to_string())
    print("\n=== MAR-ONLY pair-level address_not_clear % by prob decile ===")
    print(pair_prob[["address_not_clear","partner_reached_cant_find","_n_pairs"]].to_string())

    # ---- Call-level (use parent's calls_resolved, filter by assigned_time via manifest lookup) ----
    cr = pd.read_csv(PARENT_CALLS_RESOLVED)
    cr["assigned_time"] = pd.to_datetime(cr["assigned_time"])
    cr_mar = cr[(cr["assigned_time"] >= "2026-03-01") & (cr["assigned_time"] < "2026-04-01")].copy()
    for c in ["mobile","partner_id"]:
        cr_mar[c] = cr_mar[c].astype(str)
    cw = cr_mar.merge(alloc_slim, on=["mobile","partner_id"], how="left")
    print(f"\nMar call-level rows: {len(cw):,}")

    call_dist = pct_crosstab(cw, "distance_decile", "primary_reason")
    call_prob = pct_crosstab(cw, "prob_decile", "primary_reason")
    call_dist.to_csv(INV / "mar_callLevel_reason_by_distance_decile.csv")
    call_prob.to_csv(INV / "mar_callLevel_reason_by_prob_decile.csv")

    print("\n=== MAR-ONLY call-level primary_reason % by distance decile (address_not_clear col) ===")
    print(call_dist[["address_not_clear","partner_reached_cant_find","slot_confirmation","noise_or_empty","_total"]].to_string())

    # ---- Comparison vs full cohort ----
    full_dist = pd.read_csv(PARENT_PAIR_DIST, index_col=0)
    full_prob = pd.read_csv(PARENT_PAIR_PROB, index_col=0)

    cmp_dist = pd.DataFrame({
        "full_cohort_address_not_clear": full_dist["address_not_clear"],
        "mar_only_address_not_clear": pair_dist["address_not_clear"],
        "delta_pp": pair_dist["address_not_clear"] - full_dist["address_not_clear"],
        "full_n":   full_dist["_n_pairs"],
        "mar_n":    pair_dist["_n_pairs"],
    })
    cmp_prob = pd.DataFrame({
        "full_cohort_address_not_clear": full_prob["address_not_clear"],
        "mar_only_address_not_clear": pair_prob["address_not_clear"],
        "delta_pp": pair_prob["address_not_clear"] - full_prob["address_not_clear"],
        "full_n":   full_prob["_n_pairs"],
        "mar_n":    pair_prob["_n_pairs"],
    })
    cmp_dist.to_csv(INV / "comparison_vs_full_distance.csv")
    cmp_prob.to_csv(INV / "comparison_vs_full_prob.csv")

    print("\n=== COMPARISON: full Jan-Mar vs Mar-only — address_not_clear by DISTANCE decile ===")
    print(cmp_dist.round(1).to_string())
    print("\n=== COMPARISON: full Jan-Mar vs Mar-only — address_not_clear by PROB decile ===")
    print(cmp_prob.round(1).to_string())

    print("\nDONE")


if __name__ == "__main__":
    main()
