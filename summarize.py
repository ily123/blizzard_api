"""Summarizes data from the MySQL DB and pipes it into a SQLite file.

This script runs 2 SQL queries aganist the MDB keyruns database, and
summarizes data from the runs table. The first query aggs runs into a
(spec, level, num_runs) summary table. The second query aggs top 500
runs view into a (period, dungeon, spec, num_runs) table.

    Usage:

    run 'python summarize.py' in the command line
"""
import sqlite3
from typing import List, Optional

import mysql.connector
import pandas as pd

import mplusdb


def send_query_to_mdb(query) -> Optional[List[tuple]]:
    """Sends query to MDB."""
    result = None
    mdb = mplusdb.MplusDatabase(".db_config")
    conn = mdb.connect()
    try:
        cursor = conn.cursor()
        cursor.execute("use keyruns")
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
    except Exception as e:
        print("ERROR CONNECTING TO MDB: ", e)
    finally:
        conn.close()
    return result


def get_runs():
    """Aggs runs table by spec/level."""
    query = """
       SELECT spec, level, count(level) FROM
       (SELECT run_id, spec, level FROM new_table INNER JOIN
       roster ON roster.run_id = new_table.id) as J
       GROUP BY spec, level;
    """
    data = send_query_to_mdb(query)
    return data


def get_top_weekly_runs():
    """Aggs runs table by spec/level."""
    query = """
        SELECT period, dungeon, spec, count(spec) FROM period_rank
        LEFT JOIN roster
        ON period_rank.id = roster.run_id
        GROUP BY period, dungeon, spec
    """
    data = send_query_to_mdb(query)
    return data


def connect_to_sqlite(db_file_path: str) -> Optional[sqlite3.Connection]:
    """Connects to the SQLite DB"""
    conn = None
    try:
        conn = sqlite3.connect(db_file_path)
    except Exception as e:
        print("ERROR CONNECTING TO SQLITE: ", e)
    return conn


def push_runs_to_sqlite(runs):
    """Push summary runs data to SQLite db."""
    conn = connect_to_sqlite("data/summary.sqlite")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS main_summary")
    cursor.execute(
        """
        CREATE TABLE main_summary (
            spec integer NOT NULL,
            level integer NOT NULL,
            run_count integer NOT NULL
        );
        """
    )
    cursor.executemany(
        """
        INSERT INTO main_summary(spec, level, run_count)
        VALUES(?,?,?)
        """,
        runs,
    )
    conn.commit()
    conn.close()


def push_weekly_runs_to_sqlite(weekly_runs):
    """Push top 500 runs summary to SQLite db."""
    conn = connect_to_sqlite("data/summary.sqlite")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS weekly_summary")
    cursor.execute(
        """
        CREATE TABLE weekly_summary (
            period integer NOT NULL,
            dungeon integer NOT NULL,
            spec integer NOT NULL,
            run_count integer NOT NULL
        );
        """
    )
    cursor.executemany(
        """
        INSERT INTO weekly_summary(period, dungeon, spec, run_count)
        VALUES(?,?,?,?)
        """,
        weekly_runs,
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    runs = get_runs()
    push_runs_to_sqlite(runs)
    weekly_runs = get_top_weekly_runs()
    push_weekly_runs_to_sqlite(weekly_runs)
