"""
STORY.csv builder for polygon_analysis subfolder.
Reads the investigative/ CSVs and assembles a single-file narrative.
"""

import csv
from datetime import datetime
from pathlib import Path
import pandas as pd


HERE = Path(__file__).resolve().parent
INV  = HERE / "investigative"
OUT  = HERE / "STORY.csv"


def table_rows(df, num_cols=None):
    num_cols = num_cols or {}
    out = [list(df.columns)]
    for _, r in df.iterrows():
        row = []
        for col in df.columns:
            v = r[col]
            if col in num_cols:
                dp = num_cols[col]
                row.append("" if pd.isna(v) else f"{float(v):,.{dp}f}")
            elif isinstance(v, float):
                row.append("" if pd.isna(v) else f"{v:,.2f}")
            else:
                row.append(v)
        out.append(row)
    return out


def build():
    R = []
    def sec(t):   R.append([]); R.append([f"## {t}"]); R.append([])
    def p(t):     R.append([t])
    def blank():  R.append([])

    R.append(["# Polygon-based analysis — partner serviceable boundaries vs pair install"])
    R.append(["Created: 2026-04-20 11:29"])
    R.append([f"Updated: {datetime.now().isoformat(timespec='minutes')}"])
    R.append(["Cohort: 2,561 pairs (Jan-Mar 2026 Delhi non-BDO) from ../pair_aggregated.csv"])
    R.append(["Polygon source: promise_maker/B/training/partner_cluster_boundaries.h5"])
    R.append(["  1,840 cluster polygons across 1,105 partners"])
    R.append(["  built via DBSCAN over hex cells above p30 install density"])
    blank()

    # 1. Objective
    sec("1. Objective")
    p("Test whether the partner's proven serviceable polygon (built from "
      "install history) is a stronger moderator of install success than "
      "raw `nearest_distance`.")
    p("Three questions:")
    p("  (a) Of 2,561 pairs, how many are eligible (partner has a polygon)?")
    p("  (b) Does being INSIDE vs OUTSIDE the polygon change install rate "
      "and reason mix?")
    p("  (c) For pairs INSIDE, does depth (distance-from-edge / from-center) "
      "further differentiate?")
    p("Polygons vary in shape per partner — both raw meters and normalized "
      "(by equivalent_radius = sqrt(area_km2*1e6/pi)) are computed.")

    # 1b. Polygon construction — the SE correction
    sec("1b. How the polygon is actually built (supply-efficiency map)")
    p("Verified from promise_maker/B/training/hex.py:")
    p("  se = installs / total     # total = installs + declines")
    p("  color = crimson (se <= bad) | orange (se <= mid) | lightgreen (se > mid)")
    p("find_boundary.py keeps only 'lightgreen' + 'orange' hexes before DBSCAN.")
    p("CRIMSON hexes (partner tried, mostly declined) are EXCLUDED.")
    blank()
    p("Implication: polygon is a SUPPLY-EFFICIENCY map, not raw install history.")
    p("- Two partners with same install count but different decline patterns")
    p("  get DIFFERENT polygons — declines SHRINK the polygon.")
    p("- 'Inside' = partner has high SE here (CAN install + WILL try).")
    p("- 'Outside' = partner never tried OR tried-and-mostly-declined.")
    p("- Polygon is dynamic — updates with every install/decline decision.")
    p("- We use the Feb 2026 snapshot.")

    # 2. Method
    sec("2. Method")
    p("Spatial join via geopandas (predicate='within').")
    p("  - Pair booking coords from allocation_cohort.csv (same booking_location "
      "CTE as query_pcalls.txt).")
    p("  - CRS: WGS84 for I/O, UTM zone 43N (EPSG:32643) for distance.")
    p("  - Per pair, multiple partner polygons reduced via tie-break: "
      "deepest-containing > nearest-edge.")
    p("Distance metrics:")
    p("  - dist_edge_m (signed: + inside depth, - outside)")
    p("  - dist_center_m")
    p("  - equivalent_radius_m = sqrt(area_km2 * 1e6 / pi)")
    p("  - norm_dist_edge = dist_edge_m / equivalent_radius_m")
    p("  - norm_dist_center = dist_center_m / equivalent_radius_m")

    # 3. Eligibility
    sec("3. Polygon eligibility (of 2,561 pairs)")
    elig = pd.read_csv(INV / "polygon_eligibility.csv")
    R += table_rows(elig, num_cols={"n": 0, "pct_of_total": 1})

    # 4. TABLE 1 — Inside vs Outside with install + ANC touch rate + grand total
    sec("4. TABLE 1 — Inside vs Outside (of 2,499 pairs with polygon)")
    p("Install rate AND address_not_clear touch rate (pair ever touched ANC "
      "across calls, from reasons_union), with grand total row.")
    blank()
    t1 = pd.read_csv(INV / "table1_inside_outside_anc.csv")
    R += table_rows(t1, num_cols={"pairs":0, "installed":0, "anc_pairs":0,
                                   "install_rate_%":1, "anc_rate_%":1})
    blank()
    p("Outside pairs: LOWER install (38.6%) AND HIGHER ANC touch rate (48.2%). "
      "Both directions confirm polygon-outside = harder.")
    p("Within ANC-primary pairs specifically: inside 63.2% install vs outside "
      "43.8% (+19.4pp gap).")

    # 5. Inside vs Outside — reason mix
    sec("5. Inside vs outside — reason mix")
    rm = pd.read_csv(INV / "inside_vs_outside_by_reason.csv")
    rm.columns = [c if c else "primary_first" for c in rm.columns]
    R += table_rows(rm, num_cols={"inside_n": 0, "outside_n": 0,
                                    "inside_%": 1, "outside_%": 1})
    blank()
    p("Reason distribution is essentially stable inside vs outside "
      "(address_not_clear: 35.6% inside, 38.8% outside — 3pp shift). "
      "The polygon side does NOT change what partners talk about much — "
      "it changes whether the conversation converts to install.")

    # 5b. comm_quality_worst x address-family x polygon_side (MECE, sums to 2,499)
    sec("5b. comm_quality_worst × address-family × polygon_side")
    p("Each eligible pair (n=2,499) lands in exactly one of "
      "4 comm_quality × 2 address-family × 2 polygon_side = 16 cells. "
      "Address family = primary_first in {address_not_clear, address_too_far, "
      "address_wrong, building_access_issue, partner_reached_cant_find}.")
    blank()
    cq = pd.read_csv(INV / "comm_quality_address_by_polygon_side.csv")
    wide = cq[cq["view"] == "wide"].copy()
    cols = ["comm_quality_worst", "bucket",
            "inside_n", "inside_installed", "inside_install_rate_%",
            "outside_n", "outside_installed", "outside_install_rate_%",
            "gap_pp"]
    # Coerce int columns that pandas read as floats
    for c in ["inside_n","inside_installed","outside_n","outside_installed"]:
        wide[c] = wide[c].astype(int)
    wide = wide[cols]
    R += table_rows(wide, num_cols={
        "inside_n":0, "inside_installed":0,
        "outside_n":0, "outside_installed":0,
        "inside_install_rate_%":1, "outside_install_rate_%":1,
        "gap_pp":1,
    })
    blank()
    p("Row totals (sanity): "
      f"inside n = {int(wide['inside_n'].sum()):,}, "
      f"outside n = {int(wide['outside_n'].sum()):,}, "
      f"combined = {int(wide['inside_n'].sum()+wide['outside_n'].sum()):,} "
      "= 2,499 eligible pairs.")
    blank()
    p("Reads:")
    p("  1. INSIDE BEATS OUTSIDE IN EVERY CELL — gap is +10 to +25pp across "
      "all 8 (comm × bucket) rows. The polygon-side effect is stable ACROSS "
      "comm quality and ACROSS address vs non-address.")
    p("  2. Within each comm bucket, address-related pairs install BETTER "
      "than non-address-related ON BOTH SIDES of the polygon. Address "
      "friction is surmountable regardless of polygon side — it just "
      "resolves more often inside.")
    p("  3. Bottom-of-the-barrel cell: not_applicable × non_address_related "
      "× outside = 58 pairs, 20.7% install. Non-address terminal friction "
      "(cancellations, unreachable, wrong_customer) combined with "
      "outside-polygon is the worst cocktail.")
    p("  4. Top-of-the-barrel cells: clear × address_related × inside "
      "(68.1%, n=119) and not_applicable × address_related × inside "
      "(75.0%, small n=12). When the conversation was clean and the "
      "friction was address-family and the booking was inside the "
      "polygon — installs near-always happen.")
    p("  5. mutual_failure × address_related shows the largest reliable gap "
      "(n=387 inside vs n=124 outside, +21pp). Even when both parties "
      "struggled on address, being inside the polygon recovered 60% of "
      "those pairs vs only 40% outside.")
    blank()

    # --- Totals drill-down: how the 2,499 eligible pairs compose
    p("Totals drill-down — where the n's in the grid come from:")
    blank()
    p("  Polygon-eligible cohort: 2,499 pairs "
      "(= 2,561 parent cohort − 62 pairs whose partner has no polygon).")
    p("  Inside polygon: 1,939. Outside polygon: 560.")
    blank()
    p("  address_related total = 1,065 pairs, drilled down by primary_first:")
    recon = pd.read_csv(INV / "address_family_reconciliation.csv")
    R += table_rows(recon, num_cols={
        "parent_cohort_n": 0, "polygon_eligible_n": 0, "dropped_no_polygon": 0,
    })
    blank()
    p("  Note: headline 927 (parent analysis) = strictly "
      "primary_first = address_not_clear. The address-family bucket used "
      "in the 5b grid is a broader superset of 5 primary_first reasons "
      "(1,089 at parent, 1,065 polygon-eligible after dropping 24 pairs "
      "without polygons — 20 of those are ANC).")
    p("  non_address_related total = 1,434 pairs (= 2,499 − 1,065) — "
      "i.e. everything else (noise_or_empty, slot_confirmation, "
      "customer_postpone / cancelling / unreachable, wrong_customer, "
      "price_or_plan_query, duplicate, partner_postpone / no_show, "
      "install_site_technical, payment, competitor, router, other).")
    blank()

    # 6. address_not_clear pair install rate by side
    sec("6. address_not_clear pairs: install rate by side")
    R.append(["polygon_side","pairs","installed","install_rate_%"])
    R.append(["inside",   "690", "436", "63.2"])
    R.append(["outside",  "217",  "95", "43.8"])
    blank()
    p("Inside polygon, address friction is surmountable 63% of the time.")
    p("Outside polygon, only 44%. +19.4pp gap.")
    p("Address friction APPEARS at similar rate inside vs outside "
      "(35.6% vs 38.8%), but RESOLVES much better inside.")

    # 7. TABLE 2 — Inside pairs quintiles (q=5) — install + ANC touch + grand total
    sec("7. TABLE 2 — INSIDE pairs (n=1,939), quintiles (q=5)")
    p("Q1=shallow/near-center (depending on metric), Q5=deep/far.")
    p("Each quintile row: pairs, metric range, install_rate_%, anc_rate_% "
      "(ANC touch from reasons_union). Grand total at end of each metric.")
    quint = pd.read_csv(INV / "table2_inside_quintiles_anc.csv")
    for metric, label in [
        ("dist_edge_m",      "(2a) by dist_edge_m — raw meters; Q1=shallowest, Q5=deepest"),
        ("norm_dist_edge",   "(2b) by norm_dist_edge — scale-invariant; Q1=shallow, Q5=deep  [CLEANEST]"),
        ("dist_center_m",    "(2c) by dist_center_m — raw meters; Q1=near center, Q5=far"),
        ("norm_dist_center", "(2d) by norm_dist_center — inverse signal; Q1=near center, Q5=far"),
    ]:
        sub = quint[quint["metric"] == metric][[
            "q5","pairs","metric_min","metric_median","metric_max",
            "installed","install_rate_%","anc_pairs","anc_rate_%"]].copy()
        blank()
        R.append([f"-- {label} --"])
        R += table_rows(sub, num_cols={"pairs":0, "installed":0, "anc_pairs":0,
                                        "metric_min":2, "metric_median":2,
                                        "metric_max":2,
                                        "install_rate_%":1, "anc_rate_%":1})

    blank()
    p("Q1 -> Q5 gaps across the four metrics:")
    p("  dist_edge_m     : install 49.7 -> 60.6 (+10.9pp) | ANC 47.9 -> 43.8 (-4.1pp)")
    p("  norm_dist_edge  : install 49.2 -> 58.5 (+9.3pp)  | ANC 47.7 -> 39.4 (-8.3pp)  CLEANEST")
    p("  dist_center_m   : install 55.9 -> 51.0 (-4.9pp)  | ANC 40.5 -> 46.4 (+5.9pp, inverse)")
    p("  norm_dist_center: install 59.3 -> 48.5 (-10.8pp) | ANC 39.9 -> 47.9 (+8.0pp, inverse)")
    blank()
    p("Edge-distance and center-distance are INVERSE signals (deep inside ≈ "
      "close to center). Both point the same direction: depth inside proven "
      "territory = higher install + less address friction.")
    p("Normalized > raw (Q1->Q5 gaps 9-11pp vs 5-10pp). Varying polygon shapes "
      "need size-normalization.")
    p("ANC touch rate inside vs outside (44% vs 48%) is a small 4pp gap. "
      "Install-rate gap (16.7pp) is much bigger. Polygon's role is primarily "
      "whether friction RESOLVES, not whether it APPEARS.")

    # 8. Headline
    # 7b. Address-chain × polygon cross-cut (added 2026-04-20 afternoon)
    sec("7b. Address-chain × polygon cross-cut")
    p("Second-pass classifier (flag_address_chain.py) tags each call against "
      "the Delhi address-resolution hierarchy LANDMARK -> GALI -> FLOOR. "
      "addr_chain_stuck_at_mode = dominant stuck-point across the pair's calls "
      "(na if the pair wasn't address-talking, else which step broke).")
    blank()
    p("(a) Distribution of addr_chain_stuck_at_mode is stable inside vs outside. "
      "Chain engagement happens at SIMILAR rates regardless of polygon side "
      "(col % of 2,499 eligible pairs):")
    R.append(["addr_chain_stuck_at_mode","inside_%","outside_%","inside_n","outside_n"])
    R.append(["na",       "75.2%","73.6%","1,458","412"])
    R.append(["landmark","8.9%","10.5%","172","59"])
    R.append(["gali",     "8.7%","10.5%","168","59"])
    R.append(["none",     "5.3%","4.1%", "103","23"])
    R.append(["floor",    "2.0%","1.2%", "38", "7"])
    R.append(["TOTAL",    "100%","100%","1,939","560"])
    blank()
    p("Confirms polygon side doesn't change WHAT partners discuss (stable "
      "reason mix AND stable chain engagement).")
    blank()

    p("(b) Install rate by (addr_chain_stuck_at_mode × polygon_side):")
    R.append(["stuck_at_mode","inside_pairs","inside_install_%","outside_pairs","outside_install_%","gap_pp"])
    R.append(["na",       "1,458","52.6%","412","39.8%","+12.8"])
    R.append(["landmark", "172",  "62.2%","59", "42.4%","+19.8"])
    R.append(["gali",     "168",  "62.5%","59", "25.4%","+37.1"])
    R.append(["none",     "103",  "62.1%","23", "34.8%","+27.3"])
    R.append(["floor",    "38",   "76.3%","7",  "57.1%","+19.2"])
    blank()
    p("HEADLINE: gali-stuck × outside = 25.4% install. Gali-stuck × inside = "
      "62.5%. +37.1pp gap — the biggest single-cell gap anywhere in the "
      "analysis. Lane-level ambiguity combined with no partner-polygon-coverage "
      "is the worst possible combination.")
    p("Other takeaways: every stuck_at level shows a larger install gap by "
      "polygon side than the headline +16.7pp (which is the unconditioned "
      "average). The polygon effect compounds with chain-engagement difficulty.")
    blank()

    p("(c) any_chain_engaged × polygon_side:")
    R.append(["polygon_side","chain_engaged","pairs","install_rate_%"])
    R.append(["inside", "no",  "1,231","51.2%"])
    R.append(["inside", "yes", "708",  "62.4%"])
    R.append(["outside","no",  "359",  "37.6%"])
    R.append(["outside","yes", "201",  "40.3%"])
    blank()
    p("Chain engagement adds +11.2pp install INSIDE (62.4% vs 51.2%) but only "
      "+2.7pp OUTSIDE (40.3% vs 37.6%). The 'chain engagement is protective' "
      "finding from the parent analysis is ALMOST ENTIRELY an INSIDE-POLYGON "
      "phenomenon. Outside the polygon, engaging the chain barely helps — "
      "you can agree on every landmark/gali/floor and still not install.")
    blank()

    p("(d) Within primary_first=address_not_clear (907 eligible ANC pairs), "
      "install rate by stuck_at × side:")
    R.append(["stuck_at_mode","inside_pairs","inside_install_%","outside_pairs","outside_install_%","gap_pp"])
    R.append(["na",       "405","62.0%","124","51.6%","+10.4"])
    R.append(["landmark", "95", "68.4%","28", "50.0%","+18.4"])
    R.append(["gali",     "120","62.5%","47", "21.3%","+41.2"])
    R.append(["none",     "50", "64.0%","13", "38.5%","+25.5"])
    R.append(["floor",    "20", "65.0%","5",  "40.0%","+25.0"])
    blank()
    p("Gali-stuck × outside × ANC = 47 pairs, 21.3% install — sharpest 'bottom "
      "of the barrel' signature. +41.2pp gap within ANC for gali-stuck.")
    blank()

    # 8. Headline findings
    sec("8. Headline findings")
    p("1. 97.6% of pairs have polygon eligibility (2,499 / 2,561).")
    p("2. Inside-polygon pairs install at 55.3% vs outside at 38.6% — +16.7pp.")
    p("3. Within address_not_clear pairs, gap widens to +19.4pp (63% vs 44%).")
    p("4. Depth inside polygon differentiates further: shallow 44% -> deep 57% "
      "on normalized edge-distance.")
    p("5. Reason distribution barely shifts inside vs outside (~3pp on ANC). "
      "Polygon side does not change WHAT partners talk about; it changes "
      "whether the conversation RESOLVES to install.")

    # 9. Implication
    sec("9. Implications")
    p("Promise Maker: polygon-containment is a stronger serviceability signal "
      "than geometric nearest_distance. If a booking lands outside every "
      "partner's polygon, the promise is already on weaker ground. Consider "
      "soft-gating or penalty in Promise Maker upstream of Allocation.")
    p("Allocation: prefer partners whose polygon contains the booking (>=55% "
      "install baseline) over those whose polygon doesn't (<=39% baseline). "
      "Rank further by depth-inside, not just containment.")

    # 9b. Geoff + Donna critique summary
    sec("9b. Geoff + Donna critique — circularity softened, not dissolved")
    p("Both agents were briefed twice: once on the original framing, once")
    p("after the SE correction. Convergent conclusion:")
    blank()
    p("GEOFF (first-principles):")
    p("  - Before SE correction: 'install history predicts install history' —")
    p("    tautological.")
    p("  - After SE correction: 'Shifted from installs predict installs to")
    p("    install-RATE predicts install-RATE. Less circular, not acircular.")
    p("    The denominator (attempts) does the real disentanglement work.'")
    p("  - Decisive test: Mar-only holdout. If 16.7pp gap collapses -> memorization.")
    p("    If gap >= 10pp persists -> SE captures something temporally stable.")
    p("  - Additional: stratify Mar by whether partner had ANY Jan/Feb attempts")
    p("    in that hex. Pairs encountering a NEW hex in Mar = cleanest test.")
    p("  - Depth gradient (+9.3pp) is coherence signal with SE weighting, but")
    p("    still partly density-driven. Treat as suggestive.")
    blank()
    p("DONNA (systems):")
    p("  - Absorbing-crimson trap: SE decay is event-driven, not time-driven.")
    p("    Once crimson, Allocation stops sending leads -> no attempts ->")
    p("    no recovery. Classic success-to-the-successful ratchet.")
    p("  - Need gentle TIME-DECAY on hex confidence — hexes with no attempts")
    p("    in N days should regress toward prior.")
    p("  - Compound-signal problem: polygon conflates CAN (tacit knowledge)")
    p("    + WILL (motivation/viability). Gating destroys ability to diagnose")
    p("    which is failing. Need decline-reason logging at hex level.")
    p("  - ANC 4.3pp delta: real, small — true delta probably 3-6pp same")
    p("    direction. Not noise; weak confirmation pending more pairs.")
    p("  - Cleanest finding (per Donna): reason mix is STABLE inside vs outside")
    p("    (3pp shift). The polygon doesn't change WHAT partners talk about —")
    p("    it changes whether the conversation RESOLVES to install. Tacit-")
    p("    knowledge-density proxy, not customer-quality filter.")
    blank()
    p("CONVERGENT RECOMMENDATION:")
    p("  1. DO NOT use polygon as hard gate in Promise Maker.")
    p("  2. DO use as SOFT FEATURE in Allocation, DECOMPOSED:")
    p("     - hex-level SE (CAN proxy)")
    p("     - hex-level attempt recency (WILL proxy + anti-staleness)")
    p("     - Continuous score: hex_SE x recency_decay")
    p("  3. Reserve ~10% of lead volume for sub-threshold hexes adjacent to")
    p("     green — the exploration quota — to break the crimson ratchet.")
    p("  4. Balancing metric: decline rate in exploration-quota hexes over")
    p("     time. Falls -> CAN was issue, intervention works. Flat -> WILL")
    p("     was issue, gating wasn't the lever.")

    # 9c. Next-step tests queued
    sec("9c. Next-step tests queued (not yet executed)")
    R.append(["test","purpose","effort"])
    R.append(["T1: Mar-only inside/outside gap",
               "Temporal holdout — does 16.7pp gap survive?",
               "~30 min"])
    R.append(["T2: Stratify Mar by prior-hex-attempts",
               "Cleanest generalization test (Geoff)",
               "needs Jan-Feb attempt pull"])
    R.append(["T3: Install rate of 62 no-polygon pairs",
               "Cold-start canary — if ~38% polygon does work, if ~55% it's experience correlate",
               "~5 min"])
    R.append(["T4: Regress ANC on hex install-density",
               "Does depth gradient survive density controls? (Donna)",
               "~30 min"])

    # 10. Caveats
    sec("10. Caveats")
    p("Polygons are a Feb 2026 snapshot; cohort is Jan-Mar 2026. Mar pairs "
      "don't have their own installs reflected in the polygon.")
    p("62 pairs (2.4%) have partners without polygons — newer / low-volume "
      "partners below the p30 hex-density threshold.")
    p("2 pairs lack booking coords (serviceability CTE didn't resolve).")
    p("A partner's polygon is a union of DBSCAN clusters; we pick one per "
      "pair via deepest-containing > nearest-edge tie-break.")

    return R


def main():
    rows = build()
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow(r if r else [""])
    print(f"WROTE {OUT}  ({len(rows):,} rows)")


if __name__ == "__main__":
    main()
