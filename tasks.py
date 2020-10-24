"""Python methods for running ETL tasks."""
import importlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from json import JSONDecodeError
from typing import Tuple

import requests

import blizzard_api
import blizzard_credentials
import mplusdb

importlib.reload(mplusdb)
importlib.reload(blizzard_api)
mdb = mplusdb.MplusDatabase("config/db_config.ini")


def get_access_token():
    """Get OAuth access tokens."""
    cred = blizzard_credentials.Credentials("config/blizzard_api_access.ini")
    return cred.access_token


def get_leaderboard_urls(region, period, dungeon):
    """Constructs dungeon leaderboard call URL for every realm in region."""
    caller = blizzard_api.Caller()
    realm_ids = caller.get_connected_realm_ids(region=region)
    url_factory = blizzard_api.UrlFactory(
        region=region, access_token=get_access_token()
    )
    realm_urls = []
    for realm_id in realm_ids:
        url = url_factory.get_mythic_plus_leaderboard_url(
            dungeon_id=dungeon, realm_id=realm_id, period=period
        )
        realm_urls.append(url)
    return realm_urls


def get_data(region, period, dungeon):
    """Get region-wide agg of leaderboards for dungeon."""
    urls = get_leaderboard_urls(region, period, dungeon)
    responses = multi_threaded_call(urls)
    return responses


def api_call(urls):
    """Calls urls in a requests session."""
    responses = []
    with requests.Session() as session:
        for url in urls:
            try:
                response = session.get(url, timeout=5)
            except:
                response = session.get(url, timeout=5)
            responses.append(response)
    return responses


def divide_chunks(list_, n):
    """Divide list into chunks of size n."""
    for i in range(0, len(list_), n):
        yield list_[i : i + n]


def multi_threaded_call(urls):
    """Sends multiple calls to the API at once."""

    # chunk the urls into pieces with 10 urls each
    url_chunks = divide_chunks(urls, 10)

    threads = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for chunk in url_chunks:
            threads.append(executor.submit(api_call, chunk))
    responses = []
    for task in as_completed(threads):
        responses.extend(task.result())
    return responses


def parse_responses(responses):
    """Parses leaderboard jsons and aggs them into a single list of key runs."""

    runs = []
    rosters = []

    for resp in responses:
        try:
            leaderboard = blizzard_api.KeyRunLeaderboard(resp.json())
            runs.extend(leaderboard.get_runs_as_tuple_list())
            rosters.extend(leaderboard.get_rosters_as_tuple_list())
        except JSONDecodeError as e:
            print("Leaderboard parse error: JSONDecodeError ", e)
        except KeyError as e:
            print("Leaderboard parse error: KeyError", e)
    # the same run appears in multiple leaderboards, so uniq the data
    runs = list(set(runs))
    rosters = list(set(rosters))
    return runs, rosters


def pull_existing_run_ids(region, period):
    """Pulls id column from the run table in the MDB."""
    run_ids = []
    conn = mdb.connect()
    region = {"us": 1, "eu": 3, "kr": 2, "tw": 4}[region]
    try:
        cursor = conn.cursor()
        cursor.execute("use keyruns")
        cursor.execute(
            "SELECT id FROM run WHERE region=%s and period=%s" % (region, period)
        )
        run_ids = cursor.fetchall()
        cursor.close()
    except BaseException as e:
        print("Problem fetching ids from MDB: ", str(e))
    finally:
        conn.close()
    # format into list of ints
    run_ids = [int(item[0]) for item in run_ids]
    return run_ids


def find_uniq(existing_ids, runs):
    """find novel runs"""
    incoming_ids = [run[0] for run in runs]
    new_ids = list(set(incoming_ids) - set(existing_ids))
    new_records = [r for r in runs if r[0] in new_ids]
    return new_records


def main_method(period=None):
    """blah"""
    caller = blizzard_api.Caller()
    dungeons = caller.get_dungeons()
    regions = ["us", "eu", "tw", "kr"]
    # regions = ["eu"]
    # dungeons = [244]
    for region in regions:
        if not period:
            period = caller.get_current_period(region)
        print("period %s, region %s" % (period, region))
        t0 = time.time()
        existing_run_ids = pull_existing_run_ids(region, period)  # what's in the DB
        print("getting DB data: ", time.time() - t0)
        for dungeon in dungeons:
            t0 = time.time()
            responses = get_data(region=region, period=period, dungeon=dungeon["id"])
            runs, rosters = parse_responses(responses)
            print("API calls: ", time.time() - t0)
            print("Total runs: ", len(runs))
            t0 = time.time()
            novel_runs = find_uniq(existing_run_ids, runs)
            novel_rosters = find_uniq(existing_run_ids, rosters)
            print("Find new runs: ", time.time() - t0)
            print("New runs: ", len(novel_runs))
            t0 = time.time()
            if len(novel_runs) > 0:
                mdb.insert(table="run", data=novel_runs)
                mdb.insert(table="roster", data=novel_rosters)
            print("Inserting new runs: ", time.time() - t0)
            print("-next-" * 5)
        print("=" * 30)
