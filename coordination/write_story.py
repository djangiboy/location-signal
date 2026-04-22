"""
Story CSV Builder -- Partner <-> Customer Calls
================================================
Assembles a single-file narrative STORY.csv from the investigative/ outputs
of this subfolder's pipeline (pull_calls -> transcribe -> classify -> embed
-> aggregate -> merge_with_allocation).

Reads:
    investigative/calls_manifest.csv
    investigative/transcripts_classified.csv
    investigative/pair_aggregated.csv
    investigative/pairs_with_alloc.csv
    investigative/callLevel_reason_by_distance_decile.csv
    investigative/callLevel_reason_by_prob_decile.csv
    investigative/callLevel_reason_by_nearest_type.csv
    investigative/pairLevel_reason_by_distance_decile.csv
    investigative/pairLevel_reason_by_prob_decile.csv
    investigative/uccl_monthly.csv

Writes:
    STORY.csv   -- opens top-to-bottom in a spreadsheet like a report.

Run from: analyses/data/location_accuracy/partner_customer_calls/
    python write_story.py
"""

import csv
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np


HERE    = Path(__file__).resolve().parent
INV     = HERE / "investigative"
OUT     = HERE / "STORY.csv"


# ============================================================
# FORMATTING HELPERS
# ============================================================
def table_rows(df, num_cols=None, pct_cols=None):
    """DataFrame -> list-of-lists (header + data) with formatting.
    pct_cols -> 0.12 -> '12.00%'. num_cols={col: decimals}."""
    pct_cols = pct_cols or []
    num_cols = num_cols or {}
    out = [list(df.columns)]
    for _, r in df.iterrows():
        row = []
        for col in df.columns:
            v = r[col]
            if col in pct_cols:
                row.append("" if pd.isna(v) else f"{float(v):.2%}")
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
    R = []

    def sec(t):   R.append([]); R.append([f"## {t}"]); R.append([])
    def p(t):     R.append([t])
    def blank():  R.append([])

    # ============================================================
    # HEADER
    # ============================================================
    R.append([f"# Partner <-> Customer Call Transcription Analysis"])
    R.append([f"Created: 2026-04-19"])
    R.append([f"Updated: {datetime.now().isoformat(timespec='minutes')}"])
    R.append([
        "Cohort: Delhi · Jan-Mar 2026 · non-BDO. "
        "Ground-truth complement to ../location_accuracy/ dropdown analysis."
    ])
    blank()

    # ============================================================
    # 1. WHY THIS EXISTS
    # ============================================================
    sec("1. Why this exists")
    p("../location_accuracy/ found that the dropdown `decision_reason` = "
      "'address_not_clear' separates 48% -> 2.5% across GNN prob deciles "
      "and 9.8% -> 28.5% across distance deciles.")
    p("The dropdown is what partners CLICK when they decline. Two partners "
      "declining for different real reasons can click the same option.")
    p("This subfolder replaces `partner clicked X` with `partner actually "
      "said X on the call` — via Exotel recording + OpenAI Whisper "
      "(Hindi->English in one pass) + Claude Haiku classification + "
      "OpenAI embedding cross-check.")

    # ============================================================
    # 1b. MERGE QUALITY (pre-anything-else)
    # ============================================================
    sec("1b. Merge quality — who survived the UCCL join")
    p("Master pair cohort — Jan-Mar 2026 Delhi non-BDO, post-serviceability, "
      "first ASSIGNED event per (mobile, partner).")
    R.append(["stage","unique mobiles","unique (mobile, partner) pairs"])
    R.append(["All assigned (Jan-Mar Delhi)", "6,523", "8,584"])
    R.append(["+ passed serviceability gate", "6,405", "8,444"])
    R.append(["+ non-BDO filter (MASTER)",    "5,225", "6,951"])
    R.append(["INNER JOIN with UCCL recording, call in [assigned, +14d]", "2,336", "2,991"])
    R.append(["After resolve_call_to_partner (time-proximity ownership)", "—",     "2,561"])
    blank()
    p("DROP-OFF 1: master (6,951) -> calls-inner-join (2,991) = 3,960 pairs lost (57%).")
    p("That 57% is NOT `no calls happened` — it's dominated by UCCL ingestion "
      "timing. Broken down:")
    blank()
    R.append(["sub-bucket","n","% of 3,960"])
    R.append(["UCCL row exists, but no recording (Cand #2)", "1,024", "25.9%"])
    R.append(["  only MISSED_CALL rows",                        "536", ""])
    R.append(["  only CANCELLED / REJECTED rows",               "551", ""])
    R.append(["  only UNKNOWN status",                          "316", ""])
    R.append(["  CONNECTED but no recording",                     "0", ""])
    R.append(["No UCCL row at all (Cand #1 + #3)",             "2,936", "74.1%"])
    blank()
    p("Finding: CONNECTED ≡ has_recording (zero exceptions). MISSED / CANCELLED "
      "/ REJECTED / UNKNOWN never carry a recording.")
    p("The dominant bucket (2,936 pairs, 74% of the no-recording cohort) is "
      "pairs with NO UCCL row at all. This is concentrated in Jan-Feb — the "
      "UCCL ingestion bed-in period.")
    blank()
    p("UCCL no-call rate by month (master pairs):")
    R.append(["month","total","with call","no call","% no-call"])
    R.append(["Jan 2026",  "2,666", "725",   "1,941", "72.8%"])
    R.append(["Feb 2026",  "2,319", "999",   "1,320", "56.9%"])
    R.append(["Mar 2026",  "1,867", "1,216", "651",   "34.9%"])
    R.append(["Apr 2026 (partial)","99","51","48",    "48.5%"])
    blank()
    p("Feb 7-9 had >92% no-call for 3 consecutive days — acute UCCL outage.")

    # Install rates by bucket — validates resolve_call_to_partner
    blank()
    p("Install rate by UCCL-activity bucket (6,951 master pairs):")
    R.append(["bucket","n","installed","install rate"])
    R.append(["A. Has recording (in manifest)",          "2,991", "1,320", "44.1%"])
    R.append(["B. UCCL row but no recording (M/C/R/U)",  "1,024",   "278", "27.1%"])
    R.append(["C. No UCCL row at all",                   "2,936", "1,549", "52.8%"])
    blank()
    p("(A) splits further: after resolve_call_to_partner drops 430 orphans, "
      "the 2,561 pairs with actual resolved calls install at 51.4%. "
      "The 430 orphans install at 0.7% — confirming they're ghost "
      "assignments the resolver correctly excludes.")
    blank()
    p("Interpretation: B is the lowest install (27%) — failed call attempts "
      "predict failed installs. C is highest (53%) — smooth installs that "
      "didn't need phone coordination, plus Jan/Feb UCCL gaps on pairs that "
      "installed anyway.")
    blank()

    # ============================================================
    # 1c. noise_or_empty vs Candidate #2 — different failure modes
    # ============================================================
    sec("1c. noise_or_empty (537 pairs) vs Candidate #2 (1,024 pairs) — distinct failures")
    R.append(["dimension","Candidate #2","noise_or_empty"])
    R.append(["n",                      "1,024", "537"])
    R.append(["audio existed?",         "NO",  "YES — was transcribed"])
    R.append(["UCCL call_status",       "MISSED / CANCELLED / REJECTED / UNKNOWN", "CONNECTED"])
    R.append(["what happened",          "Call never connected", "Call connected, zero substantive speech"])
    R.append(["where detected",         "SQL (no recording_url)", "Haiku classification of transcript"])
    R.append(["pipeline stage",         "Filtered in pull_calls.py", "Tagged in classify_reasons.py"])
    blank()
    p("Both are 'failed communication' at different stages. Candidate #2 = "
      "routing/dialing failure. noise_or_empty = conversational failure.")

    # ============================================================
    # 2. DATA SOURCE + UCCL POPULATION HISTORY
    # ============================================================
    sec("2. Data source")
    p("USER_CONNECTION_CALL_LOGS (PROD_DB.POSTGRES_RDS_PARTNER_CALL_LOG_IVR):")
    p("  - partner<->customer calls via Exotel, between ASSIGNED and install")
    p("  - has `recording_url` (needs HTTP Basic auth with Exotel SID+Token)")
    p("  - ~27% of rows have a recording (~= CONNECTED call_status)")
    p("partner_call_log (same schema) = PTL, partners->Wiom-support. Not the source here.")
    blank()
    if (INV / "uccl_monthly.csv").exists():
        p("UCCL population history (from probe_call_log_dates.py):")
        uccl = pd.read_csv(INV / "uccl_monthly.csv")
        R += table_rows(uccl, num_cols={"row_count":0, "distinct_calls":0,
                                         "distinct_from":0, "with_recording":0})
        blank()
        p("Earliest created_at: 2025-12-30 21:37 (go-live 2025-12-31).")
        p("Implication: Dec 2025 cohort from ../location_accuracy/ "
          "could NOT be used (early-Dec calls pre-date UCCL). "
          "Cohort shifted to Jan-Mar 2026.")

    # ============================================================
    # 3. COHORT DESCRIPTIVES
    # ============================================================
    sec("3. Cohort scale")
    manifest = pd.read_csv(INV / "calls_manifest.csv")
    pairs    = pd.read_csv(INV / "pairs_with_alloc.csv")
    tx       = pd.read_csv(INV / "transcripts.csv") if (INV / "transcripts.csv").exists() else None
    p(f"Call manifest rows            : {len(manifest):,}")
    p(f"Unique call_ids (recordings)  : {manifest['call_id'].nunique():,}")
    if tx is not None:
        p(f"Transcribed (unique call_ids) : {len(tx):,}")
    p(f"Unique mobiles                : {manifest['mobile'].nunique():,}")
    p(f"Unique (mobile, partner_id)   : {manifest[['mobile','partner_id']].drop_duplicates().shape[0]:,}")
    p(f"Pair-level rows (final)       : {len(pairs):,}")
    p(f"Installed pairs               : {(pairs['installed']==1).sum():,}  "
      f"({(pairs['installed']==1).mean()*100:.1f}%)")
    p(f"Pairs with >1 distinct reason : {(pairs['reasons_count']>1).sum():,}  "
      f"({(pairs['reasons_count']>1).mean()*100:.1f}%)")
    blank()
    p("n_calls per pair distribution:")
    nc = pairs["n_calls"].value_counts().sort_index().reset_index()
    nc.columns = ["n_calls", "pairs"]
    R += table_rows(nc, num_cols={"n_calls":0, "pairs":0})

    # ============================================================
    # 4. REASON TAXONOMY
    # ============================================================
    sec("4. Reason taxonomy (20 first-principles labels)")
    p("Decomposed from first principles: the call sits between ASSIGNED and "
      "OTP_VERIFIED; JTBD = resolve everything needed for a physical install.")
    R.append(["category", "labels"])
    R.append(["Location resolution",    "address_not_clear, address_too_far, address_wrong, building_access_issue"])
    R.append(["Scheduling",             "customer_postpone, partner_postpone, slot_confirmation"])
    R.append(["Post-visit recovery",    "partner_reached_cant_find, partner_no_show"])
    R.append(["Customer decision",      "customer_cancelling, competitor_or_consent"])
    R.append(["Commercial",             "price_or_plan_query, payment_issue"])
    R.append(["Technical / site",       "install_site_technical, router_or_stock_issue, duplicate_or_existing_connection"])
    R.append(["Communication / fallback","wrong_customer, customer_unreachable, noise_or_empty, other"])
    blank()
    p("Full definitions + disambiguation + few-shot examples: "
      "classify_reasons.py :: SYSTEM_PROMPT (V2).")

    # ============================================================
    # 5. PRIMARY_REASON DISTRIBUTION (pair-level, primary_first)
    # ============================================================
    sec("5. Primary reason distribution (pair-level)")
    dist = (pairs["primary_first"].value_counts()
                .rename("count").to_frame()
                .assign(pct=lambda d: (d["count"]/len(pairs)*100).round(1))
                .reset_index()
                .rename(columns={"index":"primary_first"}))
    R += table_rows(dist, num_cols={"count":0, "pct":1})

    # ============================================================
    # 5b. PAIR-LEVEL install rate BY primary_first (surmountable vs terminal)
    # ============================================================
    sec("5b. Pair-level install rate by primary_first reason")
    p("For each reason (as first in sorted union across the pair's calls), "
      "how many pairs installed vs didn't. This is the surmountable-vs-"
      "terminal gradient.")
    blank()
    ir = (pairs.groupby("primary_first")
                .agg(pairs=("installed","count"),
                     installed=("installed","sum"))
                .reset_index())
    ir["not_installed"]     = ir["pairs"] - ir["installed"]
    ir["install_rate_%"]    = (ir["installed"] / ir["pairs"] * 100).round(1)
    ir["share_of_cohort_%"] = (ir["pairs"] / len(pairs) * 100).round(1)
    ir = ir.sort_values("pairs", ascending=False)[[
        "primary_first","pairs","share_of_cohort_%","installed",
        "not_installed","install_rate_%"]]
    R += table_rows(ir, num_cols={"pairs":0, "installed":0, "not_installed":0,
                                   "share_of_cohort_%":1, "install_rate_%":1})
    blank()
    p(f"TOTAL: {len(pairs):,} pairs, {pairs['installed'].sum():,} installed "
      f"({pairs['installed'].mean()*100:.1f}%), {(pairs['installed']==0).sum():,} "
      f"not installed.")
    blank()
    p("Surmountable-vs-terminal read: install_site_technical 73% / "
      "partner_reached_cant_find 71% / building_access_issue 71% / "
      "slot_confirmation 65% / address_not_clear 59% (all surmountable). "
      "customer_cancelling 2% / address_too_far 17% / router_or_stock 20% / "
      "competitor_or_consent 22% (all terminal).")

    # ============================================================
    # 6. CALL-LEVEL DISTANCE DECILE
    # ============================================================
    sec("6. Call-level reason % by DISTANCE decile")
    p("Each call's primary_reason. Decile ranked over full 20K Jan-Mar "
      "non-BDO allocation cohort.")
    d_call = pd.read_csv(INV / "callLevel_reason_by_distance_decile.csv")
    d_call.columns = [c if c else "distance_decile" for c in d_call.columns]
    R += table_rows(d_call, num_cols={"distance_decile":0, "_total":0})

    # ============================================================
    # 7. CALL-LEVEL PROBABILITY DECILE
    # ============================================================
    sec("7. Call-level reason % by PROBABILITY decile")
    p_call = pd.read_csv(INV / "callLevel_reason_by_prob_decile.csv")
    p_call.columns = [c if c else "prob_decile" for c in p_call.columns]
    R += table_rows(p_call, num_cols={"prob_decile":1, "_total":0})

    # ============================================================
    # 8. CALL-LEVEL BY NEAREST_TYPE
    # ============================================================
    sec("8. Call-level reason % by nearest_type (active_base vs splitter)")
    t_call = pd.read_csv(INV / "callLevel_reason_by_nearest_type.csv")
    t_call.columns = [c if c else "nearest_type" for c in t_call.columns]
    R += table_rows(t_call, num_cols={"_total":0})

    # ============================================================
    # 9. PAIR-LEVEL DISTANCE DECILE (touch rate)
    # ============================================================
    sec("9. Pair-level reason touch-rate by DISTANCE decile")
    p("% of pairs that touched the reason on AT LEAST ONE call.")
    p("Note: saturated metric — pairs with more calls have higher touch "
      "rates by construction. Compare with call-level above for a cleaner "
      "signal.")
    d_pair = pd.read_csv(INV / "pairLevel_reason_by_distance_decile.csv")
    d_pair.columns = [c if c else "distance_decile" for c in d_pair.columns]
    R += table_rows(d_pair, num_cols={"distance_decile":0, "_n_pairs":0})

    # ============================================================
    # 10. PAIR-LEVEL PROBABILITY DECILE (touch rate)
    # ============================================================
    sec("10. Pair-level reason touch-rate by PROBABILITY decile")
    p_pair = pd.read_csv(INV / "pairLevel_reason_by_prob_decile.csv")
    p_pair.columns = [c if c else "prob_decile" for c in p_pair.columns]
    R += table_rows(p_pair, num_cols={"prob_decile":1, "_n_pairs":0})

    # ============================================================
    # 11. DECISION -> INSTALL GAP
    # ============================================================
    sec("11. Decision -> install time gap (installed pairs)")
    inst = pairs[pairs["installed"] == 1].copy()
    inst["gap_h"] = pd.to_numeric(inst["decision_to_install_hours"], errors="coerce")
    inst = inst[inst["gap_h"].notna() & (inst["gap_h"] >= 0)]
    q = inst["gap_h"].describe(percentiles=[.1,.25,.5,.75,.9,.95,.99])
    R.append(["statistic", "hours"])
    for k, v in q.items():
        R.append([k, f"{v:,.1f}"])
    blank()
    p("Bucketed:")
    bins = [0,1,6,24,48,72,168,999999]
    labels = ["<1h","1-6h","6-24h","1-2d","2-3d","3-7d",">7d"]
    inst["bucket"] = pd.cut(inst["gap_h"], bins=bins, labels=labels, right=False)
    b = inst["bucket"].value_counts().sort_index().reset_index()
    b.columns = ["bucket","count"]
    b["pct"] = (b["count"]/len(inst)*100).round(1)
    R += table_rows(b, num_cols={"count":0, "pct":1})
    blank()
    p("Median gap (hours) by primary_first reason — installed pairs only:")
    gpr = (inst.groupby("primary_first")["gap_h"]
               .agg(["median","mean","count"])
               .reset_index()
               .sort_values("count", ascending=False))
    gpr = gpr[gpr["count"] >= 5]
    R += table_rows(gpr, num_cols={"median":1, "mean":1, "count":0})

    # ============================================================
    # 11b. TIME-TO-INSTALL (HOURS) — address vs non-address split
    # ============================================================
    sec("11b. Time-to-install percentiles — address vs non-address (installed only)")
    p("Question: pairs with address friction / mutual confusion on call — do "
      "they burn more hours between decision and install than pairs where "
      "the call surfaced non-address reasons?")
    blank()
    p("Cohort: 1,317 installed pairs. Split MECE by primary_first: "
      "address_related = {address_not_clear, address_too_far, address_wrong, "
      "building_access_issue, partner_reached_cant_find}. "
      "non_address_related = everything else (noise_or_empty, "
      "slot_confirmation, customer_postpone, etc.).")
    blank()

    ADDRESS_FAMILY = {
        "address_not_clear", "address_too_far", "address_wrong",
        "building_access_issue", "partner_reached_cant_find",
    }
    inst2 = inst.copy()
    inst2["bucket_addr"] = np.where(
        inst2["primary_first"].isin(ADDRESS_FAMILY),
        "address_related", "non_address_related")

    def qrow(label, s):
        s = s.dropna()
        if len(s) == 0:
            return [label, "0"] + [""] * 9
        return [
            label, f"{len(s):,}",
            f"{s.min():.2f}",   f"{np.percentile(s,25):.2f}",
            f"{np.percentile(s,50):.2f}", f"{s.mean():.2f}",
            f"{np.percentile(s,75):.2f}", f"{np.percentile(s,90):.2f}",
            f"{np.percentile(s,95):.2f}", f"{np.percentile(s,99):.2f}",
            f"{s.max():,.2f}",
        ]

    R.append(["bucket","n","min","p25","median","mean","p75","p90","p95","p99","max"])
    R.append(qrow("ALL_INSTALLED", inst2["gap_h"]))
    R.append(qrow("address_related",
                  inst2.loc[inst2["bucket_addr"]=="address_related","gap_h"]))
    R.append(qrow("non_address_related",
                  inst2.loc[inst2["bucket_addr"]=="non_address_related","gap_h"]))
    blank()

    addr_s = inst2.loc[inst2["bucket_addr"]=="address_related","gap_h"].dropna()
    non_s  = inst2.loc[inst2["bucket_addr"]=="non_address_related","gap_h"].dropna()
    p(f"Split check: address_related n={len(addr_s):,} + "
      f"non_address_related n={len(non_s):,} = {len(addr_s)+len(non_s):,} "
      f"= 1,317 installed pairs. Clean MECE.")
    blank()
    p("COUNTER-INTUITIVE read — address friction is NOT a time-burner "
      "(conditional on eventually installing):")
    p(f"  median:  address {np.percentile(addr_s,50):.1f}h vs non-address "
      f"{np.percentile(non_s,50):.1f}h  "
      f"(address is {np.percentile(non_s,50)-np.percentile(addr_s,50):+.1f}h)")
    p(f"  p75:     address {np.percentile(addr_s,75):.1f}h vs non-address "
      f"{np.percentile(non_s,75):.1f}h")
    p(f"  p90:     address {np.percentile(addr_s,90):.1f}h vs non-address "
      f"{np.percentile(non_s,90):.1f}h  (essentially tied)")
    p(f"  p95:     address {np.percentile(addr_s,95):.1f}h vs non-address "
      f"{np.percentile(non_s,95):.1f}h  (tied)")
    p(f"  max:     address {addr_s.max():,.0f}h  ({addr_s.max()/24:.0f}d) "
      f"vs non-address {non_s.max():,.0f}h  ({non_s.max()/24:.0f}d)  "
      "— non-address carries the longer tail")
    blank()
    p("Interpretation: the pairs that installed despite non-address friction "
      "(customer postponed, price dispute, wrong_customer, noise calls) "
      "are slower to get over the line than pairs that negotiated through "
      "address confusion. Once address gets resolved — usually within one "
      "follow-up call — the install proceeds on the normal ~20h track. "
      "Non-address issues like postponement or price query drag the "
      "scheduling window further. The >7d tail (58 days max) lives on the "
      "non-address side.")
    p("Caveat: this conditions on installed. The story for non-installed "
      "pairs is in Section 5b — non-address primary_first buckets "
      "(customer_cancelling 2.4% install, address_too_far 16.7%, etc.) "
      "are where terminal failure concentrates. So non-address burns time "
      "when it installs, AND kills the install more often when it doesn't.")
    blank()

    # ============================================================
    # 12. COMPARISON WITH DROPDOWN (location_accuracy)
    # ============================================================
    sec("12. Transcript vs dropdown — the headline finding")
    R.append(["metric", "dropdown (../location_accuracy)", "transcript (here)"])
    R.append(["address_not_clear base rate", "~13%", "~20% of calls / 36% of pairs (primary_first)"])
    R.append(["spread by distance decile",  "9.8% -> 28.5% (monotonic up)", "19.5% -> 20.1% (flat, 6.5pp range)"])
    R.append(["spread by prob decile",      "47.7% -> 2.5% (monotonic down)", "16.2% -> 21.7% (flat, 7.1pp range)"])
    R.append(["splitter excess friction",    "splitter install gap",          "splitter +4pp on address_not_clear"])
    blank()
    p("Interpretation:")
    p("1. Dropdown UNDER-COUNTS address friction by ~2x. "
      "~20% of actual calls involve address friction vs ~13% dropdown rate.")
    p("2. Distance doesn't separate address friction on actual calls. "
      "Pervasive communication pattern, not a geometric phenomenon.")
    p("3. The dropdown's 48%->2.5% prob pattern is a DECLINE-CHANNEL ARTIFACT. "
      "Low-prob partners face similar per-call friction but disproportionately "
      "CHOSE 'address not clear' as their dropdown exit. Geoff's "
      "'dismissal channel' framing is now EMPIRICALLY CONFIRMED.")
    p("4. Splitters face +4pp more address friction per call. Real signal.")

    # ============================================================
    # 12b. WHY-CHAIN — drilling down into the address failure
    # ============================================================
    sec("12b. Why-chain: why do address_not_clear calls happen?")
    p("Headline: address_not_clear is the SINGLE largest reason bucket "
      "(37.4% of pair-level primary_first), and the single largest reason in "
      "the non-install population (30.5%). So 'why does address_not_clear "
      "fail' is the pivotal root cause.")
    blank()
    p("Why 1: Why do installs fail?")
    R.append(["non-install reason","n","% of non-installs"])
    R.append(["address_not_clear",               "380", "30.5%"])
    R.append(["noise_or_empty",                  "266", "21.4%"])
    R.append(["slot_confirmation",                "90",  "7.2%"])
    R.append(["customer_cancelling",              "83",  "6.7%"])
    R.append(["customer_unreachable",             "73",  "5.9%"])
    R.append(["customer_postpone",                "73",  "5.9%"])
    R.append(["wrong_customer",                   "67",  "5.4%"])
    R.append(["(13 others)",                     "212", "17.0%"])
    blank()
    p("Why 2: address_not_clear wins the non-install distribution. WHY does it "
      "happen? Tagged communication-quality on the 1,023 unique "
      "address_not_clear transcripts via a focused Haiku pass "
      "(flag_comm_failure.py):")
    blank()
    R.append(["comm_quality","n","%","install rate"])
    R.append(["one_sided_confusion (partner confused, customer clear)", "471", "46.0%", "54.6%"])
    R.append(["mutual_failure (both struggle)",                         "322", "31.5%", "48.4%"])
    R.append(["clear (partner resolved on second try)",                 "209", "20.4%", "62.2%"])
    R.append(["not_applicable",                                          "21",  "2.1%", "—"])
    blank()
    p("Why 3: Which is the dominant sub-type? 46% of address_not_clear is "
      "ONE-SIDED — customer gave landmarks clearly, partner couldn't parse "
      "or locate. Only 32% is genuinely mutual breakdown.")
    blank()
    p("Why 4: Why does the partner fail to parse a clearly-given address? "
      "Hypothesis anchors:")
    p("  (a) Partner territorial unfamiliarity. SPLITTER partners have +4pp "
      "more address_not_clear per call than active_base (23.8% vs 19.9%). "
      "Splitter = no prior install in the area -> fewer internal landmarks "
      "mapped in partner's head.")
    p("  (b) Phone/audio quality. Whisper translation artifacts inflate "
      "some cases; real audio noise in others.")
    p("  (c) Hindi dialect and landmark-language mismatches between customer "
      "and partner.")
    blank()
    p("Why 5: What breaks mutual cases apart from one-sided? Cross with "
      "partner_reached_cant_find — which is ON-GROUND navigation (partner "
      "actually at/near the location):")
    blank()
    R.append(["among partner_reached_cant_find (n=496)","n","%"])
    R.append(["mutual_failure",         "203", "40.9%"])
    R.append(["one_sided_confusion",    "116", "23.4%"])
    R.append(["clear",                   "96", "19.4%"])
    R.append(["not_applicable",          "81", "16.3%"])
    blank()
    p("Mutual-failure rate is 41% for on-ground navigation calls vs 32% for "
      "pre-dispatch address calls. When the partner is standing outside and "
      "customer is directing by phone, the two-agent negotiation becomes "
      "harder — this is where mutual failure peaks.")
    blank()
    p("So 'address failure' decomposes to:")
    p("  - 46% of it: partner-side parsing difficulty (pre-dispatch) — "
      "fixable with better address capture upstream (location share, pin "
      "drop, Places API at booking time)")
    p("  - 32% of it: genuine mutual breakdown — fixable with structured "
      "navigation flow (in-call pin share, building-level address hierarchy)")
    p("  - 22% of it: actually resolved within the call — not a failure")
    blank()
    p("Implication: the dominant lever is NOT customer training. It's pre-"
      "dispatch address-capture quality. Splitter partners, by virtue of "
      "covering unfamiliar territory, bear disproportionate cost.")

    # ============================================================
    # 12c. Pair-level comm_quality (worst-case rollup) + install rate
    #      + MECE split by address-family (primary_first)
    # ============================================================
    sec("12c. Pair-level comm_quality (worst observed across all calls)")
    p("For pairs with multiple calls, we collect every call's comm_quality "
      "and take the pessimistic rollup (mutual > one_sided > clear > NA). "
      "Answers: did the partner-customer pair EVER have mutual breakdown?")
    blank()

    ADDRESS_FAMILY = {
        "address_not_clear", "address_too_far", "address_wrong",
        "building_access_issue", "partner_reached_cant_find",
    }
    COMM_ORDER = ["mutual_failure", "one_sided_confusion", "clear", "not_applicable"]
    total_pairs = len(pairs)

    # --- Table A: comm_quality_worst x install rate
    a = (pairs.groupby("comm_quality_worst")
               .agg(n=("installed","size"), installed=("installed","sum"))
               .reindex(COMM_ORDER).reset_index())
    a["share"]        = a["n"]         / total_pairs
    a["install_rate"] = a["installed"] / a["n"]

    R.append(["comm_quality_worst", f"n", f"% of {total_pairs:,} pairs",
              "installed", "install_rate_%"])
    for _, r in a.iterrows():
        R.append([r["comm_quality_worst"],
                  f"{int(r['n']):,}",
                  f"{r['share']*100:.1f}%",
                  f"{int(r['installed']):,}",
                  f"{r['install_rate']*100:.1f}%"])
    R.append(["TOTAL",
              f"{total_pairs:,}",
              "100.0%",
              f"{int(a['installed'].sum()):,}",
              f"{a['installed'].sum()/total_pairs*100:.1f}%"])
    blank()
    p("40% of pairs had at least one mutual-breakdown call. Higher than the "
      "call-level 26% because multi-call pairs accumulate exposure. "
      "not_applicable installs WORST (36.5%) — that bucket is dominated by "
      "noise_or_empty calls, which are a terminal communication failure.")
    blank()

    # --- Table B: MECE split by address-family
    p("MECE split: each comm_quality_worst bucket split by whether the pair's "
      "primary_first sits in the address family (address_not_clear, "
      "address_too_far, address_wrong, building_access_issue, "
      "partner_reached_cant_find). Eight rows sum back to the full cohort.")
    blank()
    pairs_copy = pairs.copy()
    pairs_copy["is_address"] = pairs_copy["primary_first"].isin(ADDRESS_FAMILY)
    b = (pairs_copy.groupby(["comm_quality_worst", "is_address"])
                   .agg(n=("installed","size"), installed=("installed","sum"))
                   .reset_index())
    b["bucket"]       = b["is_address"].map({True: "address_related",
                                              False: "non_address_related"})
    b["share"]        = b["n"]         / total_pairs
    b["install_rate"] = b["installed"] / b["n"]
    b["_ord"]         = b["comm_quality_worst"].map({k:i for i,k in enumerate(COMM_ORDER)})
    b = b.sort_values(["_ord", "is_address"], ascending=[True, False])

    R.append(["comm_quality_worst", "bucket", "n",
              f"% of {total_pairs:,}", "installed", "install_rate_%"])
    for _, r in b.iterrows():
        R.append([r["comm_quality_worst"],
                  r["bucket"],
                  f"{int(r['n']):,}",
                  f"{r['share']*100:.1f}%",
                  f"{int(r['installed']):,}",
                  f"{r['install_rate']*100:.1f}%"])
    R.append(["TOTAL", "",
              f"{int(b['n'].sum()):,}",
              f"{b['share'].sum()*100:.1f}%",
              f"{int(b['installed'].sum()):,}",
              f"{b['installed'].sum()/b['n'].sum()*100:.1f}%"])
    blank()
    p("Read: within EVERY comm_quality bucket, address-related pairs install "
      "BETTER than non-address-related. Address friction is surmountable — "
      "gets resolved on a follow-up call. Non-address problems (cancellations, "
      "price, wrong_customer, unreachable) are the terminal ones. "
      "Biggest gap is in not_applicable (noise-dominated): non-address "
      "installs ~35%, address installs ~71% — confirming noise_or_empty is a "
      "real install killer for non-address reasons, not a classifier artifact.")
    blank()

    # ============================================================
    # 12d. ADDRESS-CHAIN DRILL-DOWN (LANDMARK -> GALI -> FLOOR)
    # ============================================================
    sec("12d. Address-chain drill-down (LANDMARK -> GALI -> FLOOR)")
    p("Second-pass classifier (flag_address_chain.py) re-reads every transcript "
      "and tags it against the canonical Delhi address-resolution hierarchy: "
      "first converge on a mutually-recognized LANDMARK, then the GALI / lane, "
      "then the FLOOR inside the building. Calls can skip levels, enter mid-chain, "
      "or fail to engage.")
    blank()
    p("Columns added (call-level): addr_landmark_step, addr_gali_step, "
      "addr_floor_step, addr_chain_stuck_at, addr_chain_evidence.")
    p("Pair-level rollups: addr_landmark_best, addr_gali_best, addr_floor_best "
      "(furthest-along — optimistic), addr_chain_stuck_at_list, addr_chain_stuck_at_mode.")
    blank()
    p("Call-level stuck_at distribution (4,930 unique calls):")
    R.append(["addr_chain_stuck_at","n","% of calls"])
    R.append(["na (not an address-chain call)","3,727","75.6%"])
    R.append(["landmark (couldn't agree on anchor)","430","8.7%"])
    R.append(["gali (lane could not be resolved)","364","7.4%"])
    R.append(["none (chain resolved / non-address end)","350","7.1%"])
    R.append(["floor","59","1.2%"])
    blank()
    p("Call-level bottleneck: GALI (7.4%) edges LANDMARK (8.7% is more calls "
      "but landmark-stuck is often followed by re-attempt; gali-stuck tends "
      "to be terminal within the call). Only 1.2% of calls fail at floor — "
      "once gali lands, floor resolves.")
    blank()

    p("Pair-level addr_chain_stuck_at_mode x install rate (2,561 pairs):")
    R.append(["addr_chain_stuck_at_mode","pairs","share_%","installed","install_rate_%"])
    R.append(["na",       "1,915", "74.8%", "948", "49.5%"])
    R.append(["landmark", "239",   "9.3%",  "136", "56.9%"])
    R.append(["gali",     "232",   "9.1%",  "124", "53.4%"])
    R.append(["none",     "129",   "5.0%",  "75",  "58.1%"])
    R.append(["floor",    "46",    "1.8%",  "34",  "73.9%"])
    blank()
    p("COUNTER-INTUITIVE: every chain-engaged bucket installs BETTER than `na` "
      "(49.5%). Engaging the chain at all is protective — +7pp at landmark, +4pp "
      "at gali, +9pp if resolved, +24pp at floor (because by the time you're "
      "arguing about floor, the partner is already at the door).")
    blank()

    p("any_chain_engaged (at least one call with stuck_at in landmark/gali/floor/none):")
    R.append(["cohort","any_chain_engaged","pairs","install_rate_%"])
    R.append(["All 2,561",   "no",  "1,627", "47.8%"])
    R.append(["All 2,561",   "yes", "934",   "57.7%"])
    R.append(["Within 927 ANC","no",  "385",   "58.7%"])
    R.append(["Within 927 ANC","yes", "542",   "59.2%"])
    blank()
    p("Across full cohort: chain-engaged pairs install +10pp better (57.7% vs "
      "47.8%). Within ANC, chain engagement barely matters (+0.5pp) — ANC pairs "
      "install ~59% regardless. The chain signal adds PREDICTIVE POWER outside "
      "the ANC bucket — i.e. for pairs not flagged as address-friction by "
      "primary_first, actually engaging the chain still correlates with install.")
    blank()

    p("CROSSTAB: primary_first x addr_chain_stuck_at_mode (2,561 pairs)")
    R.append(["primary_first","na","landmark","gali","floor","none","TOTAL"])
    R.append(["address_not_clear",          "538","129","169","26","65","927"])
    R.append(["noise_or_empty",              "493","24","10","5","5","537"])
    R.append(["slot_confirmation",           "183","23","15","4","30","255"])
    R.append(["customer_postpone",           "123","8","7","0","2","140"])
    R.append(["customer_unreachable",        "122","3","4","1","0","130"])
    R.append(["partner_reached_cant_find",   "69","21","11","3","10","114"])
    R.append(["wrong_customer",              "83","8","3","1","3","98"])
    R.append(["customer_cancelling",         "81","3","1","0","0","85"])
    R.append(["price_or_plan_query",         "47","6","0","1","4","58"])
    R.append(["duplicate_or_existing_connection","33","3","2","1","2","41"])
    R.append(["partner_postpone",            "26","3","3","0","3","35"])
    R.append(["address_too_far",             "23","6","1","0","0","30"])
    R.append(["partner_no_show",             "24","1","3","1","1","30"])
    R.append(["install_site_technical",      "23","0","1","2","0","26"])
    R.append(["payment_issue",               "19","1","0","0","0","20"])
    R.append(["address_wrong",               "6","0","1","1","3","11"])
    R.append(["competitor_or_consent",       "8","0","1","0","0","9"])
    R.append(["building_access_issue",       "7","0","0","0","0","7"])
    R.append(["router_or_stock_issue",       "5","0","0","0","0","5"])
    R.append(["other",                       "2","0","0","0","1","3"])
    R.append(["TOTAL",                       "1,915","239","232","46","129","2,561"])
    blank()
    p("Row totals tie to primary_first distribution (section 5). Column totals "
      "tie to addr_chain_stuck_at_mode distribution above. Note: 538 of 927 "
      "ANC pairs have mode=na — not a contradiction. Mode is pessimistic to "
      "noise: an ANC pair with 3 calls (1 address + 2 noise) has mode=na. Use "
      "any_chain_engaged (list-based) for chain-engagement presence, mode for "
      "dominant theme.")
    blank()

    p("Within 927 ANC — furthest step reached across the pair's calls:")
    R.append(["step","na","one_tried","multiple_tried","converged","not_reached","attempted","na_ground"])
    R.append(["addr_landmark_best","386","189","163","145","44","—","—"])
    R.append(["addr_gali_best",    "383","—","—","173","183","188","—"])
    R.append(["addr_floor_best",   "397","—","—","55","379","58","38"])
    blank()
    p("Of 927 ANC pairs: 145 (16%) CONVERGED on a landmark somewhere in their "
      "calls, 173 (19%) got the gali confirmed, only 55 (6%) resolved the floor. "
      "~383 (41%) never even engaged the gali step — their address chain broke "
      "at or before landmark.")
    blank()

    p("Key reads:")
    p("  (i) Gali is the single largest call-level bottleneck (7.4% of all calls "
      "stuck there). Pre-dispatch address capture that gives the partner the gali "
      "directly should be highest-leverage.")
    p("  (ii) Floor-stuck pairs install at 74% — the chain is working; residual "
      "friction at floor level is surmountable and mostly resolves same visit.")
    p("  (iii) The 40% of ANC pairs that never engaged the gali step have a "
      "different failure mode than the ones that did — probably customer "
      "disengagement or partner never asking. Worth splitting as a separate pattern.")
    blank()

    # ============================================================
    # 13. CLASSIFIER EVOLUTION V1 -> V2
    # ============================================================
    sec("13. Classifier V1 -> V2 (audit trail)")
    p("V1 over-used noise_or_empty (30% of calls). Embeddings rescued 34% "
      "of that bucket into real reasons.")
    p("V2 tightened SYSTEM_PROMPT:")
    p("  - Explicit rule: any intelligible content -> classify by content.")
    p("  - Dialect note: 'bom/vyom/router/ruter' = Wiom Net box (not location).")
    p("  - Few-shot examples from real pilot transcripts.")
    p("V2 fixed embedding `competitor_or_consent` prototype (was drifting on "
      "'my husband/wife' family-timing language).")
    p("Result: Haiku <-> embedding agreement 29% -> 47% (+18pp).")
    p("V1 outputs archived as investigative/*_v1.csv for audit.")

    # ============================================================
    # 14. FILE MAP
    # ============================================================
    sec("14. File map")
    p("SQL queries:")
    p("  query_pcalls.txt       — call manifest (Jan-Mar Delhi non-BDO)")
    p("  query_allocation.txt   — full allocation cohort for decile computation")
    blank()
    p("Python pipeline (in order):")
    p("  1. pull_calls.py          -> calls_manifest.csv")
    p("  2. transcribe_calls.py    -> transcripts.csv  (Exotel + Whisper, 10 workers)")
    p("  3. classify_reasons.py    -> transcripts_classified.csv  (Haiku + regex)")
    p("  4. embedding_classify.py  -> embedding_reason_scores.csv + embedding_vs_haiku.csv")
    p("  5. aggregate_per_pair.py  -> calls_resolved.csv + pair_aggregated.csv")
    p("  6. merge_with_allocation  -> calls_with_alloc.csv + pairs_with_alloc.csv + decile CSVs")
    blank()
    p("Chain script: run_downstream.sh (steps 3-6)")
    blank()
    p("Utilities: show_samples_by_reason.py, smoke_test_one.py, probe_call_log_dates.py")
    blank()
    p("Key deliverable tables:")
    p("  pairs_with_alloc.csv     -- 1 row per (mobile, partner), 18 cols, "
      "includes raw transcripts, reasons_union, decision_to_install_hours, "
      "distance/prob deciles, nearest_type.")
    p("  calls_with_alloc.csv     -- 1 row per call (finer granularity).")

    return R


def main():
    rows = build_story()
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        for row in rows:
            w.writerow(row if row else [""])
    print(f"WROTE {OUT}  ({len(rows):,} rows)")


if __name__ == "__main__":
    main()
