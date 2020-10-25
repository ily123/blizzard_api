"""Classes to query and parse World of Warcraft  (WoW) M+ game data.

Blizzard/WoW API docs:
https://develop.battle.net/documentation/world-of-warcraft/game-data-apis
"""
from typing import List, Optional, Tuple, Type

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
    def _send_request(call_url):
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
