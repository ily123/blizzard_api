"""Classes to query and parse World of Warcraft  (WoW) M+ game data.

Blizzard/WoW API docs:
https://develop.battle.net/documentation/world-of-warcraft/game-data-apis


Usage example:

    import blizzard_api

    batch_caller = blizzard_api.BatchCaller(api_token)
    batch_caller.region = "us"
    batch_caller.dungeon = 244
    batch_caller.period = 744
    batch_caller.workers = 5
    runs, rosters = batch_caller.get_data()

"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from json import JSONDecodeError
from typing import Generator, List, Optional, Tuple, Type

import requests

import blizz_parser
import blizzard_credentials


def _isvalid(region: str) -> bool:
    """Checks if region string is valid."""
    valid_regions = ["us", "eu", "kr", "tw", "cn"]
    return region.lower() in valid_regions


class UrlFactory:
    """API url call constructor."""

    def __init__(self, access_token: str, region: str) -> None:
        """Inits with API access token and region id.

        Region id must be one of 'us', 'eu', 'kr', 'tw', 'cn'
        """
        if not _isvalid(region):
            raise ValueError("region token must be one of: us, eu, kr, tw, cn")
        self.region = region
        self.access_token = access_token
        self.host = self._get_host(region)
        self.locale = "en_US"  # not entirel sure how this affects calls

    @staticmethod
    def _get_host(region: str) -> str:
        """Constructs regional host name component of the request call."""
        if region == "cn":
            host = "gateway.battlenet.com.cn"
        else:
            host = "{region}.api.blizzard.com".format(region=region)
        return host

    def _get_request_call_url(self, endpoint: str, namespace: str) -> str:
        """Constructs Url of the API request call."""
        template = (
            "https://{host}/{endpoint}?namespace={namespace}&"
            + "locale={locale}&"
            + "access_token={token}"
        )
        call_url = template.format(
            host=self.host,
            endpoint=endpoint,
            namespace=namespace,
            locale=self.locale,
            token=self.access_token,
        )
        return call_url

    def get_connected_realm_index_url(self) -> str:
        """Constucts URL for connected realm index (list) call."""
        endpoint = "data/wow/connected-realm/index"
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self._get_request_call_url(endpoint, namespace)
        return call_url

    def get_connected_realm_url(self, realm_id: int) -> str:
        """Constructs URL for connected realm call."""
        endpoint = "data/wow/connected-realm/{rid}".format(rid=realm_id)
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self._get_request_call_url(endpoint, namespace)
        return call_url

    def get_mythic_plus_leaderboard_url(
        self, dungeon_id: int, realm_id: int, period: int
    ) -> str:
        """Constructs URL for mythic+ leaderboard call."""
        endpoint = (
            "data/wow/connected-realm/{realm}/mythic-leaderboard/"
            "{dungeon}/period/{period}"
        ).format(realm=realm_id, dungeon=dungeon_id, period=period)
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self._get_request_call_url(endpoint, namespace)
        return call_url

    def get_timeperiod_index_url(self) -> str:
        """Constructs URL for timeperiod index call."""
        endpoint = "data/wow/mythic-keystone/period/index"
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self._get_request_call_url(endpoint, namespace)
        return call_url

    def get_timeperiod_url(self, period: int) -> str:
        """Constructs URL for timeperiod call."""
        if period < 641:
            raise ValueError(
                """
                Earliest allowed period in Blizz DB is 641, you entered %d"""
                % period
            )
        endpoint = "/data/wow/mythic-keystone/period/{periodId}".format(periodId=period)
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self._get_request_call_url(endpoint, namespace)
        return call_url

    def get_spec_index_url(self) -> str:
        """Constructs URL for a spec index call."""
        endpoint = "data/wow/playable-specialization/index"
        namespace = "static-{region}".format(region=self.region)
        call_url = self._get_request_call_url(endpoint, namespace)
        return call_url

    def get_spec_url(self, spec_id: int) -> str:
        """Constructs URL for spec call."""
        endpoint = "data/wow/playable-specialization/{spec_id}".format(spec_id=spec_id)
        namespace = "static-{region}".format(region=self.region)
        call_url = self._get_request_call_url(endpoint, namespace)
        return call_url

    def get_dungeon_index_url(self) -> str:
        """Constructs URL for dungeons index call."""
        endpoint = "data/wow/mythic-keystone/dungeon/index"
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self._get_request_call_url(endpoint, namespace)
        return call_url


class Caller:
    """Abstracts API interactions into a high-level interface."""

    _default_access_token_fp = "config/blizzard_api_access.ini"

    def __init__(self, access_token: Optional[str] = None) -> None:
        """Inits wtih access token. If token not given, tries to get one."""
        if not access_token:
            auth = blizzard_credentials.Credentials(self._default_access_token_fp)
            access_token = auth.access_token
        self.access_token = access_token
        if not self.access_token:
            raise ValueError(
                """Caller needs a valid access token
                to query Blizzard API"""
            )

    @staticmethod
    def _send_request(call_url) -> requests.Response:
        """Sends URL request to Blizzard API."""
        response = requests.get(call_url)
        response.raise_for_status()  # catches 4xx and 5xx codes
        if response.status_code != 200:  # if something non-obvious happened
            raise Exception(
                "Call not successful [status code %s]: %s"
                % (response.status_code, call_url)
            )
        return response

    def get_spec_ids(self) -> List[dict]:
        """Gets list of spec ids and names."""
        region = "us"
        url_factory = UrlFactory(self.access_token, region)
        url = url_factory.get_spec_index_url()
        response = self._send_request(url)
        json = response.json()
        specs = blizz_parser.parse_spec_index_json(json)
        return specs

    def get_spec_by_id(self, spec_id: int) -> dict:
        """Gets full spec info given spec id."""
        region = "us"
        url_factory = UrlFactory(self.access_token, region)
        url = url_factory.get_spec_url(spec_id)
        response = self._send_request(url)
        spec_info = blizz_parser.parse_spec_json(response.json())
        return spec_info

    def get_class_spec_table(self) -> List[dict]:
        """Gets table of playable classes and specs."""
        class_spec_table = []
        specs = self.get_spec_ids()
        for spec in specs:
            spec_info = self.get_spec_by_id(spec["spec_id"])
            class_spec_table.append(spec_info)
        return class_spec_table

    def get_leaderboard(
        self, region: str, realm: int, dungeon: int, period: int
    ) -> Type[blizz_parser.KeyRunLeaderboard]:
        """Gets leaderboard for specified region/realm/dungeon/period."""
        url_factory = UrlFactory(self.access_token, region)
        call_url = url_factory.get_mythic_plus_leaderboard_url(
            dungeon_id=dungeon, realm_id=realm, period=period
        )
        response = self._send_request(call_url)
        leaderboard = blizz_parser.KeyRunLeaderboard(response.json())
        return leaderboard

    def get_period_ids(self, region: str) -> List[int]:
        """Gets list of m+ period ids for region."""
        url_factory = UrlFactory(self.access_token, region)
        period_index_url = url_factory.get_timeperiod_index_url()
        response = requests.get(period_index_url)
        periods = blizz_parser.parse_timeperiod_index_json(response.json())
        return periods

    def get_current_period(self, region: str) -> int:
        """Gets current m+ period for region."""
        periods = self.get_period_ids(region=region)
        current_period = max(periods)
        return current_period

    def get_period_startend(self, region: str, period: int) -> Tuple[int, int]:
        """Gets start and end timestamp for period."""
        url_factory = UrlFactory(self.access_token, region)
        period_url = url_factory.get_timeperiod_url(period)
        response = requests.get(period_url)
        start, end = blizz_parser.parse_timeperiod_json(response.json())
        return start, end

    def get_dungeons(self) -> List[dict]:
        """Gets list of dungeon ids.

        Warning: only returns data for current expansion.
        """
        url_factory = UrlFactory(self.access_token, region="us")
        dungeon_index_url = url_factory.get_dungeon_index_url()
        response = requests.get(dungeon_index_url)
        dungeons = blizz_parser.parse_dungeon_index_json(response.json())
        return dungeons

    def get_connected_realm_ids(self, region: str) -> List[int]:
        """Gets list of connected realm ids for region."""
        url_factory = UrlFactory(self.access_token, region=region)
        realm_index_url = url_factory.get_connected_realm_index_url()
        response = requests.get(realm_index_url)
        realm_ids = blizz_parser.parse_connected_realm_index_json(response.json())
        return realm_ids

    def get_connected_realm(self, region: str, realm_id: int) -> List[dict]:
        """Gets info for a shard given its id and region."""
        url_factory = UrlFactory(self.access_token, region=region)
        realm_url = url_factory.get_connected_realm_url(realm_id=realm_id)
        response = requests.get(realm_url)
        # "connected" realms correspond to a cluster of realms
        # that used to be stand-alone but got merged; some "connected"
        # realms only contain 1 realm (never merged)
        # Anyway, this is what the line below returns a list
        realms_in_cluster = blizz_parser.parse_connected_realm_json(response.json())
        return realms_in_cluster

    def get_connected_realms(self, region: str) -> List[dict]:
        """Gets full info for all of region's shards."""
        cluster_ids = self.get_connected_realm_ids(region="us")
        realms = []
        for cluster_id in cluster_ids:
            realms_in_cluster = self.get_connected_realm(
                region=region, realm_id=cluster_id
            )
            realms.extend(realms_in_cluster)
        return realms


