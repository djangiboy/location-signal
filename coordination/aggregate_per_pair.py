"""
Aggregate per (mobile, partner_id) from call-level classifications
===================================================================
Same (mobile, partner_id) often has 2–3 calls. A call can show one reason on
the first attempt (address_not_clear) and a different reason on the second
(slot_confirmation or customer_postpone). We capture ALL reasons that appeared.

Also resolves the ambiguity introduced by the SQL join: when one customer was
assigned to multiple partners, a call appears once per partner in the manifest.
The ACTUAL partner on the call is the one with the most-recent assigned_time
BEFORE the call_time. We pick that row.

Input:
    investigative/calls_manifest.csv           (raw join)
    investigative/transcripts_classified.csv   (one row per call_id)

Output:
    investigative/calls_resolved.csv           one row per call_id, correct
                                                (mobile, partner_id) assigned
    investigative/pair_aggregated.csv          one row per (mobile, partner_id):
                                                n_calls, reasons_set, summary_concat
"""

from pathlib import Path
import pandas as pd
import numpy as np


HERE    = Path(__file__).resolve().parent
OUT_DIR = HERE / "investigative"

MANIFEST  = OUT_DIR / "calls_manifest.csv"
CLASS_CSV = OUT_DIR / "transcripts_classified.csv"
RESOLVED  = OUT_DIR / "calls_resolved.csv"
PAIR_CSV  = OUT_DIR / "pair_aggregated.csv"


def resolve_call_to_partner(manifest):
    """For each call_id, keep the (mobile, partner_id) row whose assigned_time
    is most recent BEFORE call_time (non-negative time_since_assigned, minimized)."""
    df = manifest.copy()
    df["call_time"]     = pd.to_datetime(df["call_time"])
    df["assigned_time"] = pd.to_datetime(df["assigned_time"])
    df["delta_sec"]     = (df["call_time"] - df["assigned_time"]).dt.total_seconds()

    # Keep rows with non-negative delta (call after assignment).
    df = df[df["delta_sec"] >= 0].copy()
    # Pick the row with the smallest delta per call_id.
    df = df.sort_values(["call_id", "delta_sec"]).groupby("call_id", as_index=False).head(1)
    return df.reset_index(drop=True)


