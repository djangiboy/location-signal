"""
Tenure-Gap Investigation
=========================
Test: does the active_base vs splitter install-rate gap (3-17pp across
prob deciles, peaks at D3-D4) align with partner tenure at time of match?

Hypotheses to distinguish:
  H1 -- Pure cold-start: low-tenure partners drive the gap because they
        haven't yet routed enough bookings. Gap should concentrate at
        partner_tenure_at_match < some threshold.
  H2 -- Splitter inflation: partners roam with an app submitting many
        splitter lat/lng points to attract bookings. Partners with a
        high splitter-to-active-base ratio drive the gap, independent
        of pure age.
  H3 -- Both, independently measurable.

Data sources:
  cohort_unified_raw.csv           -- our match-level data (root)
  t_partner (genie2 MySQL)         -- partner_added_time, active_base_count
  t_node_splitter_gs (Snowflake)   -- count per partner = splitter points submitted

Grain + merge keys (from probe_tenure_tables.py):
  cohort.partner_id                <-> t_partner.long_lco_id             (BIGINT <-> BIGINT)
  cohort.partner_id                <-> t_node_splitter_gs.PARTNER_ID    (BIGINT <-> VARCHAR, cast on one side)

Outputs -> investigative/
"""

from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

from db_connectors import get_genie2_server, get_snow_connection


HERE = Path(__file__).resolve().parent
INV = HERE / "investigative"
INV.mkdir(exist_ok=True)


# ============================================================
# LOADERS
# ============================================================
def load_cohort():
    """OBJECTIVE: Pull the non-BDO unified cohort from cached CSV."""
    df = pd.read_csv(INV / "cohort_unified_raw.csv")
    df = df[df["bdo_lead"] == 0].copy()
    df["partner_id"] = df["partner_id"].astype("int64")
    df["allocated_at"] = pd.to_datetime(df["allocated_at"])
    print(f"COHORT LOADED: {len(df):,} rows (non-BDO)")
    return df


def load_t_partner():
    """OBJECTIVE: Pull partner-level snapshot from genie2 MySQL (RDS).
    Grain: 1 row per long_lco_id. RDS schema has only 5 columns --
    active_base_count is NOT here (see load_active_base_counts)."""
    conn = get_genie2_server()
    try:
        sql = ("SELECT long_lco_id AS partner_id, partner_added_time, "
               "logical_group, zone_alias FROM t_partner")
        df = pd.read_sql(sql, conn)
    finally:
        conn.close()
    df["partner_id"] = df["partner_id"].astype("int64")
    df["partner_added_time"] = pd.to_datetime(df["partner_added_time"])
    dup = df["partner_id"].duplicated().sum()
    print(f"t_partner LOADED: {len(df):,} rows | distinct partners {df['partner_id'].nunique():,} | duplicates {dup}")
    return df


def load_active_base_counts():
    """OBJECTIVE: Aggregate t_active_base (RDS genie2) to get
    current active_base_count per partner. Grain after aggregation:
    1 row per long_partner_id. This replaces the missing
    active_base_count column on RDS t_partner."""
    conn = get_genie2_server()
    try:
        sql = ("SELECT long_partner_id AS partner_id, "
               "COUNT(*) AS active_base_count, "
               "COUNT(DISTINCT long_customer_id) AS active_customer_count "
               "FROM t_active_base "
               "WHERE long_partner_id IS NOT NULL "
               "GROUP BY long_partner_id")
        df = pd.read_sql(sql, conn)
    finally:
        conn.close()
    df["partner_id"] = df["partner_id"].astype("int64")
    print(f"active_base counts LOADED: {len(df):,} partners with at least one active_base row")
    return df


