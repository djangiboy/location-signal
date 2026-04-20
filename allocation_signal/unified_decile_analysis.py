"""
Unified Distance-Decile Analysis -- Delhi / Dec 2025
======================================================
One cohort: (mobile, partner_id) allocation -> first decision (INTERESTED,
ASSIGNED, or DECLINED-non-72h) -> install join (same partner).

Per distance decile (1 = nearest, 10 = farthest):
    total_obs
    %installed                  installed / total_obs
    %area_declined              area_flag / total_obs
    %address_not_clear          address_flag / total_obs

Denominator is total_obs (all allocations-with-a-decision), NOT total
declines -- this is the causal read: "does distance cause X?" not
"given X, is it Y?". (Fix for Geoff's Leak B.)

Install join unchanged from prior queries: same (mobile, partner_id)
match, OTP_VERIFIED after allocated_at. Analysis is at match level
(partner x booking), not booking level. A booking installed via a
different partner does NOT count as installed here.

SCOPE: post-Promise-Maker. Every row in the cohort is a booking
(serviceable=TRUE at the serviceability check). We evaluate Allocation
(GNN ranking of partners), NOT Promise Maker. A separate lead-level
analysis will evaluate Promise Maker later.

Run from: system_build/analyses/data/location_accuracy/
"""

from pathlib import Path

import pandas as pd
import numpy as np
from db_connectors import get_snow_connection


HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "investigative"
OUT_DIR.mkdir(exist_ok=True)

QUERY_FILE = HERE / "query_unified_correl.txt"

# ============================================================
# REGEX PATTERNS FOR DECLINE-REASON FLAGGING
# ============================================================
# AREA_DECLINE_PATTERN: coverage / serviceability / distance-framed
# partner-chosen decline reasons. Built on colleague's baseline +
# LLM semantic expansion (Hinglish, Hindi distance words, infra
# tokens, 'meters or more away' system dropdown).
#
# DELIBERATE EXCLUSIONS:
#   - 'address' -- top system dropdown is address-parsing, tracked
#     separately in ADDRESS_NOT_CLEAR_PATTERN.
#   - 'router' -- partner capacity, not coverage.
AREA_DECLINE_PATTERN = (
    r'feasible|fisible|fijebal|fesibal|fissible|fessible|fisibalty|fisibility|fesibility|fezible|fesable|'
    r'area|ariya|coverage|\bcvg\b|zone|outside|'
    r'location|'
    r'serviceab|servicab|network|signal|'
    r'line|lane|wire|wiring|cable|kebal|fiber|fibre|faiber|fybar|'
    r'range|renj|reach|daira|dayra|dayara|door|doori|\bdur\b|duri|\bfar\b|'
    r'\brfs\b|\bpole\b|\bjb\b|\bolt\b|tower|'
    r'meters or more away'
)

# ADDRESS_NOT_CLEAR_PATTERN: couldn't parse the address.
# System dropdown (English) + Hindi sibling. NOT coverage.
ADDRESS_NOT_CLEAR_PATTERN = r"understand the address|पता समझ"


# ============================================================
# SHARED HELPERS
# ============================================================
def load_query(path):
    """OBJECTIVE: Read a SQL file and strip trailing semicolon so the
    Snowflake connector treats it as a single statement."""
    with open(path, "r") as f:
        return f.read().strip().rstrip(";")


def fetch_cohort(conn, sql, label):
    """OBJECTIVE: Execute SQL via Snowflake cursor and return a pandas
    DataFrame with lowercased column names. Prints row count breadcrumb."""
    print(f"RUNNING {label} QUERY...")
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0].lower() for d in cur.description]
    cur.close()
    df = pd.DataFrame(rows, columns=cols)
    print(f"  FETCHED ROWS: {len(df):,}")
    return df


def report_nulls(df, col):
    """OBJECTIVE: Print null / non-null counts for a column so we catch
    data-quality gaps before trusting the column in downstream metrics."""
    n_total = len(df)
    n_null = df[col].isna().sum()
    print("\n" + "=" * 70)
    print(f"NULL CHECK ON {col}")
    print("=" * 70)
    print(f"TOTAL ROWS         : {n_total:,}")
    print(f"{col} IS NULL       : {n_null:,} ({(n_null / n_total) if n_total else 0:.1%})")
    print(f"{col} IS NOT NULL   : {n_total - n_null:,}")


