"""Pipeline tasks to get and summarize M+ data.

Example usage:
    import pipeline

    pipeline.get_runs() # scrapes *all* leaderboard endpoints, 15-30 mins
    pipeline.summarize() # goes into MDB and pushes *new* data into summary tables
"""
import sqlite3
import time
from typing import List, Optional, Tuple

import pandas as pd

import blizz_api
import mplusdb


def find_uniq(existing_ids, runs) -> List[tuple]:
    """Returns records that are novel to MDB."""
    incoming_ids = [run[0] for run in runs]
    new_ids = list(set(incoming_ids) - set(existing_ids))
    new_records = [r for r in runs if r[0] in new_ids]
    return new_records


def get_data():
    """Scrapes all of M+ leaderboards and inserts new records into MDB."""
    caller = blizz_api.Caller()
    batch_caller = blizz_api.BatchCaller(caller.access_token)  # share the token
    batch_caller.workers = 6
    print(batch_caller.workers)

    dungeons = caller.get_dungeons()
    dungeons = [d["id"] for d in dungeons]
    regions = ["us", "eu", "tw", "kr"]
    region_int = {"us": 1, "eu": 3, "kr": 2, "tw": 4}
    mdb = mplusdb.MplusDatabase("config/db_config.ini")
    cycle_start = time.time()
    print("START CYCLE:")
    for region in regions:
        period = caller.get_current_period(region)
        # peek at what's already present in the db for this period/region
        existing_run_ids = mdb.pull_existing_run_ids(region_int[region], period)
        print("Retrieved existing run ids from MDB for [%s %s]" % (region, period))
        for dungeon in dungeons:
            # point batch caller toward region/period/dungeon endpoints
            batch_caller.region = region
            batch_caller.dungeon = dungeon
            batch_caller.period = period

            calls_start = time.time()
            runs, rosters = batch_caller.get_data()
            novel_runs = find_uniq(existing_run_ids, runs)
            novel_rosters = find_uniq(existing_run_ids, rosters)
            calls_end = time.time()

            insert_start = time.time()
            if len(novel_runs) > 0:
                mdb.insert(table="run", data=novel_runs)
                mdb.insert(table="roster", data=novel_rosters)
            insert_end = time.time()
            print(
                (
                    "batch call (%d sec) success [%s %s %s]"
                    + " got %d total runs, inserted %d new runs (%d sec) into MDB"
                )
                % (
                    calls_end - calls_start,
                    region,
                    period,
                    dungeon,
                    len(runs),
                    len(novel_runs),
                    insert_end - insert_start,
                )
            )
    print("END CYCLE, exec time %d seconds" % (time.time() - cycle_start))


def update_mdb_summary() -> None:
    """Updates summary tables in MDB."""
    caller = blizz_api.Caller()
    us_current_period = caller.get_current_period("us")
    # different regions roll into new period (reset) at
    # different times. So on Tue/Wed the regions are in
    # different time periods, and US is the first to roll over.
    # So we will regenerate the summary table for all data from
    # [US current period] & [US current period - 1] to account for
    # this period overlap
    start = us_current_period - 1
    end = us_current_period
    mdb = mplusdb.MplusDatabase("config/db_config.ini")
    mdb.update_summary_spec_table(period_start=start, period_end=end)
    mdb.update_weekly_top500_table(period_start=start, period_end=end)


def export_mdb_summary() -> None:
    """Exports summary tables in the MDB as sqlite file."""
    mdb = mplusdb.MplusDatabase("config/db_config.ini")
    # runs grouped by spec/level/season
    summary_spec = mdb.get_summary_spec_table_as_df()
    push_summary_spec_to_sqlite(summary_spec)
    # summary counts of specs within top 500 for each dungeon for each period
    weekly_top500_summary = mdb.get_weekly_top500()
    push_weekly_top500_summary_to_sqlite(weekly_top500_summary)

    # This module needs to be refactored.
    # For now, I hard code the period for SL season 1 (780,...)
    # I don't know when the season ends, so period end is 10,000
    comp_data = mdb.get_composition_data(period_start=770, period_end=10000)
    push_comp_data_to_sqlite(comp_data)

    # get activity data and push to SQLite
    runs_per_period = mdb.get_activity_data()
    push_activity_data_to_sqlite(runs_per_period)


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


def push_activity_data_to_sqlite(activity: List[Tuple[int, int]]) -> None:
    """Push activity data to sqlite.

    Parameter
    ---------
    activity : List[Tuple[int, int]]
        List of (period, number key runs) tuples.
    """
    conn = connect_to_sqlite("data/summary.sqlite")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS activity")
    cursor.execute(
        """
        CREATE TABLE activity(
            period integer NOT NULL,
            run_count integer NOT NULL
        );
        """
    )
    cursor.executemany(
        """
        INSERT INTO activity(period, run_count)
        VALUES(?,?)
        """,
        activity,
    )
    conn.commit()
    conn.close()


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


def push_comp_data_to_sqlite(data: List[Tuple[str, int, float, float, int]]) -> None:
    """Pushes composition data to SQLite db.

    Parameters
    ----------
    data : List[tuple(str, int, float, float, int)]
        list of tuples with comp data, including tokenized comp name
        the number of runs, and average and std dev of the run key levels
    """
    conn = connect_to_sqlite("data/summary.sqlite")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS composition")
    cursor.execute(
        """
        CREATE TABLE composition(
            composition text NOT NULL,
            run_count integer NOT NULL,
            level_mean real NOT NULL,
            level_std real NOT NULL,
            level_max integer NOT NULL
        );
        """
    )
    cursor.executemany(
        """
        INSERT INTO composition(composition, run_count, level_mean, level_std, level_max)
        VALUES(?,?,?,?,?)
        """,
        data,
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    get_data()
    update_export_summary()
