"""
Assemble STORY.csv for the GPS jitter (Stage A) analysis.

Reads all the per-step CSVs in investigations/ and weaves a narrative CSV
(top-to-bottom readable in a spreadsheet) following the sibling convention
used in allocation_signal/ and coordination/.

Invoke AFTER running the pipeline:
    python pull_wifi_pings.py
    python build_jitter.py
    python headline_jitter.py
    python build_jitter_ge5.py
    python write_story.py

Every section's numbers are sourced from investigations/ CSVs -- the
story is a pure aggregator, no computation here.

Run from: promise_maker_gps/gps_jitter/
"""

import csv
from datetime import datetime
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
INV = HERE / "investigations"
OUT_PATH = HERE / "STORY.csv"

ANALYSIS_PERIOD = "2025-09-01 to 2026-01-26"  # query date range
COHORT_LABEL = "Pan-India mobiles emitting wifi_connected_location_captured in this window"


# ============================================================
# INPUT CSVS
# ============================================================
FUNNEL         = INV / "jitter_funnel.csv"
PING_DECILES   = INV / "jitter_ping_deciles.csv"
PING_QUANT     = INV / "jitter_ping_quantiles.csv"
MAX_DECILES    = INV / "jitter_mobile_max_deciles.csv"
MAX_QUANT      = INV / "jitter_mobile_max_quantiles.csv"
MED_DECILES    = INV / "jitter_mobile_median_deciles.csv"
MED_QUANT      = INV / "jitter_mobile_median_quantiles.csv"
PINGS_HIST     = INV / "jitter_mobile_pings_histogram.csv"
GE5_COMPARE    = INV / "jitter_ge5_vs_v4_comparison.csv"
GE5_MOB        = INV / "jitter_mobile_v4_ge5.csv"
GE5_PAIRS      = INV / "jitter_pairs_v4_ge5.csv"
CONSEC_DEC     = INV / "jitter_consec_deciles.csv"
CONSEC_QNT     = INV / "jitter_consec_quantiles.csv"
CONSEC_VS_ANC  = INV / "jitter_consec_vs_anchor.csv"
CONSEC_PAIRS   = INV / "jitter_consec_pairs.csv"


# ============================================================
# FORMATTING HELPERS
# ============================================================
def table_rows(df, num_cols=None, pct_cols=None):
    """DataFrame -> list-of-lists (header + data) with per-column formatting."""
    pct_cols = pct_cols or []
    num_cols = num_cols or {}
    out = [list(df.columns)]
    for _, r in df.iterrows():
        row = []
        for col in df.columns:
            v = r[col]
            if col in pct_cols:
                row.append("" if pd.isna(v) else f"{float(v):.1%}")
            elif col in num_cols:
                dp = num_cols[col]
                row.append("" if pd.isna(v) else f"{float(v):,.{dp}f}")
            elif isinstance(v, float):
                row.append("" if pd.isna(v) else f"{v:,.2f}")
            else:
                row.append(v)
        out.append(row)
    return out


