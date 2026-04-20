"""
Probe script — t_partner / t_active_base / t_node_splitter_gs
==============================================================
Before we merge partner tenure + splitter-vs-active-base mix into our
cohort, inspect each source table to understand:
  - Columns available
  - Grain (what's the natural primary key?)
  - Uniqueness of partner_id
  - Count + time range
  - Sample rows

Three tables:
  1. t_partner           (genie2 MySQL) -- for partner_added_time
  2. t_active_base       (genie2 MySQL) -- for partner-level active-base footprint
  3. t_node_splitter_gs  (Snowflake, prod_db.ds_tables) -- splitter submissions

Output goes to investigative/probe_summary.txt for reuse.
Not wired into any other script.
"""

from pathlib import Path
from datetime import datetime

from db_connectors import get_genie2_server, get_snow_connection


HERE = Path(__file__).resolve().parent
INV = HERE / "investigative"
INV.mkdir(exist_ok=True)
OUT_TXT = INV / "probe_summary.txt"


def section(label, lines):
    lines.append("\n" + "=" * 80)
    lines.append(label)
    lines.append("=" * 80)


def run_g2_query(conn, sql, label, lines):
    lines.append(f"\n-- {label}")
    lines.append(f"-- SQL: {sql.strip()}")
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        cur.close()
        lines.append(f"-- COLUMNS ({len(cols)}): {cols}")
        lines.append(f"-- ROW COUNT RETURNED: {len(rows)}")
        for r in rows[:10]:
            lines.append(f"  {r}")
        return rows, cols
    except Exception as e:
        lines.append(f"-- ERROR: {e}")
        return None, None


def run_snow_query(conn, sql, label, lines):
    lines.append(f"\n-- {label}")
    lines.append(f"-- SQL: {sql.strip()}")
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        cur.close()
        lines.append(f"-- COLUMNS ({len(cols)}): {cols}")
        lines.append(f"-- ROW COUNT RETURNED: {len(rows)}")
        for r in rows[:10]:
            lines.append(f"  {r}")
        return rows, cols
    except Exception as e:
        lines.append(f"-- ERROR: {e}")
        return None, None


def main():
    lines = [f"PROBE RUN: {datetime.now():%Y-%m-%d %H:%M:%S}"]

    # ---------------- GENIE2 MYSQL ----------------
    section("1. t_partner (genie2 MySQL)", lines)
    g2 = get_genie2_server()
    try:
        run_g2_query(g2, "SHOW COLUMNS FROM t_partner", "schema", lines)
        run_g2_query(g2, "SELECT COUNT(*) AS total_rows, COUNT(DISTINCT partner_id) AS distinct_partners FROM t_partner", "row count + distinct partners", lines)
        run_g2_query(g2, "SELECT * FROM t_partner LIMIT 3", "sample rows", lines)
    finally:
        pass  # close at end

    # ---------------- T_ACTIVE_BASE ----------------
    section("2. t_active_base (genie2 MySQL)", lines)
    try:
        run_g2_query(g2, "SHOW COLUMNS FROM t_active_base", "schema", lines)
        run_g2_query(g2, "SELECT COUNT(*) AS total_rows, COUNT(DISTINCT partner_id) AS distinct_partners FROM t_active_base", "row count + distinct partners", lines)
        run_g2_query(g2, "SELECT * FROM t_active_base LIMIT 3", "sample rows", lines)
    finally:
        g2.close()

    # ---------------- SNOWFLAKE ----------------
    section("3. t_node_splitter_gs (Snowflake, prod_db.ds_tables)", lines)
    snow = get_snow_connection()
    if snow is None:
        lines.append("-- Snowflake connection failed. Skipping.")
    else:
        try:
            run_snow_query(snow, "DESC TABLE prod_db.ds_tables.t_node_splitter_gs", "schema", lines)
            run_snow_query(snow, "SELECT COUNT(*) AS total_rows FROM prod_db.ds_tables.t_node_splitter_gs", "row count", lines)
            run_snow_query(snow, "SELECT * FROM prod_db.ds_tables.t_node_splitter_gs LIMIT 3", "sample rows", lines)
        finally:
            snow.close()

    OUT_TXT.write_text("\n".join(str(x) for x in lines))
    print(f"SAVED: {OUT_TXT}")
    print("\n".join(str(x) for x in lines[-80:]))


if __name__ == "__main__":
    main()
