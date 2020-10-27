"""Pipeline tasks to get and summarize M+ data.

Example usage:
    import pipeline

    pipeline.get_runs() # scrapes *all* leaderboard endpoints, 15-30 mins
    pipeline.summarize() # goes into MDB and pushes *new* data into summary tables
"""
import sqlite3
import time
from typing import List, Optional

import pandas as pd

import blizz_api
import mplusdb


def find_uniq(existing_ids, runs) -> List[tuple]:
    """Returns records that are novel to MDB."""
    incoming_ids = [run[0] for run in runs]
    new_ids = list(set(incoming_ids) - set(existing_ids))
    new_records = [r for r in runs if r[0] in new_ids]
    return new_records


def get_data(period=None):
    """Scrapes all of M+ leaderboards and inserts new records into MDB."""
    caller = blizz_api.Caller()
    batch_caller = blizz_api.BatchCaller(caller.access_token)  # share the token
    batch_caller.workers = 5

    dungeons = caller.get_dungeons()
    dungeons = [d["id"] for d in dungeons]
    regions = ["us", "eu", "tw", "kr"]
    region_int = {"us": 1, "eu": 3, "kr": 2, "tw": 4}
    mdb = mplusdb.MplusDatabase("config/db_config.ini")
    t0 = time.time()
    print("START CYCLE:")
    for region in regions:
        if not period:
            period = caller.get_current_period(region)
        # peek at what's already present in the db for this period/region
        existing_run_ids = mdb.pull_existing_run_ids(region_int[region], period)
        print("Retrieved existing run ids from MDB for [%s %s]" % (region, period))
        for dungeon in dungeons:
            # point batch caller toward region/period/dungeon endpoints
            batch_caller.region = region
            batch_caller.dungeon = dungeon
            batch_caller.period = period
            runs, rosters = batch_caller.get_data()

            novel_runs = find_uniq(existing_run_ids, runs)
            novel_rosters = find_uniq(existing_run_ids, rosters)
            if len(novel_runs) > 0:
                mdb.insert(table="run", data=novel_runs)
                mdb.insert(table="roster", data=novel_rosters)
            print(
                ("batch call success [%s %s %s]" + " inserted %d new runs into MDB")
                % (region, period, dungeon, len(novel_runs))
            )
    print("END CYCLE, exec time %d seconds" % (time.time() - t0))


def update_mdb_summary() -> None:
    """Updates summary tables in MDB."""
    mdb = mplusdb.MplusDatabase("config/db_config.ini")
    mdb.update_summary_spec_table(period_start=770, period_end=774)
    mdb.update_weekly_top500_table(period_start=773, period_end=773)


def export_mdb_summary() -> None:
    """Exports summary tables in the MDB as sqlite file."""
    mdb = mplusdb.MplusDatabase("config/db_config.ini")
    # runs grouped by spec/level/season
    summary_spec = mdb.get_summary_spec_table_as_df()
    push_summary_spec_to_sqlite(summary_spec)
    # summary counts of specs within top 500 for each dungeon for each period
    weekly_top500_summary = mdb.get_weekly_top500()
    push_weekly_top500_summary_to_sqlite(weekly_top500_summary)


def update_export_summary() -> None:
    """First updates, then exports MDB summary tables as sqlite file."""
    time_start = time.time()
    print("Update/Export started.")
    print("Updating summary_spec and period_rank table....")
    update_mdb_summary()
    print("...done")
    print("Collecting data and exporting to sqlite...")
    export_mdb_summary()
    print("...done")
    print("Update/Export done in %d sec" % (time.time() - time_start))


def connect_to_sqlite(db_file_path: str) -> sqlite3.Connection:
    """Connects to the SQLite DB"""
    conn = None
    try:
        conn = sqlite3.connect(db_file_path)
    except Exception as error:
        print("ERROR CONNECTING TO SQLITE: ", error)
    return conn


def push_summary_spec_to_sqlite(summary_spec: pd.DataFrame) -> None:
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
        summary_spec.values,
    )
    conn.commit()
    conn.close()


def push_weekly_top500_summary_to_sqlite(weekly_top500_summary):
    """Push weekly top 500 runs summary to SQLite db."""
    conn = connect_to_sqlite("data/summary.sqlite")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS weekly_summary")
    cursor.execute(
        """
        CREATE TABLE weekly_summary (
            period integer NOT NULL,
            spec integer NOT NULL,
            run_count integer NOT NULL
        );
        """
    )
    cursor.executemany(
        """
        INSERT INTO weekly_summary(period, spec, run_count)
        VALUES(?,?,?)
        """,
        weekly_top500_summary,
    )
    conn.commit()
    conn.close()
