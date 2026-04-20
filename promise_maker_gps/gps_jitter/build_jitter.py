"""
Build the GPS jitter baseline from raw wifi_connected_location_captured pings.

Reads investigations/wifi_pings_raw.csv (from pull_wifi_pings.py) and produces
the v1 -> v4 pipeline. Every step's attrition is logged to
investigations/jitter_funnel.csv so any downstream number can be traced back
to raw counts.

Pipeline:
    v1  anchor each mobile at row_cnt==1; merge each subsequent ping -> haversine
    v2  v1 + time_gap_days (days between subsequent ping and anchor)
    v3  v2 after 15-min dedup (drop pings <15min from prev ping on same mobile),
        then keep mobiles with >=3 total pings (anchor + >=2 subsequent)
    v4  v3 after 250m home-move cap on subsequent pings,
        then keep mobiles with >=2 surviving subsequent pings

Outputs (in investigations/):
    jitter_funnel.csv         per-step attrition (pings, mobiles, % retained)
    jitter_pairs_v4.csv       one row per surviving subsequent ping in v4
    jitter_mobile_v4.csv      one row per surviving mobile in v4 (aggregate stats)

Cross-check against Rohan's notebook (cells 11, 13, 19, 21, 23):
    >=3 pings cohort ................ 25,123 mobiles  /  120,900 pings
    df_pairs2 (subseq only) .......... 95,777 pings
    after 15-min dedup ............... 60,661 pings
    df_mobile_v3 ..................... 10,255 mobiles / 24,753 subseq pings
    after 250m cap ................... 20,525 pings
    df_mobile_v4 (final) .............. 8,317 mobiles / 20,231 subseq pings
    Headlines: median radius=12m, p75=32m, p90=116m

Run from: promise_maker_gps/gps_jitter/
    python build_jitter.py
"""

from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
INV = HERE / "investigations"

IN_RAW = INV / "wifi_pings_raw.csv"
OUT_FUNNEL = INV / "jitter_funnel.csv"
OUT_PAIRS = INV / "jitter_pairs_v4.csv"
OUT_MOBILE = INV / "jitter_mobile_v4.csv"

DEDUP_MIN = 15.0        # minutes
HOME_MOVE_CAP_M = 250.0 # meters


# ------------------------------------------------------------------
# Haversine -- meters. Vectorized (accepts scalars or numpy arrays).
# ------------------------------------------------------------------
def haversine_m(lat1, lng1, lat2, lng2):
    """Great-circle distance in meters. Earth radius = 6,371,000 m."""
    lat1 = np.radians(np.asarray(lat1, dtype=float))
    lat2 = np.radians(np.asarray(lat2, dtype=float))
    dlat = lat2 - lat1
    dlng = np.radians(np.asarray(lng2, dtype=float) - np.asarray(lng1, dtype=float))
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2) ** 2
    return 2 * 6_371_000.0 * np.arcsin(np.sqrt(a))


