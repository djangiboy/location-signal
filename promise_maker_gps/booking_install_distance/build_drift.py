"""
Stage B: Python-side funnel + drift distribution.

Reads investigations/install_drift_raw.csv (9,749 rows, mobile-keyed)
and produces:
    - step-by-step attrition (drift_funnel.csv)
    - cleaned cohort (drift_cohort_clean.csv)
    - deciles for install_drift_m and excess_drift_m
    - quantile grids for both
    - gate categorization (<=25m, 25-154.76m, >154.76m)

Stage A subtraction floor = 154.76m (per-ping p95 from gps_jitter/STORY.csv).

Run from: promise_maker_gps/booking_install_distance/
    python build_drift.py
"""

from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
INV = HERE / "investigations"

IN_RAW = INV / "install_drift_raw.csv"
OUT_FUNNEL = INV / "drift_funnel.csv"
OUT_CLEAN = INV / "drift_cohort_clean.csv"
OUT_DRIFT_DECILES = INV / "drift_deciles.csv"
OUT_DRIFT_QUANTILES = INV / "drift_quantiles.csv"
OUT_EXCESS_DECILES = INV / "excess_drift_deciles.csv"
OUT_EXCESS_QUANTILES = INV / "excess_drift_quantiles.csv"
OUT_GATE_BANDS = INV / "drift_gate_bands.csv"

# Stage A noise floor (per-ping p95, from ../gps_jitter/STORY.csv section 6)
STAGE_A_P95 = 154.76
PROMISE_GATE = 25.0

QUANTILES = [0.01, 0.05, 0.10, 0.20, 0.25, 0.30, 0.40, 0.50,
             0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99]


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


def quantile_table(s, name):
    return pd.DataFrame([
        {"quantile": f"p{int(q*100):02d}", f"{name}_m": round(float(s.quantile(q)), 2)}
        for q in QUANTILES
    ])


def banner(t):
    print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


