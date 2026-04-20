"""
Location Accuracy -- Distance-Decile Analyses
==============================================
Cohort: Delhi, Dec 2025 bookings.

Two queries share the same cohort structure, differ only in event_name
filter of decision_pairs:
  - query_install_correl.txt   event_name in ('INTERESTED', 'ASSIGNED')
  - query_decline_correl.txt   event_name = 'DECLINED'
                               (excl. System_Force_Declined_Post_Assigned_72hours)

Four slices, all by distance decile (1 = nearest, 10 = farthest):
  1. install_rate                    = installed / total           (INSTALL cohort)
  2. area_decline_rate               = area_flags / total          (DECLINE cohort)
  3. address_not_clear_decline_rate  = address_flags / total       (DECLINE cohort)
  4. post_decline_install_rate       = later_installed / total     (DECLINE cohort)

Separation = D1 rate - D10 rate. Headline metric throughout.

area vs address_not_clear kept SEPARATE: different root causes
(coverage gap vs booking-intake/address-capture quality), different interventions.

SCOPE: post-Promise-Maker. Cohort already filtered to serviceable=TRUE.
Evaluates Allocation (GNN ranking), not Promise Maker.

Run from: system_build/analyses/data/location_accuracy/
"""

from pathlib import Path

import pandas as pd
import numpy as np
from db_connectors import get_snow_connection


HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "investigative"
OUT_DIR.mkdir(exist_ok=True)


INSTALL_QUERY_FILE = "query_install_correl.txt"
DECLINE_QUERY_FILE = "query_decline_correl.txt"

# ============================================================
# REGEX PATTERNS FOR DECLINE-REASON FLAGGING
# ============================================================
# AREA_DECLINE_PATTERN: coverage / serviceability / distance-framed
# declines. Built on colleague's baseline + LLM semantic expansion
# (Hinglish spellings, Hindi distance words, infra tokens, the
# 'meters or more away' system dropdown).
#
# DELIBERATE EXCLUSIONS:
#   - 'address' -- the top system dropdown "couldn't understand the
#     address" (4,962 rows) is address-parsing, not coverage. Tracked
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

# ADDRESS_NOT_CLEAR_PATTERN: partner couldn't parse the address text.
# System dropdown (English) + Hindi sibling. NOT coverage.
ADDRESS_NOT_CLEAR_PATTERN = r"understand the address|पता समझ"


# ============================================================
# SHARED HELPERS
# ============================================================
def load_query(path):
    """OBJECTIVE: Read a SQL file from disk and strip trailing semicolon
    so the Snowflake connector accepts it as a single statement."""
    with open(path, "r") as f:
        return f.read().strip().rstrip(";")


def fetch_cohort(conn, sql, label):
    """OBJECTIVE: Run SQL via Snowflake cursor, return a pandas DataFrame
    with lowercased column names. Prints row count as a breadcrumb."""
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
    """OBJECTIVE: Surface data-quality gaps by printing null / non-null
    counts for a column before we trust it in any downstream metric."""
    n_total = len(df)
    n_null = df[col].isna().sum()
    print("\n" + "=" * 70)
    print(f"NULL CHECK ON {col}")
    print("=" * 70)
    print(f"TOTAL ROWS         : {n_total:,}")
    print(f"{col} IS NULL       : {n_null:,} ({(n_null / n_total) if n_total else 0:.1%})")
    print(f"{col} IS NOT NULL   : {n_total - n_null:,}")


def distance_deciles(df, dist_col="nearest_distance"):
    """OBJECTIVE: Drop rows with null distance, cast to float, and cut
    into 10 equal-count buckets using pd.qcut. Decile 1 = nearest,
    decile 10 = farthest. Returns a copy with a new 'decile' column."""
    a = df.dropna(subset=[dist_col]).copy()
    a[dist_col] = a[dist_col].astype(float)
    a["decile"] = pd.qcut(a[dist_col], q=10, labels=False, duplicates="drop") + 1
    return a


