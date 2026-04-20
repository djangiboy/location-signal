"""
Sensitivity cut: same pipeline as build_jitter.py but restricted to mobiles
with >=5 TOTAL surviving pings (i.e., >=4 subsequent pings after the
15-min dedup + 250m home-move cap).

Rationale: mobiles with only 3 total pings (74% of v4) contribute just 2
jitter measurements each. Per-mobile stats (min/max/mean/median/p75) on 2
samples are noisy. Restricting to >=4 subsequent gives tighter per-mobile
estimates at the cost of a much smaller cohort.

Reads v4 outputs directly (no re-run of the pipeline):
    investigations/jitter_pairs_v4.csv
    investigations/jitter_mobile_v4.csv

Writes (all in investigations/, suffix _ge5):
    jitter_pairs_v4_ge5.csv
    jitter_mobile_v4_ge5.csv
    jitter_ping_deciles_ge5.csv,       jitter_ping_quantiles_ge5.csv
    jitter_mobile_max_deciles_ge5.csv, jitter_mobile_max_quantiles_ge5.csv
    jitter_mobile_median_deciles_ge5.csv, jitter_mobile_median_quantiles_ge5.csv
    jitter_ge5_vs_v4_comparison.csv    side-by-side quantile comparison

Run from: promise_maker_gps/gps_jitter/
    python build_jitter_ge5.py
"""

from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
INV = HERE / "investigations"

IN_PAIRS = INV / "jitter_pairs_v4.csv"
IN_MOBILE = INV / "jitter_mobile_v4.csv"

MIN_SUBSEQ = 4  # >=4 subsequent pings = >=5 total pings (anchor + subseq)

QUANTILES = [0.01, 0.05, 0.10, 0.20, 0.25, 0.30, 0.40, 0.50,
             0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99]


