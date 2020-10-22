"""Summarizes data from the MySQL DB and pipes it into a SQLite file.

This script runs 2 SQL queries aganist the MDB keyruns database, and
summarizes data from the runs table. The first query aggs runs into a
(spec, level, num_runs) summary table. The second query aggs top 500
runs view into a (period, dungeon, spec, num_runs) table.

    Usage:

    run 'python summarize.py' in the command line
"""
import sqlite3
import time
from typing import List, Optional

import mysql.connector
import pandas as pd

import mplusdb


def send_query_to_mdb(query, isfetch=False) -> Optional[List[tuple]]:
    """Sends query to MDB."""
    result = None
    mdb = mplusdb.MplusDatabase("config/db_config.ini")
    conn = mdb.connect()
    try:
        cursor = conn.cursor()
        cursor.execute("use keyruns")
        cursor.execute(query)
        if isfetch:
            result = cursor.fetchall()
        conn.commit()
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
       (SELECT run_id, spec, level FROM run INNER JOIN
       roster ON roster.run_id = run.id) as J
       GROUP BY spec, level;
    """
    data = send_query_to_mdb(query, isfetch=True)
    return data


def update_runs_summary(period1: int, period2: int):
    """Updates summary table with data from [period1 to period2]."""
    update_query = """
        INSERT INTO summary_spec
        SELECT period, spec, level, count(level) as count
        FROM run
        INNER JOIN roster on run.id = roster.run_id
        WHERE run.period BETWEEN %d AND %d
        GROUP BY period, spec, level
        ON DUPLICATE KEY UPDATE count=VALUES(count);
    """
    update_query = update_query % (period1, period2)
    result = send_query_to_mdb(update_query)
    return result


def get_runs_summary():
    """Aggs summary runs table by spec/level/season."""
    query = """
       SELECT * from summary_spec;
    """
    data = send_query_to_mdb(query, isfetch=True)
    df = pd.DataFrame(data, columns=["period", "spec", "level", "count"])
    df["season"] = "unknown"
    df.loc[(df.period) >= 734 & (df.period <= 771), "season"] = "bfa4"
    df.loc[df.period >= 772, "season"] = "bfa4_postpatch"
    dfg = (
        df[["season", "spec", "level", "count"]]
        .groupby(["season", "spec", "level"])
        .sum()
    )
    dfg.reset_index(inplace=True)
    return dfg


def push_runs_summary_to_sqlite(runs):
    """Push season-delimited summary of runs data to SQLite db."""
    conn = connect_to_sqlite("data/summary.sqlite")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS main_summary_seasons")
    cursor.execute(
        """
        CREATE TABLE main_summary_seasons (
            season varchar NOT NULL,
            spec integer NOT NULL,
            level integer NOT NULL,
            run_count integer NOT NULL
        );
        """
    )
    cursor.executemany(
        """
        INSERT INTO main_summary_seasons(season, spec, level, run_count)
        VALUES(?,?,?,?)
        """,
        runs.values,
    )
    conn.commit()
    conn.close()


def get_top_weekly_runs():
    """Aggs runs table by spec/level."""
    query = """
        SELECT period, dungeon, spec, count(spec) FROM period_rank
        LEFT JOIN roster
        ON period_rank.id = roster.run_id
        GROUP BY period, dungeon, spec
    """
    data = send_query_to_mdb(query, isfetch=True)
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
    # runs = get_runs()
    # push_runs_to_sqlite(runs)
    t0 = time.time()
    update_runs_summary(770, 775)
    runs_summary = get_runs_summary()
    print("Updated runs summary table in ", time.time() - t0)
    push_runs_summary_to_sqlite(runs_summary)
    print("Pushed summary table to SQLite file")

    t1 = time.time()
    weekly_runs = get_top_weekly_runs()
    print("Calculated weekly dungeon 500 in ", time.time() - t1)
    push_weekly_runs_to_sqlite(weekly_runs)
    print("Pushed weekly summary to SQLite file")