def main():
    # ==============================================================
    # STEP 0 -- load raw pings
    # ==============================================================
    print("=" * 70)
    print("BUILD_JITTER -- v1 -> v4 pipeline")
    print("=" * 70)
    a = pd.read_csv(IN_RAW)
    a.columns = [c.lower() for c in a.columns]
    a["mobile"] = a["mobile"].astype(str).str.strip()
    a["added_time"] = pd.to_datetime(a["added_time"])

    n_raw_pings = len(a)
    n_raw_mobiles = a["mobile"].nunique()
    print(f"\nRAW PINGS              : {n_raw_pings:,}")
    print(f"RAW MOBILES            : {n_raw_mobiles:,}")

    funnel = []  # accumulate (step, n_pings, n_mobiles, pct_pings_kept, pct_mobiles_kept)

    funnel.append({
        "step": "raw_pull",
        "n_pings": n_raw_pings, "n_mobiles": n_raw_mobiles,
        "pct_pings_kept": 1.0, "pct_mobiles_kept": 1.0,
        "note": "raw query output",
    })

    # ==============================================================
    # STEP 1 -- keep mobiles with >=3 total pings (need >=2 subseq)
    # ==============================================================
    mobile_ping_counts = a.groupby("mobile").size()
    mobiles_ge3 = mobile_ping_counts[mobile_ping_counts >= 3].index
    b = a[a["mobile"].isin(mobiles_ge3)].copy()
    n1_pings, n1_mobiles = len(b), b["mobile"].nunique()
    print(f"\n--- STEP 1: keep mobiles with >=3 pings ---")
    print(f"PINGS  : {n_raw_pings:,} -> {n1_pings:,} ({n1_pings/n_raw_pings:.1%})")
    print(f"MOBILES: {n_raw_mobiles:,} -> {n1_mobiles:,} ({n1_mobiles/n_raw_mobiles:.1%})")
    print(f"  NOTEBOOK CHECK: expect 25,123 mobiles / 120,900 pings")
    funnel.append({
        "step": ">=3_pings_filter", "n_pings": n1_pings, "n_mobiles": n1_mobiles,
        "pct_pings_kept": n1_pings / n_raw_pings,
        "pct_mobiles_kept": n1_mobiles / n_raw_mobiles,
        "note": "mobiles with only 1-2 pings drop -- no repeat measurement",
    })

    # ==============================================================
    # STEP 2 -- v1/v2: anchor + subsequent pairs, haversine + time_gap
    # ==============================================================
    b = b.sort_values(["mobile", "added_time"]).reset_index(drop=True)

    anchor = (
        b[b["row_cnt"] == 1]
        [["mobile", "install_lat", "install_lng", "added_time"]]
        .drop_duplicates(subset="mobile")
        .rename(columns={
            "install_lat": "anchor_lat",
            "install_lng": "anchor_lng",
            "added_time": "anchor_time",
        })
    )
    subs = b[b["row_cnt"] > 1][["mobile", "install_lat", "install_lng", "added_time", "row_cnt"]]
    pairs_v2 = subs.merge(anchor, on="mobile", how="inner")
    pairs_v2["distance_m"] = haversine_m(
        pairs_v2["anchor_lat"].values, pairs_v2["anchor_lng"].values,
        pairs_v2["install_lat"].values, pairs_v2["install_lng"].values,
    )
    pairs_v2["time_gap_days"] = (
        pairs_v2["added_time"] - pairs_v2["anchor_time"]
    ).dt.total_seconds() / 86400.0

    n2_pings, n2_mobiles = len(pairs_v2), pairs_v2["mobile"].nunique()
    print(f"\n--- STEP 2: v2 anchor+pairs (subsequent pings only) ---")
    print(f"SUBSEQ PINGS : {n2_pings:,}  (anchors excluded: {n1_pings - n2_pings:,})")
    print(f"MOBILES      : {n2_mobiles:,}")
    print(f"  NOTEBOOK CHECK: expect 95,777 subseq pings across 25,123 mobiles")
    funnel.append({
        "step": "v2_anchor_pairs", "n_pings": n2_pings, "n_mobiles": n2_mobiles,
        "pct_pings_kept": n2_pings / n_raw_pings,
        "pct_mobiles_kept": n2_mobiles / n_raw_mobiles,
        "note": "subsequent pings only (anchor row excluded from pair count)",
    })

    # ==============================================================
    # STEP 3 -- v3: 15-min dedup, then >=2 surviving pings total
    # ==============================================================
    c = b.copy()
    c["prev_time"] = c.groupby("mobile")["added_time"].shift(1)
    c["gap_from_prev_min"] = (
        c["added_time"] - c["prev_time"]
    ).dt.total_seconds() / 60.0
    keep_mask = c["gap_from_prev_min"].isna() | (c["gap_from_prev_min"] >= DEDUP_MIN)
    n_dedup_pings_pre = len(c)
    c_dedup = c[keep_mask].copy()
    n_dedup_pings = len(c_dedup)
    print(f"\n--- STEP 3a: 15-min dedup (same-mobile, gap<15min) ---")
    print(f"PINGS: {n_dedup_pings_pre:,} -> {n_dedup_pings:,} "
          f"({n_dedup_pings_pre - n_dedup_pings:,} dropped, "
          f"{(n_dedup_pings_pre - n_dedup_pings)/n_dedup_pings_pre:.1%})")
    print(f"  NOTEBOOK CHECK: expect 120,900 -> 60,661 pings (~60k dropped)")

    mobile_counts_after_dedup = c_dedup.groupby("mobile").size()
    mobiles_v3 = mobile_counts_after_dedup[mobile_counts_after_dedup >= 3].index
    c_v3 = c_dedup[c_dedup["mobile"].isin(mobiles_v3)].copy()
    n3_pings, n3_mobiles = len(c_v3), c_v3["mobile"].nunique()
    print(f"\n--- STEP 3b: keep mobiles with >=3 pings after dedup ---")
    print(f"PINGS  : {n_dedup_pings:,} -> {n3_pings:,}")
    print(f"MOBILES: {n2_mobiles:,} -> {n3_mobiles:,}")
    print(f"  NOTEBOOK CHECK: expect 10,255 mobiles / 24,753 subseq pings")
    funnel.append({
        "step": "v3_15min_dedup", "n_pings": n_dedup_pings, "n_mobiles": c_dedup["mobile"].nunique(),
        "pct_pings_kept": n_dedup_pings / n_raw_pings,
        "pct_mobiles_kept": c_dedup["mobile"].nunique() / n_raw_mobiles,
        "note": f"dropped pings within {DEDUP_MIN:.0f}min of prev ping (cache/bug re-emits)",
    })
    funnel.append({
        "step": "v3_ge3_after_dedup", "n_pings": n3_pings, "n_mobiles": n3_mobiles,
        "pct_pings_kept": n3_pings / n_raw_pings,
        "pct_mobiles_kept": n3_mobiles / n_raw_mobiles,
        "note": "mobiles whose surviving pings fall <3 drop (all cache-hit bursts)",
    })

    # Rebuild anchor + pairs for v3
    anchor_v3 = (
        c_v3[c_v3["row_cnt"] == 1]
        [["mobile", "install_lat", "install_lng", "added_time"]]
        .drop_duplicates(subset="mobile")
        .rename(columns={
            "install_lat": "anchor_lat",
            "install_lng": "anchor_lng",
            "added_time": "anchor_time",
        })
    )
    subs_v3 = c_v3[c_v3["row_cnt"] > 1][["mobile", "install_lat", "install_lng", "added_time", "row_cnt"]]
    pairs_v3 = subs_v3.merge(anchor_v3, on="mobile", how="inner")
    pairs_v3["distance_m"] = haversine_m(
        pairs_v3["anchor_lat"].values, pairs_v3["anchor_lng"].values,
        pairs_v3["install_lat"].values, pairs_v3["install_lng"].values,
    )
    pairs_v3["time_gap_days"] = (
        pairs_v3["added_time"] - pairs_v3["anchor_time"]
    ).dt.total_seconds() / 86400.0
    print(f"\n  v3 subseq pairs: {len(pairs_v3):,} across {pairs_v3['mobile'].nunique():,} mobiles")

    # ==============================================================
    # STEP 4 -- v4: 250m home-move cap, then >=2 surviving subseq
    # ==============================================================
    pairs_v4 = pairs_v3[pairs_v3["distance_m"] <= HOME_MOVE_CAP_M].copy()
    n_v4_pings_cap = len(pairs_v4)
    print(f"\n--- STEP 4a: {HOME_MOVE_CAP_M:.0f}m home-move cap on subseq pings ---")
    print(f"SUBSEQ PINGS: {len(pairs_v3):,} -> {n_v4_pings_cap:,} "
          f"({len(pairs_v3) - n_v4_pings_cap:,} dropped, "
          f"{(len(pairs_v3) - n_v4_pings_cap)/len(pairs_v3):.1%})")
    print(f"  NOTEBOOK CHECK: expect 24,753 -> 20,525 subseq pings (17.1% dropped)")

    subs_count_v4 = pairs_v4.groupby("mobile").size()
    mobiles_v4 = subs_count_v4[subs_count_v4 >= 2].index
    pairs_v4 = pairs_v4[pairs_v4["mobile"].isin(mobiles_v4)].copy()
    n4_pings, n4_mobiles = len(pairs_v4), pairs_v4["mobile"].nunique()
    print(f"\n--- STEP 4b: keep mobiles with >=2 surviving subseq pings ---")
    print(f"SUBSEQ PINGS: {n_v4_pings_cap:,} -> {n4_pings:,}")
    print(f"MOBILES     : {len(subs_count_v4):,} -> {n4_mobiles:,}")
    print(f"  NOTEBOOK CHECK: expect 8,317 mobiles / 20,231 subseq pings")
    funnel.append({
        "step": "v4_250m_cap", "n_pings": n_v4_pings_cap, "n_mobiles": len(subs_count_v4),
        "pct_pings_kept": n_v4_pings_cap / n_raw_pings,
        "pct_mobiles_kept": len(subs_count_v4) / n_raw_mobiles,
        "note": f"dropped subseq pings >{HOME_MOVE_CAP_M:.0f}m from anchor (home move, not jitter)",
    })
    funnel.append({
        "step": "v4_final", "n_pings": n4_pings, "n_mobiles": n4_mobiles,
        "pct_pings_kept": n4_pings / n_raw_pings,
        "pct_mobiles_kept": n4_mobiles / n_raw_mobiles,
        "note": "mobiles with <2 surviving subseq pings drop -- need >=2 for dist stats",
    })

    # ==============================================================
    # STEP 5 -- per-mobile aggregates (df_mobile_v4)
    # ==============================================================
    mobile_v4 = (
        pairs_v4.groupby("mobile")
        .agg(
            n_subseq_pings=("distance_m", "size"),
            min_dist_m=("distance_m", "min"),
            max_dist_m=("distance_m", "max"),
            mean_dist_m=("distance_m", "mean"),
            median_dist_m=("distance_m", "median"),
            p75_dist_m=("distance_m", lambda s: s.quantile(0.75)),
            max_time_days=("time_gap_days", "max"),
        )
        .reset_index()
    )
    mobile_v4 = mobile_v4.merge(anchor_v3, on="mobile", how="left")

    # ==============================================================
    # HEADLINES
    # ==============================================================
    print("\n" + "=" * 70)
    print("HEADLINES (v4)")
    print("=" * 70)

    print("\n--- PER-PING jitter distribution (20,231 expected) ---")
    d = pairs_v4["distance_m"]
    for q in [0.50, 0.75, 0.90, 0.95, 0.99]:
        print(f"  p{int(q*100):>2} = {d.quantile(q):>8.1f} m")

    print("\n--- PER-MOBILE uncertainty radius (max_dist_m per mobile, then quantiles across mobiles) ---")
    r = mobile_v4["max_dist_m"]
    for q in [0.50, 0.75, 0.90, 0.95]:
        print(f"  p{int(q*100):>2}(max_dist) = {r.quantile(q):>8.1f} m")
    print(f"\n  NOTEBOOK CHECK: expect median=12m, p75=32m, p90=116m")

    print("\n--- PER-MOBILE median_dist_m (central tendency per mobile) ---")
    m = mobile_v4["median_dist_m"]
    for q in [0.50, 0.75, 0.90, 0.95]:
        print(f"  p{int(q*100):>2}(median_dist) = {m.quantile(q):>8.1f} m")

    # ==============================================================
    # WRITE OUTPUTS
    # ==============================================================
    pd.DataFrame(funnel).to_csv(OUT_FUNNEL, index=False)
    pairs_v4.to_csv(OUT_PAIRS, index=False)
    mobile_v4.to_csv(OUT_MOBILE, index=False)
    print("\n" + "=" * 70)
    print("SAVED:")
    print(f"  {OUT_FUNNEL.name}   ({len(funnel)} rows)")
    print(f"  {OUT_PAIRS.name}    ({n4_pings:,} rows)")
    print(f"  {OUT_MOBILE.name}    ({n4_mobiles:,} rows)")


if __name__ == "__main__":
    main()
