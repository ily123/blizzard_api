"""Python methods for running ETL tasks."""

import importlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple

import requests

import blizzard_api
import blizzard_credentials
import mplusdb

importlib.reload(mplusdb)
importlib.reload(blizzard_api)
mdb = mplusdb.MplusDatabase(".db_config")


def get_access_token():
    auth = blizzard_credentials.Credentials(".api_tokens")
    return auth.access_token


def get_leaderboard_urls(region, period, dungeon):
    """Constructs dungeon leaderboard call URL for every realm in region."""
    caller = blizzard_api.Caller()
    realms = caller.get_connected_realms(region=region)
    url_factory = blizzard_api.UrlFactory(
        region=region, access_token=get_access_token()
    )
    realm_urls = []
    for realm in realms:
        url = url_factory.get_mythic_plus_leaderboard_url(
            dungeon_id=dungeon, realm_id=realm, period=period
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
    with ThreadPoolExecutor(max_workers=8) as executor:
        for chunk in url_chunks:
            threads.append(executor.submit(api_call, chunk))
    responses = []
    for task in as_completed(threads):
        responses.extend(task.result())
    return responses


def parse_responses(responses):
    """Parses leaderboard jsons and aggs them into a single list of key runs."""
    parser = blizzard_api.ResponseParser()

    runs = []
    rosters = []

    for resp in responses:
        # try:
        leaderboard = parser.parse_keyrun_leaderboard_json(resp.json())
        new_runs = leaderboard.get_runs_as_tuple_list()
        print(len(new_runs))
        runs.extend(leaderboard.get_runs_as_tuple_list())
        rosters.extend(leaderboard.get_rosters_as_tuple_list())
    # except BaseException as e:
    #    print("hey, there was a mistake parsing LB resps: ", e)
    # the same run appears in multiple leaderboards, so uniq the data
    runs = list(set(runs))
    rosters = list(set(rosters))
    return runs, rosters


def main_method():
    """blah"""
    caller = blizzard_api.Caller()
    dungeons = caller.get_dungeons()
    period = caller.get_current_period("us")
    regions = ["us", "eu", "tw", "kr"]
    for region in regions:
        period = caller.get_current_period(region)
        print(period)
        for dungeon in dungeons:
            responses = get_data(region=region, period=period, dungeon=dungeon)
            runs, rosters = parse_responses(responses)
            mdb.insert(table="new_table", data=runs)
            mdb.insert(table="roster", data=rosters)
            xxx