def load_splitter_counts():
    """OBJECTIVE: Count DISTINCT (lat, lng) splitter points per partner
    from prod_db.ds_tables.t_node_splitter_gs. Dedup first -- partners
    ping the same coord repeatedly via roaming app; counting raw rows
    would inflate the splitter_count signal. Grain after aggregation:
    1 row per PARTNER_ID. Also pull total rows and dedup delta as a
    sanity check."""
    conn = get_snow_connection()
    try:
        sql = (
            "SELECT PARTNER_ID AS partner_id_str, COUNT(*) AS splitter_count "
            "FROM (SELECT DISTINCT PARTNER_ID, LATITUDE, LONGITUDE "
            "      FROM prod_db.ds_tables.t_node_splitter_gs) "
            "GROUP BY PARTNER_ID"
        )
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()

        # sanity: rows before dedup vs after
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM prod_db.ds_tables.t_node_splitter_gs")
        raw_n = cur.fetchone()[0]
        cur.close()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM (SELECT DISTINCT PARTNER_ID, LATITUDE, LONGITUDE FROM prod_db.ds_tables.t_node_splitter_gs)")
        dedup_n = cur.fetchone()[0]
        cur.close()
    finally:
        conn.close()
    df = pd.DataFrame(rows, columns=["partner_id_str", "splitter_count"])
    df["partner_id"] = pd.to_numeric(df["partner_id_str"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["partner_id"]).copy()
    df["partner_id"] = df["partner_id"].astype("int64")
    print(f"splitter_counts LOADED: {len(df):,} partners with splitter submissions")
    print(f"  raw t_node_splitter_gs rows: {raw_n:,}")
    print(f"  distinct (partner, lat, lng): {dedup_n:,}")
    print(f"  dedup removed: {raw_n - dedup_n:,} duplicate rows ({(raw_n - dedup_n) / raw_n:.1%})")
    return df[["partner_id", "splitter_count"]]


# ============================================================
# MERGE + ENRICH
# ============================================================
def enrich_cohort(cohort, t_partner, active_base_counts, splitter_counts):
    """OBJECTIVE: Left-join t_partner (tenure), active_base_counts,
    and splitter_counts onto the cohort. Report drop-off at each step."""
    n0 = len(cohort)
    a = cohort.merge(t_partner, on="partner_id", how="left")
    missing_tenure = a["partner_added_time"].isna().sum()
    print(f"After t_partner join: {len(a):,} rows | missing tenure {missing_tenure:,} ({missing_tenure/n0:.1%})")

    b = a.merge(active_base_counts, on="partner_id", how="left")
    missing_ab = b["active_base_count"].isna().sum()
    print(f"After active_base_counts join: {len(b):,} rows | missing active_base {missing_ab:,} ({missing_ab/n0:.1%})")
    b["active_base_count"] = b["active_base_count"].fillna(0).astype(int)
    b["active_customer_count"] = b["active_customer_count"].fillna(0).astype(int)

    c = b.merge(splitter_counts, on="partner_id", how="left")
    missing_sp = c["splitter_count"].isna().sum()
    print(f"After splitter_counts join: {len(c):,} rows | missing splitter {missing_sp:,} ({missing_sp/n0:.1%})")
    c["splitter_count"] = c["splitter_count"].fillna(0).astype(int)

    # ---- tenure at time of allocation ----
    c["tenure_days_at_match"] = (c["allocated_at"] - c["partner_added_time"]).dt.days
    bad = (c["tenure_days_at_match"] < 0).sum()
    if bad > 0:
        print(f"WARNING: {bad} rows have negative tenure (partner_added_time > allocated_at)")

    # ---- partner-level splitter share (static, as-of-now) ----
    denom = c["splitter_count"] + c["active_base_count"]
    c["splitter_share"] = np.where(denom > 0, c["splitter_count"] / denom, np.nan)

    # ---- installed -> int ----
    c["installed"] = c["installed"].fillna(0).astype(int)
    return c


# ============================================================
# BINNING
# ============================================================
TENURE_BINS = [-1, 30, 90, 180, 365, 730, 10_000]
TENURE_LABELS = ["<=30d", "31-90d", "91-180d", "181-365d", "366-730d", "730d+"]

SPLITTER_SHARE_BINS = [-0.01, 0.1, 0.5, 0.9, 1.01]
SPLITTER_SHARE_LABELS = ["0-10%", "10-50%", "50-90%", "90-100%"]


def add_bins(df):
    """OBJECTIVE: Add tenure_bucket + splitter_share_bucket columns
    for groupby slicing."""
    a = df.copy()
    a["tenure_bucket"] = pd.cut(a["tenure_days_at_match"], bins=TENURE_BINS, labels=TENURE_LABELS)
    a["splitter_share_bucket"] = pd.cut(a["splitter_share"], bins=SPLITTER_SHARE_BINS, labels=SPLITTER_SHARE_LABELS)
    return a


def prob_deciles(df, prob_col="probability"):
    """OBJECTIVE: Decile on GNN probability. Mirrors unified_decile_analysis.py."""
    a = df.dropna(subset=[prob_col]).copy()
    a[prob_col] = a[prob_col].astype(float)
    a["prob_decile"] = pd.qcut(a[prob_col], q=10, labels=False, duplicates="drop") + 1
    return a


# ============================================================
# ANALYSES
# ============================================================
def tenure_distribution(df):
    """OBJECTIVE: How is tenure distributed in the cohort overall,
    and split by nearest_type? Does splitter allocations really come
    from newer partners?"""
    print("\n" + "=" * 80)
    print("TENURE DISTRIBUTION BY nearest_type")
    print("=" * 80)
    g = (
        df.groupby(["nearest_type", "tenure_bucket"], observed=True)
        .size().unstack("tenure_bucket").fillna(0).astype(int)
    )
    print(g.to_string())
    g.to_csv(INV / "tenure_by_nearest_type.csv")
    print(f"SAVED: investigative/tenure_by_nearest_type.csv")


def install_rate_by_tenure(df):
    """OBJECTIVE: Install rate per tenure bucket, overall and split by
    nearest_type. Tests H1: does low-tenure explain the gap?"""
    print("\n" + "=" * 80)
    print("INSTALL RATE BY TENURE BUCKET  (overall + by nearest_type)")
    print("=" * 80)
    overall = (
        df.groupby("tenure_bucket", observed=True)
        .agg(total=("installed", "size"), installed=("installed", "sum"))
        .reset_index()
    )
    overall["pct_installed"] = overall["installed"] / overall["total"]
    print("\nOVERALL:")
    print(overall.to_string(index=False, formatters={"pct_installed": "{:.2%}".format}))

    split = (
        df.groupby(["tenure_bucket", "nearest_type"], observed=True)
        .agg(total=("installed", "size"), installed=("installed", "sum"))
        .reset_index()
    )
    split["pct_installed"] = split["installed"] / split["total"]
    pivot = split.pivot(index="tenure_bucket", columns="nearest_type",
                        values="pct_installed").fillna(0)
    pivot_n = split.pivot(index="tenure_bucket", columns="nearest_type",
                          values="total").fillna(0).astype(int)
    print("\nBY nearest_type (install rate):")
    print(pivot.applymap(lambda v: f"{v:.2%}" if pd.notna(v) else "").to_string())
    print("\nBY nearest_type (n):")
    print(pivot_n.to_string())
    split.to_csv(INV / "install_by_tenure_x_type.csv", index=False)
    print("SAVED: investigative/install_by_tenure_x_type.csv")


def gap_by_tenure_within_prob(df):
    """OBJECTIVE: The headline test. At each prob_decile x tenure_bucket,
    compute the active_base vs splitter install-rate gap. If H1 holds,
    gap should collapse in high-tenure buckets."""
    a = prob_deciles(df)
    g = (
        a.groupby(["prob_decile", "tenure_bucket", "nearest_type"], observed=True)
        .agg(total=("installed", "size"), installed=("installed", "sum"))
        .reset_index()
    )
    g["pct_installed"] = g["installed"] / g["total"]
    piv_rate = g.pivot_table(index=["prob_decile", "tenure_bucket"],
                             columns="nearest_type", values="pct_installed",
                             observed=True)
    piv_n = g.pivot_table(index=["prob_decile", "tenure_bucket"],
                          columns="nearest_type", values="total",
                          observed=True, fill_value=0).astype(int)

    if "active_base" in piv_rate.columns and "splitter" in piv_rate.columns:
        piv_rate["gap_pp"] = (piv_rate["active_base"] - piv_rate["splitter"]) * 100

    combined = piv_rate.copy()
    for c in piv_n.columns:
        combined[(c, "n")] = piv_n[c]

    print("\n" + "=" * 90)
    print("GAP (active_base - splitter install rate) BY prob_decile x tenure_bucket")
    print("=" * 90)
    print(piv_rate.applymap(lambda v: f"{v:.2%}" if pd.notna(v) and not isinstance(v, (int,)) else v).to_string())
    print("\n(cell counts n)")
    print(piv_n.to_string())

    piv_rate.to_csv(INV / "gap_by_prob_decile_x_tenure.csv")
    piv_n.to_csv(INV / "gap_by_prob_decile_x_tenure_ncounts.csv")
    print("SAVED: investigative/gap_by_prob_decile_x_tenure.csv (rates) + _ncounts.csv")


def install_by_splitter_share(df):
    """OBJECTIVE: Partner-level splitter_share = splitter_count /
    (splitter_count + active_base_count). Tests H2: do partners with
    high splitter-submission ratio underperform at fixed prob decile?"""
    a = prob_deciles(df.dropna(subset=["splitter_share"]))
    g = (
        a.groupby(["prob_decile", "splitter_share_bucket"], observed=True)
        .agg(total=("installed", "size"), installed=("installed", "sum"))
        .reset_index()
    )
    g["pct_installed"] = g["installed"] / g["total"]
    piv = g.pivot(index="prob_decile", columns="splitter_share_bucket",
                  values="pct_installed")
    piv_n = g.pivot(index="prob_decile", columns="splitter_share_bucket",
                    values="total").fillna(0).astype(int)

    print("\n" + "=" * 90)
    print("INSTALL RATE BY prob_decile x partner_splitter_share")
    print("  (splitter_share = splitter_count / (splitter_count + active_base_count))")
    print("=" * 90)
    print(piv.applymap(lambda v: f"{v:.2%}" if pd.notna(v) else "").to_string())
    print("\n(n)")
    print(piv_n.to_string())

    piv.to_csv(INV / "install_by_prob_x_splitter_share.csv")
    piv_n.to_csv(INV / "install_by_prob_x_splitter_share_ncounts.csv")
    print("SAVED: investigative/install_by_prob_x_splitter_share.csv + ncounts")


def partner_level_summary(df):
    """OBJECTIVE: Partner-level descriptive table. For each partner,
    show their age, active_base_count, splitter_count, splitter_share,
    and the cohort share of splitter-allocations vs active_base-allocations
    they received. Ground truth for 'who is this partner'."""
    g = (
        df.groupby("partner_id")
        .agg(
            n_matches=("installed", "size"),
            n_installed=("installed", "sum"),
            n_splitter_matches=("nearest_type", lambda s: (s == "splitter").sum()),
            tenure_days_median=("tenure_days_at_match", "median"),
            active_base_count=("active_base_count", "first"),
            splitter_count=("splitter_count", "first"),
            splitter_share=("splitter_share", "first"),
        )
        .reset_index()
    )
    g["install_rate"] = g["n_installed"] / g["n_matches"]
    g["match_splitter_rate"] = g["n_splitter_matches"] / g["n_matches"]
    g = g.sort_values("n_matches", ascending=False)
    g.to_csv(INV / "partner_level_summary.csv", index=False)
    print(f"\nSAVED: investigative/partner_level_summary.csv ({len(g):,} partners)")


# ============================================================
# MAIN
# ============================================================
def main():
    print(f"RUN: {datetime.now():%Y-%m-%d %H:%M:%S}")
    cohort = load_cohort()
    t_partner = load_t_partner()
    active_base_counts = load_active_base_counts()
    splitter_counts = load_splitter_counts()

    enriched = enrich_cohort(cohort, t_partner, active_base_counts, splitter_counts)
    enriched = add_bins(enriched)
    enriched.to_csv(INV / "cohort_enriched_tenure.csv", index=False)
    print(f"SAVED: investigative/cohort_enriched_tenure.csv")

    tenure_distribution(enriched)
    install_rate_by_tenure(enriched)
    gap_by_tenure_within_prob(enriched)
    install_by_splitter_share(enriched)
    partner_level_summary(enriched)


if __name__ == "__main__":
    main()