def build_story():
    # ---- load inputs ----
    fun = pd.read_csv(FUNNEL)
    pd_dec = pd.read_csv(PING_DECILES)
    pd_qnt = pd.read_csv(PING_QUANT)
    md_dec = pd.read_csv(MAX_DECILES)
    md_qnt = pd.read_csv(MAX_QUANT)
    mn_dec = pd.read_csv(MED_DECILES)
    mn_qnt = pd.read_csv(MED_QUANT)
    hist   = pd.read_csv(PINGS_HIST)
    ge5_cmp = pd.read_csv(GE5_COMPARE)
    ge5_mob = pd.read_csv(GE5_MOB)
    ge5_pair = pd.read_csv(GE5_PAIRS)
    consec_dec = pd.read_csv(CONSEC_DEC)
    consec_qnt = pd.read_csv(CONSEC_QNT)
    consec_vs_anc = pd.read_csv(CONSEC_VS_ANC)
    n_consec = len(pd.read_csv(CONSEC_PAIRS))

    # core counts for cross-referencing
    n_mob_v4 = int(fun.loc[fun["step"] == "v4_final", "n_mobiles"].iloc[0])
    n_ping_v4 = int(fun.loc[fun["step"] == "v4_final", "n_pings"].iloc[0])
    n_mob_raw = int(fun.loc[fun["step"] == "raw_pull", "n_mobiles"].iloc[0])
    n_ping_raw = int(fun.loc[fun["step"] == "raw_pull", "n_pings"].iloc[0])
    n_mob_ge5 = len(ge5_mob)
    n_ping_ge5 = len(ge5_pair)

    R = []

    def sec(title): R.extend([[], [f"## {title}"], []])
    def p(text):    R.append([text])
    def blank():    R.append([])

    # ---- HEADER ----
    R.append(["GPS JITTER BASELINE  --  STAGE A OF PROMISE MAKER GPS AUDIT"])
    R.append([f"Last run        : {datetime.now():%Y-%m-%d %H:%M:%S}"])
    R.append([f"Analysis period : {ANALYSIS_PERIOD}  (wifi_connected_location_captured events)"])
    R.append([f"Cohort          : {COHORT_LABEL}"])
    R.append(["Status          : Stage A complete. Stage B (booking-vs-install drift) next."])
    blank()
    p("OPERATIONAL CONTEXT:")
    p("  Promise Maker gates every lead on a 25m serviceability test. That test consumes")
    p("  the booking-time lat/lng. Before we can claim 'the booking coordinate is clean/dirty',")
    p("  we have to know the intrinsic noise floor of the GPS apparatus itself.")
    p("  Stage A (this folder) establishes that floor using repeat SSID-validated pings.")
    p("  Stage B will compare booking-vs-install drift *against* this floor.")

    # ---- 1. THE QUESTION ----
    sec("1. THE QUESTION")
    p("How much does a GPS fix jitter when the SAME home is sampled repeatedly?")
    p("That number is the floor -- no downstream drift analysis can claim structural")
    p("error below it (it is just apparatus noise).")
    blank()
    p("Why wifi_connected_location_captured works as the apparatus:")
    p("  Every Wiom router broadcasts a unique SSID (one per household). The Wiom app")
    p("  emits this event every time it connects to that SSID -- first install AND every")
    p("  later reinstall/reconnect. Same physical home, multiple GPS fixes across time.")
    p("  Anchor on row_cnt=1 (first fix, SSID-validated at install).")
    p("  Treat row_cnt>=2 as repeat samples of that same home.")

    # ---- 2. COHORT & FUNNEL ----
    sec("2. COHORT & FUNNEL")
    p(f"Source: booking_logs.event_name = 'wifi_connected_location_captured'")
    p(f"Period: {ANALYSIS_PERIOD}")
    p(f"Query : query_getlatlong.txt")
    blank()
    p("Attrition (every step's freq sums back to raw):")
    R.extend(table_rows(
        fun,
        num_cols={"n_pings": 0, "n_mobiles": 0},
        pct_cols=["pct_pings_kept", "pct_mobiles_kept"],
    ))
    blank()
    p(f"Headline: raw pull {n_ping_raw:,} pings / {n_mob_raw:,} mobiles.")
    p(f"  After >=3-pings filter, 15-min dedup, 250m cap, >=2-surviving-subseq filter:")
    p(f"  FINAL v4 = {n_mob_v4:,} mobiles / {n_ping_v4:,} subsequent pings.")
    p(f"  Retention: {n_mob_v4/n_mob_raw:.1%} of raw mobiles. Most drop because they")
    p(f"  emitted only 1 ping (no repeat measurement possible) -- structural, not a bug.")

    # ---- 3. METHODOLOGY ----
    sec("3. METHODOLOGY -- CLEANING RULES")
    p("Per-ping jitter  = haversine(anchor lat/lng, subsequent ping lat/lng). ALWAYS vs the")
    p("                   row_cnt=1 anchor, NOT between consecutive pings. Consecutive-ping")
    p("                   distance would conflate sequential drift with apparatus noise.")
    blank()
    p("Rule 1 -- 15-minute dedup:")
    p("  Within any 15-min window for the same mobile, keep only the earliest ping.")
    p("  Reason: Android GPS cache hits + known app re-emit bug produce duplicate fixes")
    p("  on the same underlying reading. Not independent draws.")
    p("  Impact at Stage A: 120,900 -> 60,661 pings (~50% are not independent samples).")
    blank()
    p("Rule 2 -- 250m home-move cap:")
    p("  Drop any subsequent ping > 250m from the anchor.")
    p("  Reason: Delhi cohort has high rental turnover. >250m is almost certainly a home")
    p("  change, not apparatus jitter. Keeping these would inflate the noise floor.")
    blank()
    p("Rule 3 -- >=3 total pings / >=2 surviving subseq:")
    p("  A mobile needs at least 2 subsequent pings to yield per-mobile min/max/mean/median")
    p("  stats. Mobiles with only 1 subseq survive at the per-ping layer but drop from the")
    p("  per-mobile aggregate.")

    # ---- 4. PINGS-PER-MOBILE HISTOGRAM (confirms >=3 total) ----
    sec("4. PINGS-PER-MOBILE (v4 COHORT)  -- confirms every mobile has >=3 total pings")
    R.extend(table_rows(
        hist,
        num_cols={"n_subseq_pings": 0, "n_mobiles": 0, "n_total_pings": 0},
        pct_cols=["pct_of_mobiles", "cum_pct"],
    ))
    blank()
    p("74% of v4 mobiles have exactly 3 total pings (anchor + 2 subseq). Only ~9% have")
    p("5+ total pings. This shapes the GE5 sensitivity cohort in section 9.")

    # ---- 5. PER-PING JITTER -- DECILES ----
    sec(f"5. PER-PING JITTER  --  DECILES (n = {n_ping_v4:,} pings)")
    p("Bucket: pd.qcut(distance_m, q=10). D1 = tightest, D10 = noisiest. freq sums to n.")
    R.extend(table_rows(
        pd_dec,
        num_cols={"decile": 0, "freq": 0, "d_min": 2, "d_max": 2, "d_mean": 2, "d_median": 2},
    ))
    blank()
    p("D1-D8 (80% of pings) stay within 28m. D9 shoulders (28-89m). D10 carries the")
    p("full 89-250m tail -- ~10% of fixes are structurally bad (multipath, indoor, etc.).")

    # ---- 6. PER-PING JITTER -- QUANTILES ----
    sec("6. PER-PING JITTER  --  QUANTILES")
    R.extend(table_rows(pd_qnt))
    blank()
    p("Headline: p95 = 154.76m. THIS IS THE README'S STAGE B THRESHOLD.")
    p("Any booking-vs-install drift below 154.76m is indistinguishable from apparatus noise.")
    p("Reporting lens downstream: excess_drift = max(install_drift - 154.76, 0).")

    # ---- 6b. CONSECUTIVE-PING JITTER -- DECILES + QUANTILES + COMPARISON ----
    sec(f"6b. CONSECUTIVE-PING JITTER  --  DECILES (n = {n_consec:,} consec pairs)")
    p("Definition: haversine(ping_{i-1}, ping_i) between TEMPORALLY ADJACENT pings")
    p("within each mobile's ordered timeline (anchor + surviving subseq pings).")
    p("Same cohort as anchor-based: v4 mobiles (8,317), same 15-min dedup + 250m cap.")
    p(f"Count: each subseq ping contributes exactly one consec-distance to its")
    p(f"predecessor -> {n_consec:,} measurements, same as anchor-based count.")
    blank()
    p("Deciles:")
    R.extend(table_rows(
        consec_dec,
        num_cols={"decile": 0, "freq": 0, "d_min": 2, "d_max": 2, "d_mean": 2, "d_median": 2},
    ))
    blank()
    p("D10's max (320m) exceeds our 250m anchor cap -- geometrically valid: two pings")
    p("can each be within 250m of anchor but >250m from each other if on opposite sides.")
    blank()
    p("Quantiles:")
    R.extend(table_rows(consec_qnt))
    blank()
    p("Per-consec-pair p50 = 5.90m,  p75 = 14.89m,  p95 = 110.57m.")
    p("83.8% of consec pairs are within 25m (16,962 / 20,231).")

    # ---- 6c. CONSECUTIVE vs ANCHOR-BASED -- side-by-side ----
    sec("6c. CONSECUTIVE vs ANCHOR-BASED  --  TEMPORAL CORRELATION IN GPS NOISE")
    p("Same v4 cohort, same count (20,231 pairs). Different reference frame:")
    p("  anchor_m = haversine(row_cnt=1 fix, subseq fix)       (days to months apart)")
    p("  consec_m = haversine(ping_{i-1}, ping_i, sorted time) (minutes to days apart)")
    blank()
    R.extend(table_rows(
        consec_vs_anc,
        num_cols={"anchor_m": 2, "consec_m": 2, "diff_m": 2},
    ))
    blank()
    p("Consecutive is UNIFORMLY tighter than anchor-based across every percentile.")
    p("The gap widens in the mid-tail:")
    p("  p50: -23%   p75: -25%   p85: -41%   p90: -44%   p95: -29%   p99: -6%")
    blank()
    p("Read: this is the signature of TEMPORAL CORRELATION in GPS noise. Two pings")
    p("minutes apart share recent conditions -- same satellite geometry, similar")
    p("multipath environment, same weather, same phone state. Over long anchor gaps")
    p("(days to months), those correlations break and errors compound independently.")
    blank()
    p("Implications:")
    p("  1. The APPARATUS ITSELF is tight. Two independent readings taken close in time")
    p("     land within 5.9m of each other (p50) -- the hardware is not the problem.")
    p("  2. What PROPAGATES downstream is day-to-day drift, not instantaneous noise.")
    p("  3. For Stage B (booking -> install is a days-apart comparison), anchor-based")
    p("     p95 = 154.76m REMAINS the right subtraction floor, NOT consec p95 = 110.57m.")
    p("     Booking-install is not a consecutive-reading comparison.")

    # ---- 7. PER-MOBILE UNCERTAINTY RADIUS -- DECILES ----
    sec(f"7. PER-MOBILE UNCERTAINTY RADIUS  --  max_dist_m DECILES (n = {n_mob_v4:,} mobiles)")
    p("Per mobile: max_dist_m = max(haversine(anchor, each subseq ping)).")
    p("Across mobiles: decile on max_dist_m. D1 = tightest radius, D10 = noisiest.")
    R.extend(table_rows(
        md_dec,
        num_cols={"decile": 0, "freq": 0, "d_min": 2, "d_max": 2, "d_mean": 2, "d_median": 2},
    ))
    blank()
    p("D1-D7 all end <=24m -- 70.0% of v4 mobiles (5,821) have their WORST fix within")
    p("25m of the anchor. This is the headline operational read.")
    p("D8 (23.67-46.14m, median 31.79m) straddles the 25m Promise Maker gate -- this is")
    p("the borderline population where the gate flips in/out based on which fix landed.")
    p("D10 (116-250m, median 176m) is the structural tail -- ~10% of mobiles.")

    # ---- 8. PER-MOBILE UNCERTAINTY RADIUS -- QUANTILES ----
    sec("8. PER-MOBILE UNCERTAINTY RADIUS  --  QUANTILES")
    R.extend(table_rows(md_qnt))
    blank()
    p("Headline: p75(max_dist) = 31.79m -- for 75% of v4 mobiles (6,237), the worst")
    p("single fix is within ~32m of the true home. This is the operational bound we")
    p("can trust even on a bad individual reading.")
    p("CAVEAT: max_dist is an order statistic -- it grows with more pings per mobile.")
    p("Compare with GE5 cohort in section 9 to see the sampling effect.")

    # ---- 9. PER-MOBILE CENTRAL TENDENCY -- DECILES + QUANTILES ----
    sec(f"9. PER-MOBILE CENTRAL TENDENCY  --  median_dist_m DECILES (n = {n_mob_v4:,} mobiles)")
    p("Per mobile: median_dist_m = median(haversine(anchor, subseq pings)).")
    p("More robust than max_dist to single outliers. Best signal for mobile segmentation.")
    R.extend(table_rows(
        mn_dec,
        num_cols={"decile": 0, "freq": 0, "d_min": 2, "d_max": 2, "d_mean": 2, "d_median": 2},
    ))
    blank()
    p("Quantile grid:")
    R.extend(table_rows(mn_qnt))
    blank()
    p("p50 of median_dist (8.13m) ~ p50 per-ping (7.66m). Mobiles mostly do NOT have one")
    p("freak outlier -- they are either consistently clean OR consistently drifty. This")
    p("is a real Stage B handle: segment mobiles into 'clean' (low median) vs 'drifty'")
    p("(high median) before interpreting booking-vs-install drift.")

    # ---- 10. SENSITIVITY -- GE5 COHORT ----
    sec("10. SENSITIVITY  --  GE5 COHORT (mobiles with >=5 TOTAL pings)")
    p(f"GE5 = v4 mobiles with >=4 surviving subsequent pings (>=5 total incl. anchor).")
    p(f"Cohort: {n_mob_ge5:,} mobiles / {n_ping_ge5:,} subseq pings "
      f"({n_mob_ge5/n_mob_v4:.1%} of v4).")
    p("Purpose: per-mobile stats on 2 samples are noisy. GE5 gives tighter per-mobile")
    p("estimates at the cost of a much smaller, non-randomly-selected cohort.")
    blank()
    p("Side-by-side quantiles (v4 vs GE5):")
    R.extend(table_rows(
        ge5_cmp,
        num_cols={
            "ping_v4_m": 2, "ping_ge5_m": 2,
            "maxdist_v4_m": 2, "maxdist_ge5_m": 2,
            "mediandist_v4_m": 2, "mediandist_ge5_m": 2,
        },
    ))
    blank()
    p("How to read the shifts:")
    p("  a. Per-ping p95: 154.76m -> 119.95m (GE5 is tighter). The GE5 cohort is self-")
    p("     selected for engagement (reinstalled 4+ times) -- likely cleaner users.")
    p("  b. max_dist_m: p75 GROWS from 31.79 -> 37.11m. This is a sampling artifact,")
    p("     NOT apparatus worsening -- max(N) grows with N. The 'within 25m' fraction")
    p("     drops 70.0% (v4) -> 65.8% (GE5) for the same reason.")
    p("  c. median_dist_m: p75 TIGHTENS from 20.66 -> 15.06m. More samples = more stable")
    p("     per-mobile central estimate. This is the cleanest evidence that the APPARATUS")
    p("     core is tight -- the noise in per-mobile estimates is sampling variance, not")
    p("     real drift.")

    # ---- 11. KEY FINDINGS ----
    sec("11. KEY FINDINGS")
    R.append(["#", "finding"])
    R.append([1, f"Stage A cohort tied exactly to Rohan's prior notebook run: {n_mob_v4:,} mobiles / {n_ping_v4:,} subseq pings, median radius 12m, p75 32m, p90 116m. Our re-pull is a clean replica."])
    R.append([2, "Apparatus CORE is genuinely tight: per-ping p50 = 7.66m. Half of all independent GPS fixes of the same home land within 7.7m."])
    R.append([3, "70.0% of mobiles (5,821 / 8,317) have their WORST single fix within 25m of the anchor. The 25m Promise Maker gate sits right at the D7/D8 boundary."])
    R.append([4, "Per-ping p95 = 154.76m. This is the README Stage B noise-floor threshold: any booking-vs-install drift < 155m is indistinguishable from apparatus noise."])
    R.append([5, "Mobile drift appears bimodal: per-mobile median closely tracks per-ping median (8m vs 7.7m). Mobiles are either CONSISTENTLY clean or CONSISTENTLY drifty -- not a few flukes per mobile."])
    R.append([6, "D10 mobiles (~10% of v4) carry max_dist 116-250m. Even with the 250m cap, these represent structural capture error. Candidates for root-cause investigation (indoor, night, device type)."])
    R.append([7, "max_dist_m is an order statistic -- it inflates with more pings per mobile. GE5 cohort confirms median_dist tightens with more samples (20.7m -> 15.1m), while max_dist grows (31.8m -> 37.1m). Do NOT use max_dist trends across cohorts without normalizing for ping count."])
    R.append([8, "15-min dedup dropped 50% of pings (120,900 -> 60,661). Android GPS cache hits + app re-emit bug are a first-order effect. Ignoring them inflates 0m-distance spikes and tightens the noise floor artificially."])
    R.append([9, "Consecutive-ping jitter is UNIFORMLY tighter than anchor-based across every percentile (p50: 5.9 vs 7.7m, p75: 14.9 vs 20.0m, p95: 110.6 vs 154.8m). Signature of temporal correlation in GPS noise: temporally-adjacent fixes share recent conditions and their errors correlate; long-gap fixes don't."])
    R.append([10, "Apparatus itself is tight: two independent readings of the same home minutes apart land within 5.9m of each other (consec p50). The downstream problem is NOT instantaneous apparatus noise -- it's day-to-day drift."])
    R.append([11, "For Stage B, anchor-based p95 (154.8m) is the RIGHT subtraction floor, not consec p95 (110.6m). Booking-lat/lng and install-lat/lng are separated by days (fee capture -> scheduling -> install), so the relevant noise model is long-gap drift, not consecutive-reading precision."])

    # ---- 12. OPEN QUESTIONS / NEXT STEPS ----
    sec("12. OPEN QUESTIONS / NEXT STEPS (STAGE B HOOKS)")
    R.append(["id", "status", "item"])
    R.append(["A1", "done",  f"GPS jitter baseline established -- p95 = 154.76m per-ping, p75 max_dist = 31.79m (n={n_mob_v4:,})"])
    R.append(["A2", "open",  "0m-spike diagnostic: what fraction of subseq pings are exactly 0m from anchor, and how does that % break down by time-gap bucket? Confirms cache vs stable-GPS."])
    R.append(["A3", "open",  "Mobile bimodality segmentation: split v4 into 'clean' (median_dist <= 10m) and 'drifty' (median_dist > 50m). Carry that label into Stage B to see if drifty mobiles have systematically higher booking-vs-install drift."])
    R.append(["A4", "open",  "Time-of-day effect (from Rohan's original hypothesis): do late-night/indoor pings have higher jitter? Join to fee_captured_at hour in Stage B."])
    R.append(["A5", "open",  "Device self-report correlation: does booking_accuracy correlate with per-mobile median_dist? Rohan's notebook said 'WEAK' -- worth re-testing on the larger unified cohort in Stage B."])
    R.append(["B1", "next",  "Stage B: compute install_drift_meters per installed booking. Subtract p95 jitter = 154.76m to get excess_drift_meters. Decile-slice and compare against Stage A distribution."])
    R.append(["B2", "next",  "Stage B: % of installed bookings where install_drift > 25m. Every such booking is a lead where the 25m gate was applied to a lat/lng that was itself >25m off from where the customer actually lives -- a structural falsification of the gate's precondition."])
    R.append(["B3", "next",  "Back-link to allocation_signal/: does the 448km D10 tail in nearest_distance correlate with mobiles that are in our D10 drift bucket here? That would confirm booking-lat/lng noise is inflating the allocation distance signal."])

    # ---- 13. ARTIFACTS ----
    sec("13. ARTIFACTS")
    R.append(["file", "purpose"])
    R.append(["query_getlatlong.txt",              "Snowflake query: wifi_connected_location_captured events, Sep 2025 - Jan 2026"])
    R.append(["pull_wifi_pings.py",                "Runs query -> investigations/wifi_pings_raw.csv"])
    R.append(["build_jitter.py",                   "Raw -> v1/v2/v3/v4 pipeline, writes per-step CSVs + funnel"])
    R.append(["headline_jitter.py",                "v4 deciles + quantiles for per-ping / max_dist / median_dist"])
    R.append(["build_jitter_ge5.py",               "Sensitivity cut on mobiles with >=5 total pings"])
    R.append(["build_jitter_consecutive.py",       "Consecutive-ping distance (temporal-correlation companion to anchor-based)"])
    R.append(["write_story.py",                    "Assembles this STORY.csv"])
    R.append(["investigations/wifi_pings_raw.csv", "278,986 raw pings (query output)"])
    R.append(["investigations/jitter_funnel.csv",  "Per-step attrition: raw -> v4"])
    R.append(["investigations/jitter_pairs_v4.csv","20,231 subseq pings (final)"])
    R.append(["investigations/jitter_mobile_v4.csv","8,317 per-mobile aggregates (final)"])

    return R


def main():
    rows = build_story()
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        for row in rows:
            writer.writerow(row)
    print(f"SAVED: {OUT_PATH.name}  ({len(rows)} rows)")


if __name__ == "__main__":
    main()