class BatchCaller(Caller):
    """Collects region-wider leaderboard for a dungeon using parallel calls.

    Attributes needs to be set after object is created.

    Attributes
    ----------
        region : str
            region one of "us", "eu", "kr", "tw"
        dungeon : int
            a valid dungeon id
        period : int
            a valid period id
        workers : int
            number of threads to spawn (ex: 5)
    """

    def __init__(self, access_token: str) -> None:
        """Inits with access token."""
        super().__init__(access_token)
        # these need to be set using normal attribute syntax
        # (I don't want to mess with setters - just get this done)
        # these are just some valid place holders
        self.region = "us"
        self.dungeon = 244
        self.period = 733
        self.workers = 2

    def _get_leaderboard_urls(self) -> List[str]:
        """Constructs dungeon leaderboard call URL for every realm in region."""
        realm_ids = self.get_connected_realm_ids(region=self.region)
        url_factory = UrlFactory(region=self.region, access_token=self.access_token)
        realm_urls = []
        for realm_id in realm_ids:
            url = url_factory.get_mythic_plus_leaderboard_url(
                dungeon_id=self.dungeon, realm_id=realm_id, period=self.period
            )
            realm_urls.append(url)
        return realm_urls

    @staticmethod
    def _parse_responses(responses) -> Tuple[List[tuple], List[tuple]]:
        """Parses jons and aggs runs and rosters into a list of tuples."""
        runs = []
        rosters = []
        for resp in responses:
            try:
                leaderboard = blizz_parser.KeyRunLeaderboard(resp.json())
                runs.extend(leaderboard.get_runs_as_tuple_list())
                rosters.extend(leaderboard.get_rosters_as_tuple_list())
            except JSONDecodeError as error:
                print("Leaderboard parse error: JSONDecodeError ", error)
            except KeyError as error:
                print("Leaderboard parse error: KeyError", error)
        # the same run can appear on multiple realm leaderboards, so uniq the data
        runs = list(set(runs))
        rosters = list(set(rosters))
        return runs, rosters

    def get_data(self) -> Tuple[List[tuple], List[tuple]]:
        """Collects run data from all regional realms in parallel.

        Returns
        -------
            runs
                list of runs as list of tuples
            rosters
                list of player characters as list of tuples
        """
        urls = self._get_leaderboard_urls()
        responses = _multi_threaded_call(urls, self.workers)
        runs, rosters = self.parse_responses(responses)
        return runs, rosters


def _multi_threaded_call(urls, num_threads) -> List[requests.Response]:
    """Sends multiple calls to the API at once."""

    # chunk the urls into pieces with 10 urls each
    url_chunks = _divide_chunks(urls, num_threads)

    threads = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        for chunk in url_chunks:
            threads.append(executor.submit(_api_call, chunk))
    responses = []
    for task in as_completed(threads):
        responses.extend(task.result())
    return responses


def _api_call(urls) -> List[requests.Response]:
    """Calls urls in a requests session."""
    responses = []
    with requests.Session() as session:
        for url in urls:
            try:
                response = session.get(url, timeout=5)
                response.raise_for_status()
            # this exception is lazy, but we call this script hundreds of times per week
            # so if a request fails, we'll get the data next time around
            except Exception as error:
                print("Request [%s] failed with error [%s]" % (url, error))
                continue
            responses.append(response)
    return responses


def _divide_chunks(list_, n) -> Generator:
    """Divide list into chunks of size n."""
    for i in range(0, len(list_), n):
        yield list_[i : i + n]