def main():
    a = pd.read_csv(IN_RAW)
    n_raw = len(a)

    banner("BUILD_DRIFT  --  Stage B Python-side funnel")
    print(f"RAW PULL: {n_raw:,} rows (mobile-keyed)")

    funnel = [{
        "step": "raw_pull",
        "n_rows": n_raw,
        "pct_kept_vs_raw": 1.0,
        "note": "Delhi Dec-2025 installed cohort, mobile-keyed",
    }]

    # ==============================================================
    # STEP 1 -- drop BDO leads
    # ==============================================================
    n_bdo = int((a["bdo_lead"] == 1).sum())
    b = a[a["bdo_lead"] == 0].copy()
    n1 = len(b)
    print(f"\n--- STEP 1: drop bdo_lead=1 (non-self-serve journey) ---")
    print(f"ROWS: {n_raw:,} -> {n1:,}  ({n_bdo:,} dropped, {n_bdo/n_raw:.1%})")
    funnel.append({
        "step": "drop_bdo",
        "n_rows": n1, "pct_kept_vs_raw": n1 / n_raw,
        "note": f"dropped {n_bdo} BDO leads (ops-captured, different journey)",
    })

    # ==============================================================
    # STEP 2 -- drop null booking coords (should be 0, but gate it)
    # ==============================================================
    null_book = b[["booking_lat", "booking_lng"]].isna().any(axis=1).sum()
    b = b.dropna(subset=["booking_lat", "booking_lng"]).copy()
    n2 = len(b)
    print(f"\n--- STEP 2: drop null booking_lat/lng ---")
    print(f"ROWS: {n1:,} -> {n2:,}  ({null_book:,} dropped)")
    funnel.append({
        "step": "drop_null_booking_coords",
        "n_rows": n2, "pct_kept_vs_raw": n2 / n_raw,
        "note": f"dropped {null_book} rows with missing booking lat/lng",
    })

    # ==============================================================
    # STEP 3 -- drop null install coords (SSID never connected)
    # ==============================================================
    null_inst = b[["install_lat", "install_lng"]].isna().any(axis=1).sum()
    c = b.dropna(subset=["install_lat", "install_lng"]).copy()
    n3 = len(c)
    print(f"\n--- STEP 3: drop null install_lat/lng ---")
    print(f"ROWS: {n2:,} -> {n3:,}  ({null_inst:,} dropped)")
    print(f"  (installed but SSID never fired wifi_connected_location_captured)")
    funnel.append({
        "step": "drop_null_install_coords",
        "n_rows": n3, "pct_kept_vs_raw": n3 / n_raw,
        "note": f"dropped {null_inst} rows where SSID never connected within 2-month lookahead",
    })

    # Sanity: install_drift_m should be non-null wherever both coords exist
    assert c["install_drift_m"].notna().all(), "install_drift_m null after dropping null coords"

    # ==============================================================
    # STEP 4 -- CLEAN COHORT
    # ==============================================================
    n_clean = len(c)
    print(f"\n--- STAGE B CLEAN COHORT: {n_clean:,} installed bookings ---")
    print(f"  ({n_clean/n_raw:.1%} of raw pull; {n_clean/n1:.1%} of non-BDO)")
    funnel.append({
        "step": "stage_b_clean",
        "n_rows": n_clean, "pct_kept_vs_raw": n_clean / n_raw,
        "note": "final Stage B analysis cohort (non-BDO, non-null coords)",
    })

    # ==============================================================
    # STEP 5 -- compute excess_drift_m net of Stage A p95
    # ==============================================================
    c["excess_drift_m"] = (c["install_drift_m"] - STAGE_A_P95).clip(lower=0)

    # Categorize into reference bands. NOTE: these boundaries are reference
    # points, NOT gate outcomes. The 25m Promise Maker gate tests distance
    # from booking_lat/lng to the nearest historical install, NOT drift.
    # Drift is invisible to the gate. These bands tell us how much of the
    # booking coord's drift is apparatus-explainable vs structural.
    c["drift_band"] = np.where(
        c["install_drift_m"] <= PROMISE_GATE,
        "A. <=25m (within Promise Maker gate radius)",
        np.where(
            c["install_drift_m"] <= STAGE_A_P95,
            "B. 25-154.76m (within Stage A p95 -- apparatus-explainable)",
            "C. >154.76m (beyond apparatus -- structural capture error)",
        ),
    )

    # ==============================================================
    # BAND DISTRIBUTION -- reference bands, NOT gate outcomes
    # ==============================================================
    banner(f"DRIFT REFERENCE BANDS  (n = {n_clean:,} clean installs)")
    print("NOTE: these bands characterize the DRIFT distribution against two reference")
    print("points (25m gate radius, Stage A p95 apparatus noise floor). The 25m Promise")
    print("Maker gate tests booking_lat/lng vs nearest historical install -- it does NOT")
    print("test drift directly. Drift is invisible to the gate. These bands tell us how")
    print("much of the observed drift is apparatus-explainable vs structural capture error.\n")
    band_tab = (
        c.groupby("drift_band")
        .agg(
            n=("mobile", "size"),
            drift_min=("install_drift_m", "min"),
            drift_max=("install_drift_m", "max"),
            drift_median=("install_drift_m", "median"),
        )
        .reset_index()
    )
    band_tab["pct"] = band_tab["n"] / n_clean
    print(band_tab.round(2).to_string(index=False, formatters={"pct": "{:.1%}".format}))
    assert band_tab["n"].sum() == n_clean
    print(f"\n  n.sum = {band_tab['n'].sum():,}  (== {n_clean:,} clean installs  ✓)")
    band_tab.to_csv(OUT_GATE_BANDS, index=False)

    # ==============================================================
    # DRIFT DECILES
    # ==============================================================
    banner(f"INSTALL_DRIFT_M  --  DECILES (n = {n_clean:,})")
    dd = decile_table(c["install_drift_m"], "install_drift_m")
    print(dd.round(2).to_string(index=False))
    assert dd["freq"].sum() == n_clean
    print(f"\n  freq.sum = {dd['freq'].sum():,}  (== {n_clean:,} clean installs  ✓)")
    dd.to_csv(OUT_DRIFT_DECILES, index=False)

    # ==============================================================
    # DRIFT QUANTILES
    # ==============================================================
    banner("INSTALL_DRIFT_M  --  QUANTILES")
    dq = quantile_table(c["install_drift_m"], "install_drift")
    print(dq.to_string(index=False))
    dq.to_csv(OUT_DRIFT_QUANTILES, index=False)

    # ==============================================================
    # EXCESS DRIFT DECILES (many zeros -- use duplicates='drop')
    # ==============================================================
    banner(f"EXCESS_DRIFT_M = max(install_drift_m - {STAGE_A_P95}, 0)  --  DECILES")
    zero_excess = int((c["excess_drift_m"] == 0).sum())
    print(f"Zero-excess (drift <= {STAGE_A_P95}m, absorbed by Stage A): "
          f"{zero_excess:,} ({zero_excess/n_clean:.1%})")
    print(f"Non-zero excess: {n_clean - zero_excess:,} "
          f"({(n_clean - zero_excess)/n_clean:.1%})\n")

    ed = decile_table(c["excess_drift_m"], "excess_drift_m")
    print(ed.round(2).to_string(index=False))
    # NOTE: qcut with many zeros collapses low deciles. Total may be < n_clean if
    # duplicates dropped entire bins; print both counts to make the shift visible.
    print(f"\n  freq.sum = {ed['freq'].sum():,}  (cohort n = {n_clean:,})")
    ed.to_csv(OUT_EXCESS_DECILES, index=False)

    banner("EXCESS_DRIFT_M  --  QUANTILES")
    eq = quantile_table(c["excess_drift_m"], "excess_drift")
    print(eq.to_string(index=False))
    eq.to_csv(OUT_EXCESS_QUANTILES, index=False)

    # ==============================================================
    # HEADLINE CALLOUTS
    # ==============================================================
    banner("HEADLINE CALLOUTS")
    within_25 = (c["install_drift_m"] <= PROMISE_GATE).sum()
    within_155 = (c["install_drift_m"] <= STAGE_A_P95).sum()
    over_155 = n_clean - within_155
    gt_1km = (c["install_drift_m"] > 1000).sum()
    gt_10km = (c["install_drift_m"] > 10000).sum()

    print(f"Stage B cohort         : {n_clean:,} installed bookings (non-BDO, both coords present)")
    print(f"")
    print(f"Drift distribution headlines (booking_lat/lng -> true-home SSID fix):")
    print(f"  p50 drift                    : {c['install_drift_m'].median():>8.1f} m")
    print(f"  p75 drift                    : {c['install_drift_m'].quantile(0.75):>8.1f} m")
    print(f"  p95 drift                    : {c['install_drift_m'].quantile(0.95):>8.1f} m")
    print(f"")
    print(f"Reference bands (NOT gate outcomes -- gate never tests drift):")
    print(f"  <=25m (within gate radius)            : {within_25:>5,}  ({within_25/n_clean:.1%})")
    print(f"  25-154.76m (within Stage A p95 jitter): "
          f"{within_155 - within_25:>5,}  ({(within_155 - within_25)/n_clean:.1%})")
    print(f"  >154.76m (beyond apparatus -- structural capture error): "
          f"{over_155:>5,}  ({over_155/n_clean:.1%})")
    print(f"")
    print(f"Data-hygiene tail:")
    print(f"  >1km                          : {gt_1km:>5,}  ({gt_1km/n_clean:.1%})")
    print(f"  >10km                         : {gt_10km:>5,}  ({gt_10km/n_clean:.1%})")
    print(f"")
    print(f"Stage-A-relative read:")
    print(f"  Median excess_drift          : {c['excess_drift_m'].median():>6.1f} m  "
          f"(post Stage A p95 subtraction)")
    print(f"  {over_155:,} / {n_clean:,} ({over_155/n_clean:.1%}) of installs have drift")
    print(f"  exceeding the Stage A apparatus-noise p95. These are structurally wrong")
    print(f"  booking coordinates -- beyond anything GPS physics alone can produce.")

    # ==============================================================
    # WRITE
    # ==============================================================
    pd.DataFrame(funnel).to_csv(OUT_FUNNEL, index=False)
    c.to_csv(OUT_CLEAN, index=False)
    print(f"\nSAVED:")
    print(f"  {OUT_FUNNEL.name}        (funnel attrition, {len(funnel)} rows)")
    print(f"  {OUT_CLEAN.name}         (clean cohort + excess_drift + gate_band, {n_clean:,} rows)")
    print(f"  {OUT_GATE_BANDS.name}    (band table, {len(band_tab)} rows)")
    print(f"  {OUT_DRIFT_DECILES.name}  (install_drift deciles, 10 rows)")
    print(f"  {OUT_DRIFT_QUANTILES.name} (install_drift quantiles, {len(QUANTILES)} rows)")
    print(f"  {OUT_EXCESS_DECILES.name} (excess_drift deciles)")
    print(f"  {OUT_EXCESS_QUANTILES.name} (excess_drift quantiles)")


if __name__ == "__main__":
    main()
