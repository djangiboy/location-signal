"""
Consecutive-ping jitter distribution (companion to anchor-based jitter).

Every metric in build_jitter.py is measured vs the row_cnt=1 anchor. This
script computes the orthogonal read: distance between TEMPORALLY-ADJACENT
pings for the same mobile.

Reuses the v4 cohort -- same filters (15-min dedup + 250m anchor cap +
>=2 surviving subseq pings). Builds an ordered ping list per mobile
(anchor + surviving subseq) and computes haversine between each pair
of temporally adjacent pings.

Important methodological point:
    For a mobile with anchor a and surviving subseq pings p2, p3 (ordered
    by added_time), consecutive distances are:
        d1 = haversine(a,  p2)   <-- same as the anchor-based distance
        d2 = haversine(p2, p3)   <-- genuinely new
    Across the 20,231 consec measurements, 8,317 equal their anchor-based
    counterpart (the first subseq ping per mobile). The remaining 11,914
    are novel (between two non-anchor pings).

Reads:
    investigations/jitter_pairs_v4.csv   (anchor metadata + subseq pings)

Writes (investigations/):
    jitter_consec_pairs.csv            every consecutive distance
    jitter_consec_deciles.csv          10-bucket distribution
    jitter_consec_quantiles.csv        p01..p99 grid
    jitter_consec_vs_anchor.csv        side-by-side quantile comparison

Run from: promise_maker_gps/gps_jitter/
    python build_jitter_consecutive.py
"""

from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
INV = HERE / "investigations"

IN_PAIRS = INV / "jitter_pairs_v4.csv"

QUANTILES = [0.01, 0.05, 0.10, 0.20, 0.25, 0.30, 0.40, 0.50,
             0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99]


def haversine_m(lat1, lng1, lat2, lng2):
    lat1 = np.radians(np.asarray(lat1, dtype=float))
    lat2 = np.radians(np.asarray(lat2, dtype=float))
    dlat = lat2 - lat1
    dlng = np.radians(np.asarray(lng2, dtype=float) - np.asarray(lng1, dtype=float))
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2) ** 2
    return 2 * 6_371_000.0 * np.arcsin(np.sqrt(a))


def decile_table(s, name):
    d = pd.qcut(s, q=10, labels=False, duplicates="drop") + 1
    return (
        pd.DataFrame({"decile": d, name: s})
        .groupby("decile")
        .agg(
            freq=(name, "size"),
            d_min=(name, "min"),
            d_max=(name, "max"),
            d_mean=(name, "mean"),
            d_median=(name, "median"),
        )
        .reset_index()
    )


def banner(t):
    print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