def distance_deciles(df, dist_col="nearest_distance"):
    """OBJECTIVE: Drop null-distance rows, cast to float, and bucket into
    10 equal-count deciles via pd.qcut. Decile 1 = nearest,
    decile 10 = farthest."""
    a = df.dropna(subset=[dist_col]).copy()
    a[dist_col] = a[dist_col].astype(float)
    a["decile"] = pd.qcut(a[dist_col], q=10, labels=False, duplicates="drop") + 1
    return a


def prob_deciles(df, prob_col="probability"):
    """OBJECTIVE: Drop null-probability rows, cast to float, and bucket
    into 10 equal-count deciles via pd.qcut. Decile 1 = lowest GNN
    probability, decile 10 = highest."""
    a = df.dropna(subset=[prob_col]).copy()
    a[prob_col] = a[prob_col].astype(float)
    a["prob_decile"] = pd.qcut(a[prob_col], q=10, labels=False, duplicates="drop") + 1
    return a


# ============================================================
# FLAGGING
# ============================================================
def flag_outcomes(df, reason_col="decision_reason"):
    """OBJECTIVE: Attach three orthogonal 0/1 flags to each row:
        installed           -- already in cohort, just cast
        area_decline        -- decision_event=DECLINED AND area regex hit
        address_not_clear   -- decision_event=DECLINED AND address regex hit
    Area and address flags only fire when decision_event='DECLINED' --
    an INTERESTED/ASSIGNED row with 'not feasible' in remarks is not
    a decline. np.where chains."""
    a = df.copy()
    a["installed"] = a["installed"].fillna(0).astype(int)

    is_decline = a["decision_event"].astype(str).str.upper() == "DECLINED"
    reason = a[reason_col].astype(str)

    area_hit = reason.str.contains(AREA_DECLINE_PATTERN, case=False, na=False, regex=True)
    addr_hit = reason.str.contains(ADDRESS_NOT_CLEAR_PATTERN, case=False, na=False, regex=True)

    a["area_decline"] = np.where(is_decline & area_hit, 1, 0)
    a["address_not_clear"] = np.where(is_decline & addr_hit, 1, 0)
    return a


def report_event_mix(df):
    """OBJECTIVE: Sanity-check the cohort composition -- print the
    distribution of decision_event so we know the interest/assign vs
    decline split before slicing by decile."""
    a = df["decision_event"].astype(str).str.upper().value_counts(dropna=False)
    print("\n" + "=" * 70)
    print("DECISION EVENT MIX")
    print("=" * 70)
    total = len(df)
    for ev, n in a.items():
        print(f"  {ev:<15} {n:>8,}  ({n / total:.1%})")
    print(f"  {'TOTAL':<15} {total:>8,}")


# ============================================================
# CORE SLICE -- UNIFIED DECILE SUMMARY
# ============================================================
def decile_summary(df):
    """OBJECTIVE: Produce the headline table. For each distance decile,
    report total_obs, pct_installed, pct_area_decline,
    pct_address_not_clear, plus d_min / d_max / d_median. All pcts use
    total_obs as denominator (causal read). Saves CSV, returns DataFrame."""
    a = distance_deciles(df)
    b = (
        a.groupby("decile")
        .agg(
            total_obs=("installed", "size"),
            n_installed=("installed", "sum"),
            n_area_decline=("area_decline", "sum"),
            n_address_not_clear=("address_not_clear", "sum"),
            d_min=("nearest_distance", "min"),
            d_max=("nearest_distance", "max"),
            d_median=("nearest_distance", "median"),
        )
        .reset_index()
    )
    b["pct_installed"] = b["n_installed"] / b["total_obs"]
    b["pct_area_decline"] = b["n_area_decline"] / b["total_obs"]
    b["pct_address_not_clear"] = b["n_address_not_clear"] / b["total_obs"]

    print("\n" + "=" * 90)
    print("UNIFIED DECILE SUMMARY (1 = nearest, 10 = farthest)")
    print("  denominator = total_obs (all allocations with a decision)")
    print("=" * 90)
    print(b.to_string(index=False, formatters={
        "pct_installed": "{:.2%}".format,
        "pct_area_decline": "{:.2%}".format,
        "pct_address_not_clear": "{:.2%}".format,
        "d_min": "{:.3f}".format,
        "d_max": "{:.3f}".format,
        "d_median": "{:.3f}".format,
    }))

    for col in ("pct_installed", "pct_area_decline", "pct_address_not_clear"):
        sep = b[col].max() - b[col].min()
        print(f"SEPARATION {col:<25}: {sep:.2%}")

    b.to_csv(OUT_DIR / "decile_unified_summary.csv", index=False)
    print("SAVED: decile_unified_summary.csv")
    return b