def _rate_by_decile(df, flag_col, rate_label, title, csv_name):
    """OBJECTIVE: Generic decile aggregator. Given a binary flag column,
    compute flagged/total per distance decile, print a formatted table
    with d_min/d_max/d_median, report separation (best - worst), and
    save a CSV. Shared engine for all four slices."""
    a = distance_deciles(df)
    b = (
        a.groupby("decile")
        .agg(
            total=(flag_col, "size"),
            flagged=(flag_col, "sum"),
            d_min=("nearest_distance", "min"),
            d_max=("nearest_distance", "max"),
            d_median=("nearest_distance", "median"),
        )
        .reset_index()
    )
    b[rate_label] = b["flagged"] / b["total"]

    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print(b.to_string(index=False, formatters={
        rate_label: "{:.2%}".format,
        "d_min": "{:.3f}".format,
        "d_max": "{:.3f}".format,
        "d_median": "{:.3f}".format,
    }))
    sep = b[rate_label].max() - b[rate_label].min()
    print(f"SEPARATION (best - worst): {sep:.2%}")
    b.to_csv(OUT_DIR / csv_name, index=False)
    print(f"SAVED: {csv_name}")
    return b


# ============================================================
# FLAGGING
# ============================================================
def flag_declines(df, reason_col="decision_reason"):
    """OBJECTIVE: Apply the two semantic regexes to decision_reason and
    attach area_decline + address_not_clear flags (0/1) as columns.
    np.where pattern, case-insensitive, null-safe. Intentionally orthogonal
    buckets -- a reason can match both, neither, or one."""
    a = df.copy()
    reason = a[reason_col].astype(str)
    a["area_decline"] = np.where(
        reason.str.contains(AREA_DECLINE_PATTERN, case=False, na=False, regex=True), 1, 0
    )
    a["address_not_clear"] = np.where(
        reason.str.contains(ADDRESS_NOT_CLEAR_PATTERN, case=False, na=False, regex=True), 1, 0
    )
    return a


def summarize_decline_reasons(df, reason_col="decision_reason"):
    """OBJECTIVE: Dump every unique decline reason (lowercased + stripped)
    with its count and area_decline flag to CSV. This is the QA surface --
    scan this file to catch regex false positives/negatives."""
    a = df.copy()
    a["_reason_norm"] = a[reason_col].fillna("__NULL__").astype(str).str.strip().str.lower()
    b = (
        a.groupby("_reason_norm")
        .agg(
            count=("area_decline", "size"),
            area_decline=("area_decline", "max"),
        )
        .reset_index()
        .rename(columns={"_reason_norm": "decision_reason"})
        .sort_values("count", ascending=False)
    )
    b.to_csv(OUT_DIR / "decline_reasons_summary.csv", index=False)

    n_flagged_rows = int((a["area_decline"] == 1).sum())
    n_total = len(a)
    print("\n" + "=" * 70)
    print("DECLINE REASONS SUMMARY")
    print("=" * 70)
    print(f"UNIQUE REASONS (lowercased)        : {len(b):,}")
    print(f"UNIQUE REASONS FLAGGED AREA        : {(b['area_decline'] == 1).sum():,}")
    print(f"ROWS FLAGGED AREA / TOTAL DECLINES : {n_flagged_rows:,} / {n_total:,} ({n_flagged_rows / n_total:.1%})")
    print("SAVED: decline_reasons_summary.csv")
    print("\nTOP 15 REASONS:")
    print(b.head(15).to_string(index=False))
    return b


# ============================================================
# SLICE 1 -- INSTALL RATE BY DISTANCE DECILE (INSTALL COHORT)
# ============================================================
def install_rate_by_decile(df):
    """OBJECTIVE: Of all allocated leads (INTERESTED/ASSIGNED cohort),
    what share installed (OTP_VERIFIED by same partner), per distance
    decile? Headline slice -- tests whether distance predicts end-to-end
    installability at all."""
    a = df.copy()
    a["installed"] = a["installed"].astype(int)
    return _rate_by_decile(
        a,
        flag_col="installed",
        rate_label="install_rate",
        title="INSTALL RATE BY DISTANCE DECILE (1 = nearest, 10 = farthest)",
        csv_name="decile_install_rate.csv",
    )