def main():
    # ==============================================================
    # STEP 0 -- reconstruct ordered ping list per mobile from v4 pairs
    # ==============================================================
    pairs = pd.read_csv(IN_PAIRS)
    pairs["added_time"] = pd.to_datetime(pairs["added_time"])
    pairs["anchor_time"] = pd.to_datetime(pairs["anchor_time"])

    n_mobiles = pairs["mobile"].nunique()
    n_subseq = len(pairs)

    banner("CONSECUTIVE-PING JITTER  --  cohort = v4 (15-min dedup + 250m cap)")
    print(f"Source pairs       : {n_subseq:,} subseq rows / {n_mobiles:,} mobiles")

    # Extract unique anchor rows per mobile
    anchor = (
        pairs[["mobile", "anchor_lat", "anchor_lng", "anchor_time"]]
        .drop_duplicates(subset="mobile")
        .rename(columns={
            "anchor_lat": "install_lat",
            "anchor_lng": "install_lng",
            "anchor_time": "added_time",
        })
    )
    anchor["row_cnt"] = 1  # anchor is row_cnt=1 by definition

    subseq = pairs[["mobile", "install_lat", "install_lng", "added_time", "row_cnt"]]

    all_pings = pd.concat([anchor, subseq], ignore_index=True)
    all_pings = all_pings.sort_values(["mobile", "added_time"]).reset_index(drop=True)
    n_total_pings = len(all_pings)
    assert n_total_pings == n_mobiles + n_subseq, \
        f"ping count mismatch: {n_total_pings} != {n_mobiles} + {n_subseq}"
    print(f"Anchor rows added  : {n_mobiles:,}")
    print(f"Total ordered pings: {n_total_pings:,}  (anchors + subseq)")

    # ==============================================================
    # STEP 1 -- consecutive distance per mobile
    # ==============================================================
    all_pings["prev_lat"] = all_pings.groupby("mobile")["install_lat"].shift(1)
    all_pings["prev_lng"] = all_pings.groupby("mobile")["install_lng"].shift(1)
    all_pings["prev_time"] = all_pings.groupby("mobile")["added_time"].shift(1)

    all_pings["consec_dist_m"] = haversine_m(
        all_pings["prev_lat"].values, all_pings["prev_lng"].values,
        all_pings["install_lat"].values, all_pings["install_lng"].values,
    )
    all_pings["consec_gap_min"] = (
        all_pings["added_time"] - all_pings["prev_time"]
    ).dt.total_seconds() / 60.0

    consec = all_pings.dropna(subset=["consec_dist_m"]).copy()
    n_consec = len(consec)
    print(f"\nCONSECUTIVE PAIRS  : {n_consec:,} measurements")
    print(f"  (expect {n_total_pings - n_mobiles:,} = total pings - n_mobiles  ✓)"
          if n_consec == n_total_pings - n_mobiles else "  MISMATCH")

    # ==============================================================
    # STEP 2 -- DECILES
    # ==============================================================
    banner(f"CONSECUTIVE-PING JITTER  --  DECILES  (n={n_consec:,})")
    dp = decile_table(consec["consec_dist_m"], "consec_dist_m")
    print(dp.round(2).to_string(index=False))
    assert dp["freq"].sum() == n_consec
    print(f"\n  freq.sum = {dp['freq'].sum():,}  (== {n_consec:,} consec pairs  ✓)")
    dp.to_csv(INV / "jitter_consec_deciles.csv", index=False)

    # ==============================================================
    # STEP 3 -- QUANTILES
    # ==============================================================
    banner("CONSECUTIVE-PING JITTER  --  QUANTILES")
    qrows = [
        {"quantile": f"p{int(q*100):02d}",
         "consec_dist_m": round(float(consec["consec_dist_m"].quantile(q)), 2)}
        for q in QUANTILES
    ]
    q_df = pd.DataFrame(qrows)
    print(q_df.to_string(index=False))
    q_df.to_csv(INV / "jitter_consec_quantiles.csv", index=False)

    # ==============================================================
    # STEP 4 -- SIDE-BY-SIDE: consec vs anchor (same v4 cohort)
    # ==============================================================
    anchor_ping = pairs["distance_m"]  # anchor-based, same cohort
    n_anchor = len(anchor_ping)
    banner(f"CONSECUTIVE vs ANCHOR-BASED  (same v4 cohort)")
    print(f"Anchor-based pairs : {n_anchor:,}   (haversine(anchor, subseq) for each subseq ping)")
    print(f"Consecutive pairs  : {n_consec:,}   (haversine(ping_{{i-1}}, ping_i) for temporally adjacent)")
    print(f"  Note: counts equal -- each subseq ping contributes one of each.")
    print(f"  Shared rows: 8,317 (first subseq per mobile -- its predecessor IS the anchor).")
    print(f"  Genuinely new consec measurements: {n_consec - n_mobiles:,} "
          f"(between two non-anchor pings).")

    cmp_rows = []
    for q in QUANTILES:
        cmp_rows.append({
            "quantile":     f"p{int(q*100):02d}",
            "anchor_m":     round(float(anchor_ping.quantile(q)), 2),
            "consec_m":     round(float(consec["consec_dist_m"].quantile(q)), 2),
            "diff_m":       round(float(consec["consec_dist_m"].quantile(q)
                                         - anchor_ping.quantile(q)), 2),
        })
    cmp_df = pd.DataFrame(cmp_rows)
    print("\n" + cmp_df.to_string(index=False))
    cmp_df.to_csv(INV / "jitter_consec_vs_anchor.csv", index=False)

    # ==============================================================
    # STEP 5 -- HEADLINE CALLOUTS
    # ==============================================================
    banner("HEADLINE CALLOUTS")
    p50 = consec["consec_dist_m"].quantile(0.50)
    p75 = consec["consec_dist_m"].quantile(0.75)
    p95 = consec["consec_dist_m"].quantile(0.95)
    within_25 = (consec["consec_dist_m"] <= 25).sum()
    print(f"Per-consec-pair  p50 : {p50:>7.2f} m")
    print(f"Per-consec-pair  p75 : {p75:>7.2f} m")
    print(f"Per-consec-pair  p95 : {p95:>7.2f} m")
    print(f"Consec distances <=25m: {within_25:,} / {n_consec:,} "
          f"({within_25/n_consec:.1%})")

    # ==============================================================
    # WRITE RAW CONSEC PAIRS
    # ==============================================================
    consec_out = consec[[
        "mobile", "row_cnt",
        "prev_lat", "prev_lng", "prev_time",
        "install_lat", "install_lng", "added_time",
        "consec_dist_m", "consec_gap_min",
    ]]
    consec_out.to_csv(INV / "jitter_consec_pairs.csv", index=False)
    print(f"\nSAVED: 4 CSVs to investigations/")
    print(f"  jitter_consec_pairs.csv    ({n_consec:,} rows)")
    print(f"  jitter_consec_deciles.csv  (10 rows)")
    print(f"  jitter_consec_quantiles.csv ({len(QUANTILES)} rows)")
    print(f"  jitter_consec_vs_anchor.csv ({len(QUANTILES)} rows)")


if __name__ == "__main__":
    main()