def decile_table(s, name):
    d = pd.qcut(s, q=10, labels=False, duplicates="drop") + 1
    g = (
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
    return g


def quantile_series(s):
    return {f"p{int(q*100):02d}": round(float(s.quantile(q)), 2) for q in QUANTILES}


def banner(t):
    print("\n" + "=" * 74)
    print(t)
    print("=" * 74)


def main():
    pairs = pd.read_csv(IN_PAIRS)
    mob = pd.read_csv(IN_MOBILE)

    n_mob_v4 = len(mob)
    n_pings_v4 = len(pairs)

    # ------------------------------------------------------------------
    # FILTER: mobiles with >=4 surviving subseq pings (= >=5 total)
    # ------------------------------------------------------------------
    mob_ge5 = mob[mob["n_subseq_pings"] >= MIN_SUBSEQ].copy()
    pairs_ge5 = pairs[pairs["mobile"].isin(mob_ge5["mobile"])].copy()
    n_mob = len(mob_ge5)
    n_pings = len(pairs_ge5)

    banner(f"GE5 SENSITIVITY CUT -- mobiles with >=5 total pings (>={MIN_SUBSEQ} subseq)")
    print(f"v4 baseline           : {n_mob_v4:,} mobiles / {n_pings_v4:,} subseq pings")
    print(f"GE5 cut               : {n_mob:,} mobiles / {n_pings:,} subseq pings")
    print(f"RETENTION             : {n_mob/n_mob_v4:.1%} of mobiles, "
          f"{n_pings/n_pings_v4:.1%} of pings")
    print(f"MIN subseq pings      : {mob_ge5['n_subseq_pings'].min()}")
    print(f"MAX subseq pings      : {mob_ge5['n_subseq_pings'].max()}")
    assert mob_ge5["n_subseq_pings"].sum() == n_pings
    print(f"PINGS PER MOBILE      : mean {mob_ge5['n_subseq_pings'].mean():.2f}, "
          f"median {mob_ge5['n_subseq_pings'].median():.0f}")

    # ------------------------------------------------------------------
    # PER-PING DECILES + QUANTILES
    # ------------------------------------------------------------------
    banner(f"PER-PING JITTER  (n={n_pings:,} pings across {n_mob:,} mobiles)")
    dp = decile_table(pairs_ge5["distance_m"], "distance_m")
    print(dp.round(2).to_string(index=False))
    assert dp["freq"].sum() == n_pings
    print(f"\n  freq.sum = {dp['freq'].sum():,}  (== {n_pings:,} input pings  ✓)")
    dp.to_csv(INV / "jitter_ping_deciles_ge5.csv", index=False)

    qp = quantile_series(pairs_ge5["distance_m"])
    print("\nFull quantile grid (m):")
    for q, v in qp.items():
        print(f"  {q}: {v:>8.2f}")
    pd.DataFrame([{"quantile": q, "distance_m": v} for q, v in qp.items()]) \
        .to_csv(INV / "jitter_ping_quantiles_ge5.csv", index=False)

    # ------------------------------------------------------------------
    # PER-MOBILE UNCERTAINTY RADIUS (max_dist_m)
    # ------------------------------------------------------------------
    banner(f"PER-MOBILE UNCERTAINTY RADIUS  max_dist_m  (n={n_mob:,} mobiles)")
    dm = decile_table(mob_ge5["max_dist_m"], "max_dist_m")
    print(dm.round(2).to_string(index=False))
    assert dm["freq"].sum() == n_mob
    print(f"\n  freq.sum = {dm['freq'].sum():,}  (== {n_mob:,} input mobiles  ✓)")
    dm.to_csv(INV / "jitter_mobile_max_deciles_ge5.csv", index=False)

    qm = quantile_series(mob_ge5["max_dist_m"])
    print("\nFull quantile grid (m):")
    for q, v in qm.items():
        print(f"  {q}: {v:>8.2f}")
    pd.DataFrame([{"quantile": q, "max_dist_m": v} for q, v in qm.items()]) \
        .to_csv(INV / "jitter_mobile_max_quantiles_ge5.csv", index=False)

    # ------------------------------------------------------------------
    # PER-MOBILE CENTRAL TENDENCY (median_dist_m)
    # ------------------------------------------------------------------
    banner(f"PER-MOBILE CENTRAL TENDENCY  median_dist_m  (n={n_mob:,} mobiles)")
    dmd = decile_table(mob_ge5["median_dist_m"], "median_dist_m")
    print(dmd.round(2).to_string(index=False))
    assert dmd["freq"].sum() == n_mob
    dmd.to_csv(INV / "jitter_mobile_median_deciles_ge5.csv", index=False)

    qmd = quantile_series(mob_ge5["median_dist_m"])
    print("\nFull quantile grid (m):")
    for q, v in qmd.items():
        print(f"  {q}: {v:>8.2f}")
    pd.DataFrame([{"quantile": q, "median_dist_m": v} for q, v in qmd.items()]) \
        .to_csv(INV / "jitter_mobile_median_quantiles_ge5.csv", index=False)

    # ------------------------------------------------------------------
    # SIDE-BY-SIDE COMPARISON: v4 vs GE5 -- same quantiles, three metrics
    # ------------------------------------------------------------------
    banner("COMPARISON  v4 (all) vs GE5 (>=5 total pings)")
    cmp_rows = []
    for q in QUANTILES:
        cmp_rows.append({
            "quantile":           f"p{int(q*100):02d}",
            "ping_v4_m":          round(float(pairs["distance_m"].quantile(q)), 2),
            "ping_ge5_m":         round(float(pairs_ge5["distance_m"].quantile(q)), 2),
            "maxdist_v4_m":       round(float(mob["max_dist_m"].quantile(q)), 2),
            "maxdist_ge5_m":      round(float(mob_ge5["max_dist_m"].quantile(q)), 2),
            "mediandist_v4_m":    round(float(mob["median_dist_m"].quantile(q)), 2),
            "mediandist_ge5_m":   round(float(mob_ge5["median_dist_m"].quantile(q)), 2),
        })
    cmp_df = pd.DataFrame(cmp_rows)
    print(cmp_df.to_string(index=False))
    cmp_df.to_csv(INV / "jitter_ge5_vs_v4_comparison.csv", index=False)

    # ------------------------------------------------------------------
    # HEADLINE CALLOUTS (matched against the v4 callouts for easy compare)
    # ------------------------------------------------------------------
    banner("HEADLINE CALLOUTS  (GE5 cohort)")
    print(f"Cohort: {n_mob:,} mobiles / {n_pings:,} subseq pings "
          f"({n_mob/n_mob_v4:.1%} of v4)")
    p75_maxdist = mob_ge5["max_dist_m"].quantile(0.75)
    p95_ping = pairs_ge5["distance_m"].quantile(0.95)
    within_25m = (mob_ge5["max_dist_m"] <= 25).sum()
    print(f"\nP75 uncertainty radius : {p75_maxdist:>7.2f} m")
    print(f"P95 per-ping jitter    : {p95_ping:>7.2f} m  (Stage B threshold for this cohort)")
    print(f"\nMobiles within 25m max : {within_25m:,} / {n_mob:,} ({within_25m/n_mob:.1%})")

    pairs_ge5.to_csv(INV / "jitter_pairs_v4_ge5.csv", index=False)
    mob_ge5.to_csv(INV / "jitter_mobile_v4_ge5.csv", index=False)

    print("\nSAVED: 9 CSVs to investigations/ (suffix _ge5)")


if __name__ == "__main__":
    main()