def main():
    assert MANIFEST.exists() and CLASS_CSV.exists()

    m  = pd.read_csv(MANIFEST)
    cl = pd.read_csv(CLASS_CSV)

    print(f"manifest rows         : {len(m):,}")
    print(f"manifest unique calls : {m['call_id'].nunique():,}")
    print(f"classified rows       : {len(cl):,}")

    resolved = resolve_call_to_partner(m)
    print(f"\nRESOLVED — one row per call_id: {len(resolved):,}")

    # Merge resolved manifest with classifications
    cl["call_id"] = cl["call_id"].astype(str)
    resolved["call_id"] = resolved["call_id"].astype(str)
    cl_cols = ["call_id", "transcript", "lang", "primary_reason",
               "secondary_reason", "llm_summary"]
    if "comm_quality" in cl.columns:
        cl_cols += ["comm_quality"]
    if "comm_failure_evidence" in cl.columns:
        cl_cols += ["comm_failure_evidence"]
    for c in ["addr_landmark_step", "addr_gali_step", "addr_floor_step",
              "addr_chain_stuck_at", "addr_chain_evidence"]:
        if c in cl.columns:
            cl_cols += [c]
    merged = resolved.merge(cl[cl_cols], on="call_id", how="inner")
    print(f"AFTER MERGE with transcripts: {len(merged):,}")
    merged.to_csv(RESOLVED, index=False)
    print(f"WROTE {RESOLVED}")

    # ---- Pair-level aggregation ----
    merged["secondary_reason"] = merged["secondary_reason"].fillna("")
    merged["llm_summary"]      = merged["llm_summary"].fillna("")

    # Severity ranking for pair-level comm_quality rollup
    COMM_RANK = {"mutual_failure":3, "one_sided_confusion":2, "clear":1, "not_applicable":0}
    COMM_RANK_INV = {v:k for k,v in COMM_RANK.items()}

    # Progress rankings — higher = further along the address-resolution chain.
    # For pair-level we roll up the BEST outcome reached across calls.
    LANDMARK_RANK = {"na":-1, "none":0, "one_tried":1, "multiple_tried":2, "converged":3}
    GALI_RANK     = {"na":-1, "not_reached":0, "attempted":1, "converged":2}
    FLOOR_RANK    = {"na":-1, "not_reached":0, "attempted":1, "na_ground":2, "converged":3}
    LANDMARK_INV  = {v:k for k,v in LANDMARK_RANK.items()}
    GALI_INV      = {v:k for k,v in GALI_RANK.items()}
    FLOOR_INV     = {v:k for k,v in FLOOR_RANK.items()}

    def agg(g):
        primary = list(sorted(set(g["primary_reason"].dropna())))
        sec     = [r for r in sorted(set(g["secondary_reason"])) if r]
        reasons = sorted(set(primary + sec))
        summaries = " | ".join(g["llm_summary"].astype(str).tolist())
        # Raw transcripts per call, concatenated. " ||| " as a visible separator
        # so a later split() recovers individual calls.
        transcripts = " ||| ".join(g["transcript"].astype(str).tolist())

        # Comm quality rollup — available when upstream flag_comm_failure.py has run
        if "comm_quality" in g.columns:
            qs = g["comm_quality"].dropna().tolist()
            comm_list = ",".join(qs)
            comm_worst = COMM_RANK_INV[max([COMM_RANK.get(q, 0) for q in qs], default=0)] if qs else ""
            comm_mode  = g["comm_quality"].mode().iat[0] if qs else ""
        else:
            comm_list = ""; comm_worst = ""; comm_mode = ""

        # Address-chain rollup — available when flag_address_chain.py has run.
        # "best" = furthest-along outcome reached across calls for the pair.
        if "addr_landmark_step" in g.columns:
            lm_vals = g["addr_landmark_step"].dropna().tolist()
            gl_vals = g["addr_gali_step"].dropna().tolist()
            fl_vals = g["addr_floor_step"].dropna().tolist()
            st_vals = g["addr_chain_stuck_at"].dropna().tolist()
            lm_best = LANDMARK_INV[max([LANDMARK_RANK.get(x, -1) for x in lm_vals], default=-1)] if lm_vals else ""
            gl_best = GALI_INV    [max([GALI_RANK.get(x, -1)     for x in gl_vals], default=-1)] if gl_vals else ""
            fl_best = FLOOR_INV   [max([FLOOR_RANK.get(x, -1)    for x in fl_vals], default=-1)] if fl_vals else ""
            stuck_list = ",".join(st_vals)
            stuck_mode = g["addr_chain_stuck_at"].mode().iat[0] if st_vals else ""
        else:
            lm_best = gl_best = fl_best = stuck_list = stuck_mode = ""

        # Timestamps — one per (mobile, partner). Take first non-null.
        assigned  = pd.to_datetime(g["assigned_time"].dropna().iat[0]) if g["assigned_time"].notna().any() else pd.NaT
        decision  = pd.to_datetime(g["decision_time"].dropna().iat[0]) if g["decision_time"].notna().any() else pd.NaT
        installed_t = pd.to_datetime(g["installed_time"].dropna().iat[0]) if g["installed_time"].notna().any() else pd.NaT

        # Gap from decision_time -> installed_time (only meaningful for installed=1).
        gap_hours = (installed_t - decision).total_seconds() / 3600 if pd.notna(installed_t) and pd.notna(decision) else float("nan")

        return pd.Series({
            "n_calls"           : len(g),
            "total_duration_s"  : g["call_duration"].fillna(0).sum(),
            "primary_reasons"   : ",".join(primary),
            "secondary_reasons" : ",".join(sec),
            "reasons_union"     : ",".join(reasons),
            "reasons_count"     : len(reasons),
            "summaries"         : summaries[:2000],
            "transcripts"       : transcripts,   # all raw transcripts across calls
            "installed"         : g["installed"].max(),
            "decision_event"    : g["decision_event"].mode().iat[0] if len(g) else "",
            "decision_reason"   : g["decision_reason"].dropna().iat[0] if g["decision_reason"].notna().any() else "",
            "assigned_time"     : assigned,
            "decision_time"     : decision,
            "installed_time"    : installed_t,
            "decision_to_install_hours": gap_hours,
            "comm_quality_list" : comm_list,
            "comm_quality_worst": comm_worst,
            "comm_quality_mode" : comm_mode,
            "addr_landmark_best": lm_best,
            "addr_gali_best"    : gl_best,
            "addr_floor_best"   : fl_best,
            "addr_chain_stuck_at_list": stuck_list,
            "addr_chain_stuck_at_mode": stuck_mode,
        })

    pair = (merged
            .groupby(["mobile", "partner_id"])
            .apply(agg)
            .reset_index())
    print(f"\nPAIR-LEVEL ROWS: {len(pair):,}")

    # Quick descriptives
    print("\nn_calls per pair:")
    print(pair["n_calls"].value_counts().sort_index().to_string())

    print("\npair-level primary_reasons (first reason in sorted set):")
    pair["primary_first"] = pair["primary_reasons"].str.split(",").str[0]
    print(pair["primary_first"].value_counts().to_string())

    # How often does a pair have >1 distinct reason?
    multi = (pair["reasons_count"] > 1).sum()
    print(f"\npairs with >1 distinct reason across calls: {multi:,} "
          f"({multi/len(pair)*100:.1f}%)")

    pair.to_csv(PAIR_CSV, index=False)
    print(f"\nWROTE {PAIR_CSV}")


if __name__ == "__main__":
    main()