# ============================================================
# PROBABILITY DECILE SUMMARY
# ============================================================
def prob_decile_summary(df):
    """OBJECTIVE: Same headline slice, but buckets on GNN `probability`
    instead of `nearest_distance`. Decile 1 = lowest predicted install
    probability, decile 10 = highest. Shows prob_min / prob_max /
    prob_median per bucket so we can read the GNN's calibration curve
    against observed outcomes."""
    a = prob_deciles(df)
    b = (
        a.groupby("prob_decile")
        .agg(
            total_obs=("installed", "size"),
            n_installed=("installed", "sum"),
            n_area_decline=("area_decline", "sum"),
            n_address_not_clear=("address_not_clear", "sum"),
            p_min=("probability", "min"),
            p_max=("probability", "max"),
            p_median=("probability", "median"),
            d_median=("nearest_distance", "median"),
        )
        .reset_index()
    )
    b["pct_installed"] = b["n_installed"] / b["total_obs"]
    b["pct_area_decline"] = b["n_area_decline"] / b["total_obs"]
    b["pct_address_not_clear"] = b["n_address_not_clear"] / b["total_obs"]

    print("\n" + "=" * 100)
    print("PROBABILITY DECILE SUMMARY (1 = lowest GNN prob, 10 = highest)")
    print("  denominator = total_obs")
    print("=" * 100)
    print(b.to_string(index=False, formatters={
        "pct_installed": "{:.2%}".format,
        "pct_area_decline": "{:.2%}".format,
        "pct_address_not_clear": "{:.2%}".format,
        "p_min": "{:.4f}".format,
        "p_max": "{:.4f}".format,
        "p_median": "{:.4f}".format,
        "d_median": "{:.2f}".format,
    }))

    for col in ("pct_installed", "pct_area_decline", "pct_address_not_clear"):
        sep = b[col].max() - b[col].min()
        print(f"SEPARATION {col:<25}: {sep:.2%}")

    b.to_csv(OUT_DIR / "decile_prob_summary.csv", index=False)
    print("SAVED: decile_prob_summary.csv")
    return b


# ============================================================
# PROB DECILE x NEAREST_TYPE CROSS-TABLE
# ============================================================
def prob_decile_by_nearest_type(df):
    """OBJECTIVE: Cross-tab probability decile x nearest_type to test
    whether GNN probability already encodes the active_base vs splitter
    distinction. Maanas recalls feeding BOTH splitter edges AND actual
    decision edges into the GNN. If that made the model type-aware,
    then within a fixed prob decile, active_base and splitter should
    install at similar rates -- probability subsumes type. Also prints
    the composition (% splitter per prob decile) to see whether the
    GNN routes splitters disproportionately to low-prob buckets."""
    a = prob_deciles(df).copy()
    a["nearest_type"] = a["nearest_type"].fillna("__NULL__").astype(str)

    # ---- side-by-side rates per (prob_decile, nearest_type) ----
    g = (
        a.groupby(["prob_decile", "nearest_type"])
        .agg(
            total=("installed", "size"),
            n_installed=("installed", "sum"),
            n_area=("area_decline", "sum"),
            n_addr=("address_not_clear", "sum"),
            p_median=("probability", "median"),
            d_median=("nearest_distance", "median"),
        )
        .reset_index()
    )
    g["pct_installed"] = g["n_installed"] / g["total"]
    g["pct_area"] = g["n_area"] / g["total"]
    g["pct_addr"] = g["n_addr"] / g["total"]

    for t in ("active_base", "splitter"):
        sub = g[g["nearest_type"] == t].copy()
        if sub.empty:
            continue
        print("\n" + "=" * 100)
        print(f"PROB DECILE × NEAREST_TYPE = '{t}'")
        print("=" * 100)
        print(sub[[
            "prob_decile", "total",
            "pct_installed", "pct_area", "pct_addr",
            "p_median", "d_median",
        ]].to_string(index=False, formatters={
            "pct_installed": "{:.2%}".format,
            "pct_area": "{:.2%}".format,
            "pct_addr": "{:.2%}".format,
            "p_median": "{:.4f}".format,
            "d_median": "{:.2f}".format,
        }))

    # ---- composition: % splitter per prob decile ----
    tot = a.groupby("prob_decile").size().rename("total")
    spl = a[a["nearest_type"] == "splitter"].groupby("prob_decile").size().rename("splitter")
    ab  = a[a["nearest_type"] == "active_base"].groupby("prob_decile").size().rename("active_base")
    comp = pd.concat([tot, spl, ab], axis=1).fillna(0).astype(int).reset_index()
    comp["pct_splitter"] = comp["splitter"] / comp["total"]

    print("\n" + "=" * 70)
    print("COMPOSITION -- % SPLITTER PER PROB DECILE")
    print("  (heavy splitter share at low prob => GNN routes splitters there)")
    print("=" * 70)
    print(comp.to_string(index=False, formatters={
        "pct_splitter": "{:.2%}".format,
    }))

    g.to_csv(OUT_DIR / "prob_decile_by_nearest_type.csv", index=False)
    comp.to_csv(OUT_DIR / "prob_decile_splitter_composition.csv", index=False)
    print("\nSAVED: prob_decile_by_nearest_type.csv, prob_decile_splitter_composition.csv")
    return g, comp


