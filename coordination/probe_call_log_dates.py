"""
Probe USER_CONNECTION_CALL_LOGS population history.

QUESTIONS
  1. What is the earliest and latest created_at in the table?
  2. How does monthly row volume evolve — is there a clear "go-live" month?
  3. When did recording_url start being populated? What fraction has it by month?
  4. Which call_status values are present and how do they distribute by month?
  5. (Sanity) distinct count of call_id per month, unique from_number per month.

Also a smaller second query for `partner_call_log` (PTL) for context — did PTL
launch on a different date?

Run from: analyses/data/partner_customer_calls/
    python probe_call_log_dates.py
"""

from pathlib import Path
import pandas as pd
from db_connectors import get_snow_connection


HERE    = Path(__file__).resolve().parent
OUT_DIR = HERE / "investigative"
OUT_DIR.mkdir(exist_ok=True)


Q_MIN_MAX_UCCL = """
SELECT
    MIN(created_at)  AS min_created_at,
    MAX(created_at)  AS max_created_at,
    COUNT(*)         AS total_rows,
    COUNT(DISTINCT call_id) AS distinct_call_ids
FROM prod_db.postgres_rds_partner_call_log_ivr.user_connection_call_logs
"""

Q_MONTHLY_UCCL = """
SELECT
    DATE_TRUNC('month', created_at)::DATE            AS month,
    COUNT(*)                                         AS row_count,
    COUNT(DISTINCT call_id)                          AS distinct_calls,
    COUNT(DISTINCT RIGHT(from_number, 10))           AS distinct_from,
    SUM(CASE WHEN recording_url IS NOT NULL
              AND TRIM(recording_url) NOT IN ('', 'null')
            THEN 1 ELSE 0 END)                       AS with_recording,
    SUM(CASE WHEN call_status = 'CONNECTED'    THEN 1 ELSE 0 END) AS connected,
    SUM(CASE WHEN call_status = 'MISSED_CALL'  THEN 1 ELSE 0 END) AS missed,
    SUM(CASE WHEN call_status = 'CANCELLED'    THEN 1 ELSE 0 END) AS cancelled,
    SUM(CASE WHEN call_status = 'REJECTED'     THEN 1 ELSE 0 END) AS rejected,
    SUM(CASE WHEN call_status = 'UNKNOWN'      THEN 1 ELSE 0 END) AS unknown_st,
    SUM(CASE WHEN call_status NOT IN
            ('CONNECTED','MISSED_CALL','CANCELLED','REJECTED','UNKNOWN')
         OR call_status IS NULL THEN 1 ELSE 0 END)   AS other_status
FROM prod_db.postgres_rds_partner_call_log_ivr.user_connection_call_logs
GROUP BY 1
ORDER BY 1
"""

Q_DAILY_FIRST_WEEK_UCCL = """
-- Daily granularity for the first month that has any data.
WITH first_month AS (
    SELECT DATE_TRUNC('month', MIN(created_at))::DATE AS m
    FROM prod_db.postgres_rds_partner_call_log_ivr.user_connection_call_logs
)
SELECT
    created_at::DATE AS day,
    COUNT(*)         AS row_count,
    SUM(CASE WHEN recording_url IS NOT NULL
              AND TRIM(recording_url) NOT IN ('', 'null')
            THEN 1 ELSE 0 END)  AS with_recording
FROM prod_db.postgres_rds_partner_call_log_ivr.user_connection_call_logs, first_month
WHERE DATE_TRUNC('month', created_at)::DATE = first_month.m
GROUP BY 1
ORDER BY 1
"""

Q_MIN_MAX_PCL = """
SELECT
    MIN(created_at)  AS min_created_at,
    MAX(created_at)  AS max_created_at,
    COUNT(*)         AS total_rows
FROM prod_db.postgres_rds_partner_call_log_ivr.partner_call_log
"""

Q_MONTHLY_PCL = """
SELECT
    DATE_TRUNC('month', created_at)::DATE AS month,
    COUNT(*) AS row_count
FROM prod_db.postgres_rds_partner_call_log_ivr.partner_call_log
GROUP BY 1 ORDER BY 1
"""


def run(conn, sql, label):
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    df = pd.read_sql(sql, conn)
    df.columns = [c.lower() for c in df.columns]
    print(df.to_string(index=False))
    return df


def main():
    conn = get_snow_connection()
    assert conn is not None

    mm_uccl   = run(conn, Q_MIN_MAX_UCCL,         "UCCL  -- min/max created_at")
    mon_uccl  = run(conn, Q_MONTHLY_UCCL,         "UCCL  -- monthly volumes + recording fill-rate")
    first_d   = run(conn, Q_DAILY_FIRST_WEEK_UCCL,"UCCL  -- first month, daily granularity")

    mm_pcl    = run(conn, Q_MIN_MAX_PCL,          "PCL   -- min/max created_at (partner_call_log for context)")
    mon_pcl   = run(conn, Q_MONTHLY_PCL,          "PCL   -- monthly volumes")

    # Save tables
    mon_uccl.to_csv(OUT_DIR / "uccl_monthly.csv", index=False)
    first_d.to_csv(OUT_DIR / "uccl_first_month_daily.csv", index=False)
    mon_pcl.to_csv(OUT_DIR / "pcl_monthly.csv", index=False)

    # Headline summary
    mon_uccl["recording_pct"] = (mon_uccl["with_recording"] / mon_uccl["row_count"] * 100).round(1)
    print(f"\n{'=' * 70}\nHEADLINE — UCCL recording fill-rate by month\n{'=' * 70}")
    print(mon_uccl[["month", "row_count", "with_recording", "recording_pct"]].to_string(index=False))

    print(f"\nWROTE:\n  {OUT_DIR/'uccl_monthly.csv'}\n  {OUT_DIR/'uccl_first_month_daily.csv'}\n  {OUT_DIR/'pcl_monthly.csv'}")
    conn.close()


if __name__ == "__main__":
    main()
