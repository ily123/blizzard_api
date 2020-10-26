"""Pipeline tasks to get and summarize M+ data.

Example usage:
    import pipeline

    pipeline.get_runs() # scrapes *all* leaderboard endpoints, 15-30 mins
    pipeline.summarize() # goes into MDB and pushes *new* data into summary tables
"""
import time
from typing import List

import blizz_api
import mplusdb


def pull_existing_run_ids(mdb, region_: str, period: int) -> List[int]:
    """Pulls id column from the run table in the MDB."""
    conn = mdb.connect()
    region = {"us": 1, "eu": 3, "kr": 2, "tw": 4}[region_]

    run_ids = []
    try:
        cursor = conn.cursor()
        cursor.execute("use keyruns")
        cursor.execute(
            "SELECT id FROM run WHERE region=%s and period=%s" % (region, period)
        )
        run_ids = cursor.fetchall()
        cursor.close()
    except BaseException as error:
        print("Problem fetching ids from MDB: ", str(error))
    finally:
        conn.close()
    # format into list of ints
    run_ids = [int(item[0]) for item in run_ids]
    return run_ids


def find_uniq(existing_ids, runs) -> List[tuple]:
    """Returns records that are novel to MDB."""
    incoming_ids = [run[0] for run in runs]
    new_ids = list(set(incoming_ids) - set(existing_ids))
    new_records = [r for r in runs if r[0] in new_ids]
    return new_records


def get_data(period=None):
    """Scrapes all of M+ leaderboards."""
    caller = blizz_api.Caller()
    batch_caller = blizz_api.BatchCaller(caller.access_token)  # share the token
    batch_caller.workers = 5

    dungeons = caller.get_dungeons()
    dungeons = [d["id"] for d in dungeons]
    regions = ["us", "eu", "tw", "kr"]

    mdb = mplusdb.MplusDatabase("config/db_config.ini")

    print("START CYCLE:")  # airflow assigns timestamps
    for region in regions:
        if not period:
            period = caller.get_current_period(region)
        existing_run_ids = pull_existing_run_ids(
            mdb, region, period
        )  # what's in the DB
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
    print("END CYCLE")