# ============================================================
# SLICE 2 -- AREA DECLINE RATE BY DISTANCE DECILE (DECLINE COHORT)
# ============================================================
def area_decline_rate_by_decile(df):
    """OBJECTIVE: Conditional on declining, what share of declines cite
    an area/coverage reason (per AREA_DECLINE_PATTERN)? Per distance
    decile. Tests whether partner-stated coverage rejection rises with
    distance."""
    return _rate_by_decile(
        df,
        flag_col="area_decline",
        rate_label="area_decline_rate",
        title="AREA DECLINE RATE BY DISTANCE DECILE",
        csv_name="decile_area_decline_rate.csv",
    )


# ============================================================
# SLICE 3 -- ADDRESS-NOT-CLEAR RATE BY DISTANCE DECILE
# ============================================================
def address_not_clear_rate_by_decile(df):
    """OBJECTIVE: Conditional on declining, what share cite 'couldn't
    understand the address' (English dropdown + Hindi sibling)? Per
    distance decile. Pure address-parsing SHOULD be distance-independent;
    any correlation is a finding (substrate vs partner dismissal)."""
    return _rate_by_decile(
        df,
        flag_col="address_not_clear",
        rate_label="address_not_clear_decline_rate",
        title="ADDRESS-NOT-CLEAR DECLINE RATE BY DISTANCE DECILE",
        csv_name="decile_address_not_clear_rate.csv",
    )


# ============================================================
# SLICE 4 -- POST-DECLINE INSTALL RATE BY DISTANCE DECILE
# ============================================================
def post_decline_install_by_decile(df):
    """OBJECTIVE: Of leads the partner declined, what share did the
    SAME partner later install (re-notification loop)? Per distance
    decile. Tests whether decline is recoverable or terminal.
    Caveat: observation window is ~31 days (installs up to 2026-01-31
    vs declines through 2025-12-31) -- long-cycle recoveries undercounted."""
    a = df.copy()
    a["installed"] = a["installed"].astype(int)
    return _rate_by_decile(
        a,
        flag_col="installed",
        rate_label="post_decline_install_rate",
        title="POST-DECLINE INSTALL RATE BY DISTANCE DECILE (same partner)",
        csv_name="decile_post_decline_install_rate.csv",
    )


# ============================================================
# MAIN
# ============================================================
def main():
    """OBJECTIVE: Orchestrate the full pipeline -- pull both cohorts
    once, dump raw CSVs for reuse, then run all four decile slices.
    Single Snowflake connection reused across both queries."""
    conn = get_snow_connection()
    if conn is None:
        print("NO SNOWFLAKE CONNECTION. ABORTING.")
        return

    try:
        df_install = fetch_cohort(conn, load_query(INSTALL_QUERY_FILE), "INSTALL")
        df_decline = fetch_cohort(conn, load_query(DECLINE_QUERY_FILE), "DECLINE")
    finally:
        conn.close()
        print("SNOWFLAKE CONNECTION CLOSED")
    
    df_install = df_install[df_install['bdo_lead']==0].copy()
    df_decline = df_decline[df_decline['bdo_lead']==0].copy()


    df_install.to_csv(OUT_DIR / "cohort_install_raw.csv", index=False)
    df_decline.to_csv(OUT_DIR / "cohort_decline_raw.csv", index=False)
    print("SAVED: cohort_install_raw.csv, cohort_decline_raw.csv")

    # ---- INSTALL cohort ----
    report_nulls(df_install, "nearest_distance")
    install_rate_by_decile(df_install)

    # ---- DECLINE cohort ----
    report_nulls(df_decline, "nearest_distance")
    df_decline = flag_declines(df_decline)
    summarize_decline_reasons(df_decline)
    area_decline_rate_by_decile(df_decline)
    address_not_clear_rate_by_decile(df_decline)
    post_decline_install_by_decile(df_decline)


if __name__ == "__main__":
    main()
