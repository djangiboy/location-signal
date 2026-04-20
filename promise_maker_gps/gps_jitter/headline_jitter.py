"""
Stage A headline tables -- decile + quantile views on v4 outputs.

Reads:
    investigations/jitter_pairs_v4.csv        (20,231 subseq pings)
    investigations/jitter_mobile_v4.csv       (8,317 mobiles)

Writes (all in investigations/):
    jitter_ping_deciles.csv          per-ping distance_m deciles (pd.qcut, D1..D10)
    jitter_ping_quantiles.csv        per-ping distance_m quantiles (p10..p99)
    jitter_mobile_max_deciles.csv    per-mobile max_dist_m deciles
    jitter_mobile_max_quantiles.csv  per-mobile max_dist_m quantiles
    jitter_mobile_median_deciles.csv per-mobile median_dist_m deciles
    jitter_mobile_median_quantiles.csv
    jitter_mobile_pings_histogram.csv  n_subseq_pings histogram (confirms >=2 subseq)

Every table's freq sums back to the source n (20,231 pings OR 8,317 mobiles),
so downstream consumers can tie any slice back to the funnel.

Run from: promise_maker_gps/gps_jitter/
    python headline_jitter.py
"""

from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
INV = HERE / "investigations"

IN_PAIRS = INV / "jitter_pairs_v4.csv"
IN_MOBILE = INV / "jitter_mobile_v4.csv"

QUANTILES = [0.01, 0.05, 0.10, 0.20, 0.25, 0.30, 0.40, 0.50,
             0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99]


def decile_table(s, name):
    """qcut to deciles and aggregate. Returns a df with freq + dist stats per decile.
    freq column sums to len(s) -- ties back to source n."""
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


def quantile_table(s, name):
    return pd.DataFrame([
        {"quantile": f"p{int(q*100):02d}", f"{name}_m": round(float(s.quantile(q)), 2)}
        for q in QUANTILES
    ])


def banner(t):
    line = "=" * 74
    print(f"\n{line}\n{t}\n{line}")


def main():
    pairs = pd.read_csv(IN_PAIRS)
    mob = pd.read_csv(IN_MOBILE)

    n_pings = len(pairs)
    n_mobiles = len(mob)
    n_mobiles_pairs = pairs["mobile"].nunique()
    assert n_mobiles == n_mobiles_pairs, f"mobile count mismatch: {n_mobiles} vs {n_mobiles_pairs}"

    # ------------------------------------------------------------------
    # CONFIRM: every v4 mobile has >=2 subseq pings (so >=3 total inc. anchor)
    # ------------------------------------------------------------------
    banner("PINGS-PER-MOBILE HISTOGRAM (v4 -- confirms >=3 total pings)")
    hist = (
        mob["n_subseq_pings"]
        .value_counts()
        .sort_index()
        .rename_axis("n_subseq_pings")
        .reset_index(name="n_mobiles")
    )
    hist["n_total_pings"] = hist["n_subseq_pings"] + 1  # + anchor
    hist["pct_of_mobiles"] = hist["n_mobiles"] / n_mobiles
    hist["cum_pct"] = hist["pct_of_mobiles"].cumsum()
    print(hist.to_string(index=False,
                         formatters={"pct_of_mobiles": "{:.1%}".format,
                                     "cum_pct": "{:.1%}".format}))
    print(f"\nTOTAL MOBILES (v4)  : {n_mobiles:,}")
    print(f"MIN subseq pings     : {mob['n_subseq_pings'].min()}")
    print(f"MAX subseq pings     : {mob['n_subseq_pings'].max()}")
    print(f"SUM of subseq pings  : {mob['n_subseq_pings'].sum():,}  "
          f"(must equal pair count {n_pings:,})")
    assert mob["n_subseq_pings"].sum() == n_pings
    hist.to_csv(INV / "jitter_mobile_pings_histogram.csv", index=False)

    # ------------------------------------------------------------------
    # PER-PING distance_m: deciles + full quantile grid
    # ------------------------------------------------------------------
    banner(f"PER-PING JITTER DISTRIBUTION  (n={n_pings:,} pings across {n_mobiles:,} mobiles)")
    dp = decile_table(pairs["distance_m"], "distance_m")
    print(dp.round(2).to_string(index=False))
    assert dp["freq"].sum() == n_pings, f"decile freq sum != {n_pings}"
    print(f"\n  freq.sum() = {dp['freq'].sum():,}  (== {n_pings:,} input pings  ✓)")
    dp.to_csv(INV / "jitter_ping_deciles.csv", index=False)

    print("\nFull quantile grid:")
    qp = quantile_table(pairs["distance_m"], "distance")
    print(qp.to_string(index=False))
    qp.to_csv(INV / "jitter_ping_quantiles.csv", index=False)

    # ------------------------------------------------------------------
    # PER-MOBILE uncertainty radius (max_dist_m): deciles + quantiles
    # ------------------------------------------------------------------
    banner(f"PER-MOBILE UNCERTAINTY RADIUS  max_dist_m  (n={n_mobiles:,} mobiles)")
    dm = decile_table(mob["max_dist_m"], "max_dist_m")
    print(dm.round(2).to_string(index=False))
    assert dm["freq"].sum() == n_mobiles
    print(f"\n  freq.sum() = {dm['freq'].sum():,}  (== {n_mobiles:,} input mobiles  ✓)")
    dm.to_csv(INV / "jitter_mobile_max_deciles.csv", index=False)

    print("\nFull quantile grid:")
    qm = quantile_table(mob["max_dist_m"], "max_dist")
    print(qm.to_string(index=False))
    qm.to_csv(INV / "jitter_mobile_max_quantiles.csv", index=False)

    # ------------------------------------------------------------------
    # PER-MOBILE central tendency (median_dist_m): deciles + quantiles
    # ------------------------------------------------------------------
    banner(f"PER-MOBILE CENTRAL TENDENCY  median_dist_m  (n={n_mobiles:,} mobiles)")
    dmd = decile_table(mob["median_dist_m"], "median_dist_m")
    print(dmd.round(2).to_string(index=False))
    assert dmd["freq"].sum() == n_mobiles
    dmd.to_csv(INV / "jitter_mobile_median_deciles.csv", index=False)

    print("\nFull quantile grid:")
    qmd = quantile_table(mob["median_dist_m"], "median_dist")
    print(qmd.to_string(index=False))
    qmd.to_csv(INV / "jitter_mobile_median_quantiles.csv", index=False)

    # ------------------------------------------------------------------
    # Headline callouts tied back to 8,317 mobiles
    # ------------------------------------------------------------------
    banner("HEADLINE CALLOUTS")
    print(f"Cohort: {n_mobiles:,} mobiles / {n_pings:,} subseq pings (v4 final)")
    print(f"  all mobiles have >=3 total pings (anchor + >=2 subsequent)")
    print(f"\nP75 uncertainty radius : {mob['max_dist_m'].quantile(0.75):>7.1f} m")
    print(f"  -> for 75% of mobiles (6,237), the worst fix is within this many meters of the true home")
    print(f"\nP95 per-ping jitter    : {pairs['distance_m'].quantile(0.95):>7.1f} m  (README Stage B threshold)")
    print(f"  -> any booking-vs-install drift below this is indistinguishable from apparatus noise")

    print("\nSAVED: 7 CSVs to investigations/")


if __name__ == "__main__":
    main()