# ============================================================
# NEAREST_TYPE GROUPBY (active_base vs splitter)
# ============================================================
def summary_by_nearest_type(df):
    """OBJECTIVE: Simple groupby on `nearest_type` ('active_base' vs
    'splitter') showing total_obs, %installed, %area_decline,
    %address_not_clear, and distance min/max/median per bucket.
    Splitter = freshly-onboarded partners using a fixed distribution
    point as install-proxy (per Maanas). Cold-start surfacing cut."""
    a = df.copy()
    a["nearest_type"] = a["nearest_type"].fillna("__NULL__").astype(str)
    b = (
        a.groupby("nearest_type")
        .agg(
            total_obs=("installed", "size"),
            n_installed=("installed", "sum"),
            n_area_decline=("area_decline", "sum"),
            n_address_not_clear=("address_not_clear", "sum"),
            d_min=("nearest_distance", "min"),
            d_max=("nearest_distance", "max"),
            d_median=("nearest_distance", "median"),
        )
        .reset_index()
        .sort_values("total_obs", ascending=False)
    )
    b["pct_installed"] = b["n_installed"] / b["total_obs"]
    b["pct_area_decline"] = b["n_area_decline"] / b["total_obs"]
    b["pct_address_not_clear"] = b["n_address_not_clear"] / b["total_obs"]

    print("\n" + "=" * 100)
    print("SUMMARY BY NEAREST_TYPE (active_base vs splitter)")
    print("=" * 100)
    print(b.to_string(index=False, formatters={
        "pct_installed": "{:.2%}".format,
        "pct_area_decline": "{:.2%}".format,
        "pct_address_not_clear": "{:.2%}".format,
        "d_min": "{:.3f}".format,
        "d_max": "{:.3f}".format,
        "d_median": "{:.3f}".format,
    }))
    b.to_csv(OUT_DIR / "summary_by_nearest_type.csv", index=False)
    print("SAVED: summary_by_nearest_type.csv")
    return b



# ============================================================
# MAIN
# ============================================================
def main():
    """OBJECTIVE: Run the full unified pipeline -- pull cohort, flag
    outcomes, report event mix + null check, produce the headline
    decile summary. Dumps raw cohort to CSV for reuse."""
    conn = get_snow_connection()
    if conn is None:
        print("NO SNOWFLAKE CONNECTION. ABORTING.")
        return

    try:
        df = fetch_cohort(conn, load_query(QUERY_FILE), "UNIFIED")
    finally:
        conn.close()
        print("SNOWFLAKE CONNECTION CLOSED")

    df.to_csv(OUT_DIR / "cohort_unified_raw.csv", index=False)
    print("SAVED: cohort_unified_raw.csv")
    
    df = df[df['bdo_lead']==0].copy()
    print(f"AFTER NON-BDO FILTER: {len(df):,} ROWS")

    df = flag_outcomes(df)
    report_event_mix(df)
    report_nulls(df, "nearest_distance")
    report_nulls(df, "probability")
    decile_summary(df)
    prob_decile_summary(df)
    summary_by_nearest_type(df)
    prob_decile_by_nearest_type(df)


if __name__ == "__main__":
    main()
