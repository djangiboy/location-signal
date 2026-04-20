"""
Database connector template — Rohan / Ryan, copy this file to `db_connectors.py`
in each engine subfolder you run scripts from:

    cp db_connectors.example.py allocation_signal/db_connectors.py
    cp db_connectors.example.py coordination/db_connectors.py
    cp db_connectors.example.py promise_maker_gps/gps_jitter/db_connectors.py
    cp db_connectors.example.py promise_maker_gps/booking_install_distance/db_connectors.py

Then either (a) set the environment variables below, or (b) replace the
os.getenv calls with your own credentials inline. Do NOT commit the filled-in
`db_connectors.py` — it's in .gitignore.

Environment variables expected (set in your shell profile or a local .env):

    GENIE1_USER, GENIE1_PASSWORD, GENIE1_HOST, GENIE1_DATABASE
    GENIE2_USER, GENIE2_PASSWORD, GENIE2_HOST, GENIE2_DATABASE
    CLICKHOUSE_HOST, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD
    SQLSERVER_HOST, SQLSERVER_USER, SQLSERVER_PASSWORD
    SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT, SNOWFLAKE_WAREHOUSE,
      SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA, SNOWFLAKE_PRIVATE_KEY_PATH,
      SNOWFLAKE_PRIVATE_KEY_PASSPHRASE

Ask Maanas for the actual credential values (out-of-band, not over this repo).
"""
import os

import pyodbc
import clickhouse_connect
import snowflake.connector
import mysql.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def get_genie1_server():
    return mysql.connector.connect(
        user=os.environ["GENIE1_USER"],
        password=os.environ["GENIE1_PASSWORD"],
        host=os.environ["GENIE1_HOST"],
        database=os.environ.get("GENIE1_DATABASE", "genie1"),
        port=3306,
    )


def get_genie2_server():
    return mysql.connector.connect(
        user=os.environ["GENIE2_USER"],
        password=os.environ["GENIE2_PASSWORD"],
        host=os.environ["GENIE2_HOST"],
        database=os.environ.get("GENIE2_DATABASE", "genie2"),
    )


def get_happy_connection():
    return mysql.connector.connect(
        user=os.environ["HAPPY_USER"],
        password=os.environ["HAPPY_PASSWORD"],
        host=os.environ["HAPPY_HOST"],
        database=os.environ.get("HAPPY_DATABASE", "happy_main"),
    )


def get_click_db_connection():
    return clickhouse_connect.get_client(
        host=os.environ["CLICKHOUSE_HOST"],
        port=int(os.environ.get("CLICKHOUSE_PORT", 8123)),
        username=os.environ["CLICKHOUSE_USER"],
        password=os.environ["CLICKHOUSE_PASSWORD"],
    )


def _sqlserver_conn(database):
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={os.environ['SQLSERVER_HOST']};"
        f"DATABASE={database};"
        f"UID={os.environ['SQLSERVER_USER']};"
        f"PWD={os.environ['SQLSERVER_PASSWORD']};"
        "TrustServerCertificate=yes;"
    )


def get_i2e1_db_connection():
    return _sqlserver_conn("i2e1")


def get_shard1_db_connection():
    return _sqlserver_conn("shard_01")


def get_master_db_connection():
    return _sqlserver_conn("Master_db")


def get_log_db_connection():
    return _sqlserver_conn("log_db")


def get_snow_connection():
    """Snowflake key-pair auth. Place your PEM-formatted private key at the
    path given by SNOWFLAKE_PRIVATE_KEY_PATH (not in this repo)."""
    key_path = os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]
    passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "")

    with open(key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=passphrase.encode() if passphrase else None,
            backend=default_backend(),
        )

    return snowflake.connector.connect(
        user=os.environ["SNOWFLAKE_USER"],
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        private_key=private_key,
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "DS_MED_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "PROD_DB"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "DS_TABLES"),
    )


if __name__ == "__main__":
    conn = get_snow_connection()
    print("Snowflake connection OK" if conn else "Snowflake connection FAILED")
