"""
Assemble STORY.csv for Stage B (booking-vs-install distance).

Reads investigations/ outputs from pull_install_drift.py + build_drift.py
and weaves a narrative CSV following the sibling convention.

IMPORTANT framing note carried through the story: the 25m Promise Maker
gate tests booking_lat/lng against the NEAREST HISTORICAL INSTALL, not
against the true home. Drift is invisible to the gate. The reference
bands in this story characterize the drift distribution against two
reference points (25m gate radius, Stage A p95 apparatus noise), NOT
gate outcomes.

Run from: promise_maker_gps/booking_install_distance/
    python write_story.py
"""

import csv
from datetime import datetime
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
INV = HERE / "investigations"
OUT_PATH = HERE / "STORY.csv"

ANALYSIS_PERIOD_BOOKING = "2025-12-01 to 2026-01-01  (booking events, Delhi)"
ANALYSIS_PERIOD_INSTALL = "2025-12-01 to 2026-02-28  (install pings, 2-mo lookahead)"
COHORT_LABEL = "Delhi, Dec 2025 installed bookings, non-BDO (bdo_lead=0 Python-side filter)"
STAGE_A_P95 = 154.76
PROMISE_GATE = 25.0


FUNNEL       = INV / "drift_funnel.csv"
DRIFT_DEC    = INV / "drift_deciles.csv"
DRIFT_QNT    = INV / "drift_quantiles.csv"
EXCESS_DEC   = INV / "excess_drift_deciles.csv"
EXCESS_QNT   = INV / "excess_drift_quantiles.csv"
BANDS        = INV / "drift_gate_bands.csv"
CLEAN        = INV / "drift_cohort_clean.csv"


def table_rows(df, num_cols=None, pct_cols=None):
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
    fun = pd.read_csv(FUNNEL)
    drift_dec = pd.read_csv(DRIFT_DEC)
    drift_qnt = pd.read_csv(DRIFT_QNT)
    excess_dec = pd.read_csv(EXCESS_DEC)
    excess_qnt = pd.read_csv(EXCESS_QNT)
    bands = pd.read_csv(BANDS)
    clean = pd.read_csv(CLEAN)

    n_clean = int(fun.loc[fun["step"] == "stage_b_clean", "n_rows"].iloc[0])
    n_raw = int(fun.loc[fun["step"] == "raw_pull", "n_rows"].iloc[0])

    R = []
    def sec(title): R.extend([[], [f"## {title}"], []])
    def p(text): R.append([text])
    def blank(): R.append([])

    # ---- HEADER ----
    R.append(["BOOKING-vs-INSTALL DISTANCE  --  STAGE B OF PROMISE MAKER GPS AUDIT"])
    R.append([f"Last run              : {datetime.now():%Y-%m-%d %H:%M:%S}"])
    R.append([f"Analysis period (bkg) : {ANALYSIS_PERIOD_BOOKING}"])
    R.append([f"Analysis period (inst): {ANALYSIS_PERIOD_INSTALL}"])
    R.append([f"Cohort                : {COHORT_LABEL}"])
    R.append([f"Stage A reference     : p95 = {STAGE_A_P95}m (per-ping jitter, from ../gps_jitter/STORY.csv section 6)"])
    R.append(["Status                : Stage B cohort pulled, funnel built, deciles computed."])
    blank()
    p("OPERATIONAL CONTEXT + FRAMING CORRECTION (read before interpreting numbers):")
    p("  The 25m Promise Maker gate tests:")
    p(f"      distance(booking_lat/lng, nearest historical install or splitter) <= 25m")
    p("  It does NOT test drift. It does NOT test 'is booking_lat/lng accurate'.")
    p("  Drift is invisible to the gate itself.")
    blank()
    p("  What Stage B measures is INPUT QUALITY LOSS:")
    p("      install_drift_m = haversine(booking_lat/lng, first wifi_connected_location_captured)")
    p("  That number tells us how far booking_lat/lng is from the SSID-validated true")
    p("  home. Every downstream consumer that trusts booking_lat/lng ~ true home")
    p("  (Promise Maker, Allocation GNN's nearest_distance, partner navigation) is")
    p("  operating on a point that drifts from ground truth by this distance.")

    # ---- 1. THE QUESTION ----
    sec("1. THE QUESTION")
    p("How reliable is booking_lat/lng as an input to downstream matchmaking systems?")
    p("How much of the observed booking-vs-install drift is pure GPS apparatus noise")
    p("(physically unavoidable) vs structural booking-capture error (upstream-fixable)?")

    # ---- 2. COHORT & FUNNEL ----
    sec("2. COHORT & FUNNEL")
    p(f"Source  : query_install_drift.txt (this folder)")
    p(f"Booking : {ANALYSIS_PERIOD_BOOKING}")
    p(f"Install : {ANALYSIS_PERIOD_INSTALL}")
    p(f"Key columns: booking_lat/lng (from lead_state='serviceable'), install_lat/lng")
    p(f"(from first wifi_connected_location_captured), booking_accuracy, bdo_lead,")
    p(f"time_bucket, install_drift_m (haversine, SQL-side).")
    blank()
    p("Funnel (ALL counts tie back to raw):")
    R.extend(table_rows(
        fun,
        num_cols={"n_rows": 0},
        pct_cols=["pct_kept_vs_raw"],
    ))
    blank()
    p(f"RAW PULL = {n_raw:,} Delhi Dec-2025 installed mobiles.")
    p(f"After BDO drop + null-coord drops, STAGE B CLEAN COHORT = {n_clean:,}")
    p(f"({n_clean/n_raw:.1%} of raw). BDO dominates (60% of installed cohort) --")
    p(f"consistent with the ops-led install pattern seen in allocation_signal/.")

    # ---- 3. METHODOLOGY ----
    sec("3. METHODOLOGY -- WHAT COUNTS AS DRIFT")
    p("For each installed non-BDO booking:")
    p("  install_drift_m = haversine(booking_lat, booking_lng, install_lat, install_lng)")
    blank()
    p("Where:")
    p("  booking_lat/lng  : from the LATEST lead_state='serviceable' event before Jan 1")
    p("                     (this is what Promise Maker actually gated on)")
    p("  install_lat/lng  : from the FIRST wifi_connected_location_captured event")
    p("                     (SSID-validated fix at the true home, post-install)")
    blank()
    p("Stage A p95 subtraction:")
    p(f"  excess_drift_m = max(install_drift_m - {STAGE_A_P95}, 0)")
    p("  Any drift below Stage A p95 is indistinguishable from pure apparatus noise")
    p("  over a days-apart gap (booking -> install is typically a few days).")
    p("  Drift above Stage A p95 is structural capture error.")

    # ---- 4. HEADLINE: DRIFT DISTRIBUTION ----
    sec(f"4. DRIFT DISTRIBUTION -- DECILES  (n = {n_clean:,})")
    p("pd.qcut on install_drift_m. D1 = tightest, D10 = widest. freq sums to n.")
    R.extend(table_rows(
        drift_dec,
        num_cols={"decile": 0, "freq": 0, "d_min": 2, "d_max": 2, "d_mean": 2, "d_median": 2},
    ))
    blank()
    p("D1-D5 (50% of cohort) have drift <= 22.52m.")
    p("D6 (22.52-47.05m) just exceeds the 25m reference point.")
    p("D7 (47.21-117.57m) is within Stage A apparatus noise (< p95 = 154.76m).")
    p("D8 (118.04-232.74m) crosses the Stage A p95 -- entering structural territory.")
    p("D9 (232.86-477.62m) and D10 (479.29-213,846m) are unambiguously structural.")

    # ---- 5. DRIFT QUANTILES ----
    sec("5. DRIFT QUANTILES")
    R.extend(table_rows(drift_qnt))
    blank()
    p("Headlines:")
    p("  p50 = 22.52m  -- the MEDIAN drift sits right at the 25m reference.")
    p("  p75 = 162.65m -- the top quartile drifts BEYOND Stage A's noise floor.")
    p("  p95 = 767.16m -- 1 in 20 bookings has drift >3/4 km from true home.")
    p("  p99 = 2,870.83m -- 1 in 100 has drift > 2.9km.")

    # ---- 6. STAGE A vs STAGE B SIDE-BY-SIDE ----
    sec("6. STAGE A (apparatus noise) vs STAGE B (booking->install drift)")
    p("Same quantile, different reference frame. Stage A = per-ping jitter across")
    p("days/months against the anchor (pure apparatus noise). Stage B = booking->install")
    p("drift (apparatus noise + any booking-time capture error).")
    blank()
    cmp = pd.DataFrame([
        {"quantile": "p50", "stage_a_m": 7.66,   "stage_b_m": 22.52,   "ratio": "2.9x"},
        {"quantile": "p75", "stage_a_m": 19.98,  "stage_b_m": 162.65,  "ratio": "8.1x"},
        {"quantile": "p90", "stage_a_m": 88.61,  "stage_b_m": 478.62,  "ratio": "5.4x"},
        {"quantile": "p95", "stage_a_m": 154.76, "stage_b_m": 767.16,  "ratio": "5.0x"},
        {"quantile": "p99", "stage_a_m": 227.89, "stage_b_m": 2870.83, "ratio": "12.6x"},
    ])
    R.extend(table_rows(
        cmp,
        num_cols={"stage_a_m": 2, "stage_b_m": 2},
    ))
    blank()
    p("Stage B is UNIFORMLY wider than Stage A at every quantile. Booking capture")
    p("adds structural error on top of apparatus noise across the entire distribution,")
    p("not just in the tail. The multiplier peaks at p75 (8x) and p99 (13x).")

    # ---- 7. EXCESS DRIFT -- STAGE A ABSORPTION ----
    sec("7. EXCESS DRIFT  (= max(install_drift_m - Stage A p95, 0))")
    p(f"Zero-excess (drift <= {STAGE_A_P95}m, absorbed by Stage A):")
    zero_excess = int((clean["excess_drift_m"] == 0).sum())
    R.append([f"  {zero_excess:,} / {n_clean:,} installs ({zero_excess/n_clean:.1%}) -- apparatus noise fully explains these drifts"])
    R.append([f"  {n_clean - zero_excess:,} / {n_clean:,} installs ({(n_clean - zero_excess)/n_clean:.1%}) -- STRUCTURAL capture error exists"])
    blank()
    p("Excess drift deciles (80% of cohort collapsed into D1 at zero):")
    R.extend(table_rows(
        excess_dec,
        num_cols={"decile": 0, "freq": 0, "d_min": 2, "d_max": 2, "d_mean": 2, "d_median": 2},
    ))
    blank()
    p("Excess drift quantiles:")
    R.extend(table_rows(excess_qnt))
    blank()
    p("Reading: the NON-zero excess mass (25.7%) has median excess drift of 186m,")
    p("p90 of 324m, p99 of 2.7km. These bookings had coords that were wrong BEYOND")
    p("anything GPS physics can produce -- i.e., stale cache, user error, UI mistake.")

    # ---- 8. REFERENCE BANDS (CAREFUL FRAMING) ----
    sec("8. DRIFT REFERENCE BANDS  --  NOT GATE OUTCOMES")
    p("IMPORTANT FRAMING: these bands classify the DRIFT distribution against two")
    p("reference points (25m gate radius, Stage A p95). They are NOT the outcome of")
    p("the 25m Promise Maker gate, which never tests drift.")
    blank()
    R.extend(table_rows(
        bands,
        num_cols={"n": 0, "drift_min": 2, "drift_max": 2, "drift_median": 2},
        pct_cols=["pct"],
    ))
    blank()
    p("Interpretation of each band:")
    p("  A. <=25m           : drift is smaller than the gate's own search radius.")
    p("                       Even if the gate relied on drift tolerance, it would be OK.")
    p("  B. 25-154.76m      : drift exceeds gate radius BUT fits within Stage A apparatus")
    p("                       noise. Looks 'drifty' but could be explained by GPS physics.")
    p("  C. >154.76m        : drift exceeds what Stage A apparatus noise can produce.")
    p("                       Structural capture error -- upstream process/UI issue.")
    blank()
    p("51.5% in Band A tells us the booking coord is 'close enough' to the true home")
    p("in half the cases. The other 48.5% is where downstream systems receive a")
    p("degraded-to-bad coordinate.")

    # ---- 9. KEY FINDINGS ----
    sec("9. KEY FINDINGS")
    R.append(["#", "finding"])
    R.append([1, f"Stage B clean cohort = {n_clean:,} Delhi Dec-2025 installed bookings (non-BDO, both coords present). 39.5% of raw pull survives after dropping BDO (60%) and null-coord rows (0.5%)."])
    R.append([2, "Median booking->install drift = 22.5m. Half of installed bookings have booking coord drifted by more than the 25m Promise Maker gate radius would consider 'precise'."])
    R.append([3, "p75 drift = 162.7m. Top quartile of installed bookings has booking coord drifted BEYOND Stage A's apparatus-noise p95 (154.8m)."])
    R.append([4, "25.7% of installs (991 of 3,855) have drift > Stage A p95. These are STRUCTURAL booking-capture errors -- wrong coordinates that GPS physics alone cannot produce. 3.2% have drift > 1km; 0.4% > 10km."])
    R.append([5, "Stage B is uniformly wider than Stage A at every quantile (2.9x at p50, 8.1x at p75, 5x at p95, 12.6x at p99). The booking-capture process adds error on top of apparatus noise across the entire distribution, not just in the tail."])
    R.append([6, "The 25m Promise Maker gate does NOT test drift (it tests booking_lat/lng vs nearest historical install). Drift is invisible to the gate. But the gate's BALL is centered on the booking coord -- if that coord is 100m off, the gate's 25m search is centered 100m off from the true home. Downstream gate behavior is therefore corrupted by the drift distribution, even though the gate never sees drift directly."])
    R.append([7, "Catastrophic data-hygiene tail: 16 installs (0.4%) have drift > 10km; max = 213km. Almost certainly wrong-city/wrong-address bookings. Worth isolating before any retrain that consumes booking_lat/lng as a feature."])

    # ---- 10. OPEN QUESTIONS / NEXT STEPS ----
    sec("10. OPEN QUESTIONS / NEXT STEPS")
    R.append(["id", "status", "item"])
    R.append(["B1", "open",  "Does drift distribute unevenly across time_bucket? Rohan's hypothesis: late-night/indoor captures are noisier. Test on this cohort."])
    R.append(["B2", "open",  "Does booking_accuracy (device self-report) correlate with install_drift_m? Rohan's notebook said WEAK on smaller cohort -- retest on n=3,855."])
    R.append(["B3", "open",  "Catastrophic-tail isolation: 16 installs with drift > 10km. Pull their booking_lat/lng, install_lat/lng, time_bucket -- are they wrong-city, wrong-pincode, or just tap-errors?"])
    R.append(["B4", "open",  "Decline-cohort comparison: pull Delhi Dec-2025 DECLINED bookings (same query minus installed-mobiles join). Compare booking_accuracy and time_bucket distributions. If declined shows different pattern than installed, Promise Maker has a systematic admit-bias tied to booking GPS noise."])
    R.append(["B5", "open",  "Cross-link back to allocation_signal/: does Stage B drift correlate with nearest_distance D10 tail (448km outliers)? Merge on mobile."])
    R.append(["B6", "open",  "Intervention candidates: pincode reverse-geocode cross-check, force re-capture on low booking_accuracy, map-pin confirmation with landmarks. Each would reduce the 25.7% structural-error mass."])

    # ---- 11. ARTIFACTS ----
    sec("11. ARTIFACTS")
    R.append(["file", "purpose"])
    R.append(["query_install_drift.txt",         "Snowflake query (simpler than parent's Location capture funnel.sql) -- installed-only, bdo_lead as column"])
    R.append(["pull_install_drift.py",           "Runs query -> investigations/install_drift_raw.csv, prints coverage + quicklook"])
    R.append(["build_drift.py",                  "Python-side funnel (drop BDO, drop nulls), deciles, quantiles, reference bands"])
    R.append(["write_story.py",                  "Assembles this STORY.csv"])
    R.append(["investigations/install_drift_raw.csv", f"{n_raw:,} raw rows"])
    R.append(["investigations/drift_funnel.csv",    "Per-step attrition"])
    R.append(["investigations/drift_cohort_clean.csv", f"{n_clean:,} clean rows + excess_drift_m + drift_band"])
    R.append(["investigations/drift_deciles.csv, drift_quantiles.csv", "Full grids for install_drift_m"])
    R.append(["investigations/excess_drift_deciles.csv, excess_drift_quantiles.csv", "Full grids for excess_drift_m"])
    R.append(["investigations/drift_gate_bands.csv", "Three-band distribution"])

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
