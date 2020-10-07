"""Classes to query and parse World of Warcraft  (WoW) M+ game data.

Blizzard/WoW API docs:
https://develop.battle.net/documentation/world-of-warcraft/game-data-apis
"""
import importlib
import re

import requests

import blizzard_credentials
import utils
from utils import Utils

importlib.reload(utils)

SPEC_UTILS = utils.Specs()
SCORER = utils.Scorer()


class UrlFactory:
    """API url call constructor."""

    def __init__(self, access_token, region):
        """Inits with access token.

        Token is generated via _XXX_ call.
        """
        self.access_token = access_token
        self.host = self.get_host(region)
        self.region = region
        self.locale = "en_US"

    @staticmethod
    def get_host(region):
        """Constucts host name component of the request call."""
        if region == "cn":
            host = "gateway.battlenet.com.cn"
        elif region in ["us", "eu", "kr", "tw"]:
            host = "{region}.api.blizzard.com".format(region=region)
        else:
            raise ValueError("region token must be one of: us, eu, kr, tw, cn")
        return host

    def get_request_call_url(self, endpoint, namespace):
        """Constructs request call from endpoint and params."""
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

    def get_connected_realm_index_url(self):
        """Constucts API call to get list of individual realm calls."""
        endpoint = "data/wow/connected-realm/index"
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self.get_request_call_url(endpoint, namespace)
        return call_url

    def get_connected_realm_call(self, realm_id):
        """Constructs call for a given connected realm."""
        endpoint = "data/wow/connected-realm/{rid}".format(rid=realm_id)
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self.get_request_call_url(endpoint, namespace)
        return call_url

    def get_mythic_plus_leaderboard_url(self, dungeon_id, realm_id, period):
        """Constructs call to mythic+ leaderboard."""
        endpoint = (
            "data/wow/connected-realm/{realm}/mythic-leaderboard/"
            "{dungeon}/period/{period}"
        ).format(realm=realm_id, dungeon=dungeon_id, period=period)
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self.get_request_call_url(endpoint, namespace)
        return call_url

    def get_timeperiod_index_url(self):
        """Constructs url for timeperiod index call."""
        endpoint = "data/wow/mythic-keystone/period/index"
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self.get_request_call_url(endpoint, namespace)
        return call_url

    def get_timeperiod_url(self, period):
        """Constructs url for time period call."""
        if period < 641:
            raise ValueError(
                """
                Earliest allowed period in Blizz DB is 641, you entered %d"""
                % period
            )
        endpoint = "/data/wow/mythic-keystone/period/{periodId}".format(periodId=period)
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self.get_request_call_url(endpoint, namespace)
        return call_url

    def get_spec_index_url(self):
        """Returns indices of playable specializations."""
        endpoint = "data/wow/playable-specialization/index"
        namespace = "static-{region}".format(region=self.region)
        call_url = self.get_request_call_url(endpoint, namespace)
        return call_url

    def get_spec_url(self, spec_id):
        """Return url for playable spec call."""
        endpoint = "data/wow/playable-specialization/{spec_id}".format(spec_id=spec_id)
        namespace = "static-{region}".format(region=self.region)
        call_url = self.get_request_call_url(endpoint, namespace)
        return call_url

    def get_dungeon_index_url(self):
        """Returns indices of current patch dungeons."""
        endpoint = "data/wow/mythic-keystone/dungeon/index"
        namespace = "dynamic-{region}".format(region=self.region)
        call_url = self.get_request_call_url(endpoint, namespace)
        return call_url


class ResponseParser:
    """Parse Blizzard response Json."""

    def __init__(self, json=None):
        """Inits with rolled-up json string."""
        if json:
            self.json = json

    def parse_timeperiod_index_json(self, json):
        """Retrieves time period ids from periond index call json."""
        period_ids = []
        for period in json["periods"]:
            period_ids.append(period["id"])
        return period_ids

    def parse_timeperiod_json(self, json):
        """Retrieves start and end timestamps from period json."""
        start = json["start_timestamp"]
        end = json["end_timestamp"]
        return [start, end]

    def parse_connected_realm_index_json(self, json):
        """Unrolls json from a connected realm index call."""
        if not json["connected_realms"]:
            raise ("connected realms index json is empty")
        # the json supplies list of url calls to individual realms
        # we just want the realm ids contained in the urls
        realm_urls = [realm["href"] for realm in json["connected_realms"]]
        realm_ids = []
        for realm_url in realm_urls:
            realm_ids.append(self.get_realm_id_from_url(realm_url))
        return realm_ids

    def parse_connected_realm_json(self, json):
        """Parses connected realm call json output."""
        realms = []
        for realm_json in json["realms"]:
            realm = RealmRecord(realm_json)
            realms.append(realm)
        return realms

    @staticmethod
    def get_realm_id_from_url(connected_realm_url):
        """Parsess realm ID from the json."""
        cap = re.findall("connected-realm\/(\d+)\?", connected_realm_url)
        realm_id = cap[0]
        return realm_id

    @staticmethod
    def parse_keyrun_leaderboard_json(json):
        """Parses the key run leaderboard of the json."""
        leaderboard = KeyRunLeaderboard(json)
        return leaderboard

    @staticmethod
    def parse_spec_index_json(json):
        """Parses spec index call response."""
        specs = []
        for spec in json["character_specializations"]:
            id_ = spec["id"]
            name = spec["name"]
            specs.append((id_, name))
        return specs

    @staticmethod
    def parse_spec_json(json):
        """Parses playable spec json."""
        spec_id = json["id"]
        spec_name = json["name"].lower()
        class_id = json["playable_class"]["id"]
        class_name = json["playable_class"]["name"].lower()
        role = json["role"]["type"].lower()
        spec_info = [class_name, class_id, spec_name, spec_id, role]
        return spec_info

    @staticmethod
    def parse_dungeon_index_json(json):
        """Parses current dungeons index json."""
        dungeon_ids = []
        for dungeon in json["dungeons"]:
            dungeon_ids.append(dungeon["id"])
        return dungeon_ids


class KeyRunLeaderboard:
    """Container/parser for Key Run leaderboard."""

    __sql_value_template = (
        "("
        "{run_id},{dungeon},{key_level},{period},"
        "{completed_timestamp},{duration_in_ms},"
        "{faction},{region}"
        ")"
    )
    __destination_table = "run"

    def __init__(self, json):
        self.json = json
        self.get_meta_features()
        self.keyruns = self.parse_key_runs()

    def get_meta_features(self):
        """Extracts leaderboard regon-level data."""
        self.api_call_url = self.json["_links"]["self"]["href"]
        self.period = self.json["period"]
        self.realm = Utils().get_realm_id_from_url(self.json["connected_realm"]["href"])
        self.dungeon = self.json["map_challenge_mode_id"]
        region_slug = Utils().get_region_from_url(self.api_call_url)
        self.region = Utils().encode_region(region_slug)

    def __generate_sql_row_value(self, keyrun):
        """Crates VALUE component of SQL insert queryi for a run entry."""
        raise ("I broke this function. Delete it.")
        value = self.__sql_value_template.format(
            run_id=keyrun.run_id,
            dungeon=self.dungeon,
            key_level=keyrun.keystone_level,
            period=self.period,
            completed_timestamp=keyrun.completed_timestamp,
            duration_in_ms=keyrun.duration_in_ms,
            faction=keyrun.faction,
            region=self.region,
        )
        return value

    def parse_key_runs(self):
        """Unrolls runs/groups component into list of key run records.

        Parses the 'leading_groups' component of the json, which
        contains a ranking of up to 500 individual key runs.

        If 'leading_groups' missing returns [].
        """
        if "leading_groups" not in self.json.keys():
            return []
        keyruns = []
        for keyrun_json in self.json["leading_groups"]:
            keyrun = KeyRun(keyrun_json, self.region)
            keyruns.append(keyrun)
        return keyruns

    def get_runs_as_tuple_list(self):
        """Return leaderboard as list of tuples, where each tuple is a run.

        This list is meant to be fed to an SQL connector for a batch insert.
        """
        runs = []
        if not self.keyruns == []:
            return runs
        for run in self.keyruns:
            tpl = (
                run.run_id,
                self.dungeon,
                run.keystone_level,
                self.period,
                run.completed_timestamp,
                run.duration_in_ms,
                run.faction,
                self.region,
                SCORER.get_score(run.duration_in_ms, self.dungeon, run.keystone_level),
                self.istimed(run.duration_in_ms),
                run.composition,
            )
            runs.append(tpl)
        return runs

    def istimed(self, duration_in_ms):
        """Checks if the run was timed."""
        return Utils.istimed(dungeon=self.dungeon, duration=duration_in_ms)

    def get_rosters_as_tuple_list(self):
        """Returns roster data collated as list of tuples."""
        rosters = []
        for run in self.keyruns:
            tpl = run.get_members_as_tuple_list()
            rosters.extend(tpl)
        return rosters

    def get_run_comps_as_vector_list(self):
        """Return roster class/spec composition as list of lists."""
        comps = []
        for run in self.keyruns:
            comp = run.get_composition_vector()
            comps.append(comp)
        return comps

    def concat_runs_for_sql_insert(self):
        """Joins leaderboard runs into a single list.

        Each item in the list is a string formatted for an SQL insert.

        Warning: Roster data is handled separately:
            see concat_roster_for_sql_insert()
        """
        # low-level roster data is handled separetly because
        # it's got its own table in the DB
        values = []
        for keyrun in self.keyruns:
            value_string = self.__generate_sql_row_value(keyrun)
            values.append(value_string)
        return values

    def concat_rosters_for_sql_insert(self):
        """Joins roster data into a single list.

        Each item in the list is a character string
        formatted for an SQL insert.

        Warning: high-level key data is is handled separately:
            see concat_runs_for_sql_insert()
        """
        sql_template = (
            "("
            '{run_id},{character_id},"{character_name}",'
            "{character_spec},{character_realm}"
            ")"
        )
        rosters = []
        for keyrun in self.keyruns:
            for member in keyrun.roster:
                member_string = sql_template.format(
                    run_id=keyrun.run_id,
                    character_id=member.id_,
                    character_name=member.name,
                    character_spec=member.spec,
                    character_realm=member.vanity_realm_id,
                )
                rosters.append(member_string)
        return rosters


class KeyRun:
    """Container/parser for individual m+ run."""

    def __init__(self, key_run_json, region):
        """Inits record with key run json."""
        self.key_run_json = key_run_json
        self.region = region
        self.parse_json()

    def parse_json(self):
        """Parses the key run json string."""
        self.duration_in_ms = self.key_run_json["duration"]
        self.completed_timestamp = self.key_run_json["completed_timestamp"]
        self.keystone_level = self.key_run_json["keystone_level"]
        self.roster = self.parse_roster(self.key_run_json["members"])
        faction = self.roster[0].faction.lower()
        self.faction = 0 if "alliance" in faction else 1
        self.run_id = self.generate_id(self.region)
        self.composition = self.get_comp()

    def get_comp(self):
        """Generates 5-letter signature for roster spec composition."""
        sig = []
        for member in self.roster:
            sig.append(SPEC_UTILS.get_shorthand(member.spec))
        return "".join(sorted(sig))

    def parse_roster(self, members):
        """Extracts player info as a list of RosterMember objects."""
        roster = []
        for member in members:
            roster.append(RosterMember(member))
        return roster

    def generate_id(self, region):
        """Creates a unique record id for the run."""

        # This will serve as the PRIMARY KEY in the MySQL table. Uniqueness is
        # achieved by combining the truncated timestamp with character
        # id of the first player. Character ids are loosely region-unique, and
        # the same player id can't appear in two different keys at the same
        # time witin a region.

        timestamp = str(self.completed_timestamp)[1:-4]
        smallest_member_id = min([member.id_ for member in self.roster])
        run_id = "%s%s%s" % (timestamp, region, str(smallest_member_id).zfill(10))
        run_id = int(run_id)
        if run_id >= 18446744073709551615:  # max 64 bit int
            raise ValueError("Oh oh. The run id exceeds 64-bit int limit.")
        return int(run_id)

    def get_members_as_tuple_list(self):
        """Returns roster members as list of tuples."""
        members = []
        for member in self.roster:
            member_tuple = (
                self.run_id,
                member.id_,
                member.name,
                member.spec,
                member.vanity_realm_id,
            )
            members.append(member_tuple)
        return members

    def get_composition_vector(self):
        """Construct one-hot style vector to repsent spec composition."""
        specs = Utils().get_all_spec_ids()
        comp_vector = [0 for i in range(len(specs))]
        for member in self.roster:
            spec_index = specs.index(member.spec)
            comp_vector[spec_index] += 1
        comp_vector.insert(0, self.run_id)
        return tuple(comp_vector)


class RosterMember:
    """Container for player character from a key run."""

    def __init__(self, profile):
        """Inits with profile element of the 'members' json."""
        self.parse_profile(profile)

    def parse_profile(self, profile):
        """Parses character features (name, realm, etc)."""
        self.name = profile["profile"]["name"]
        self.id_ = profile["profile"]["id"]
        self.vanity_realm_id = profile["profile"]["realm"]["id"]
        self.faction = profile["faction"]["type"]
        self.spec = profile["specialization"]["id"]


class RealmRecord:
    """Container/parser for realm/shard info."""

    def __init__(self, json):
        """Inits with realm json component of realm id call return."""
        self.json = json
        self.parse_json()
        self.primary_key = self.generate_primary_key()

    def parse_json(self):
        """Unrolls the realm json."""
        self.realm_id = self.json["id"]
        self.region = self.json["region"]["id"]
        cluster_url = self.json["connected_realm"]["href"]
        self.cluster_id = int(ResponseParser.get_realm_id_from_url(cluster_url))
        self.name = self.json["name"]
        self.timezone = self.json["timezone"]
        self.name_slug = self.json["slug"]
        self.locale = self.json["locale"]

    def generate_primary_key(self):
        """Generates a unique key for record.

        This will serve as PRIMARY KEY in the db table.
        """
        primary_key = "%s%s%s" % (self.region, self.cluster_id, self.realm_id)
        return primary_key

    def get_data_for_database_table_as_dict(self):
        """Returns MDB-relevant portion of the record as dict."""
        # this one is so you can quickly make a DF with column headers
        record = {
            "cluster_id": self.cluster_id,
            "realm_id": self.realm_id,
            "name": self.name,
            "name_slug": self.name_slug,
            "region": self.region,
            "locale": self.locale,
            "timezone": self.timezone,
        }
        return record

    def get_data_for_database_table_as_tuple(self):
        """Returns MDB-relevant portion of the record as tuple."""
        # this one is so you can directly insert into MySQL
        record = (
            self.cluster_id,
            self.realm_id,
            self.name,
            self.name_slug,
            self.region,
            self.locale,
            self.timezone,
        )
        return record


class Caller:
    """Abstracts API interactions into a high-level interface."""

    __default_access_token_fp = ".api_tokens"

    def __init__(self, access_token=None):
        """Inits wtih access token. If no token, tries to get one."""
        if not access_token:
            auth = blizzard_credentials.Credentials(self.__default_access_token_fp)
            access_token = auth.access_token
        self.access_token = access_token
        if not self.access_token:
            raise ValueError(
                """Caller needs a valid access token
                to query Blizzard API"""
            )
        self.parser = ResponseParser()

    @staticmethod
    def send_request(call_url):
        response = requests.get(call_url)
        if response.status_code != 200:
            raise (
                """Call not successful
                [status code %s]: %s"""
                % (response.status_code, call_url)
            )
        return response

    def get_spec_indices(self):
        """Gets list of spec ids and names."""
        region = "us"
        url_factory = UrlFactory(self.access_token, region)
        url = url_factory.get_spec_index_url()
        response = self.send_request(url)
        json = response.json()
        specs = self.parser.parse_spec_index_json(json)
        return specs

    def get_spec_by_index(self, spec_index):
        """Returns full info for spec."""
        region = "us"
        url_factory = UrlFactory(self.access_token, region)
        url = url_factory.get_spec_url(spec_index)
        response = self.send_request(url)
        spec_info = self.parser.parse_spec_json(response.json())
        return spec_info

    def get_class_spec_table(self):
        """Gets class/spec table."""
        class_spec_table = []
        specs = self.get_spec_indices()
        for spec in specs:
            spec_id = spec[0]
            spec_info = self.get_spec_by_index(spec_id)
            class_spec_table.append(spec_info)
        return class_spec_table

    def get_leaderboard(self, region, realm, dungeon, period):
        """Gets leaderboard for specified region/realm/dungeon/period."""
        url_factory = UrlFactory(self.access_token, region)
        call_url = url_factory.get_mythic_plus_leaderboard_url(
            dungeon_id=dungeon, realm_id=realm, period=period
        )
        response = self.send_request(call_url)
        leaderboard = self.parser.parse_keyrun_leaderboard_json(response.json())
        return leaderboard

    def get_current_period(self, region):
        """Gets current m+ period for region."""
        url_factory = UrlFactory(self.access_token, region)
        period_index_url = url_factory.get_timeperiod_index_url()
        response = requests.get(period_index_url)
        periods = self.parser.parse_timeperiod_index_json(response.json())
        current_period = max(periods)
        return current_period

    def get_period_startend(self, region, period):
        """Gets start and end timestamp for period."""
        url_factory = UrlFactory(self.access_token, region)
        period_url = url_factory.get_timeperiod_url(period)
        response = requests.get(period_url)
        start, end = self.parser.parse_timeperiod_json(response.json())
        return start, end

    def get_dungeons(self):
        """Gets list of dungeon ids."""
        url_factory = UrlFactory(self.access_token, region="us")
        dungeon_index_url = url_factory.get_dungeon_index_url()
        response = requests.get(dungeon_index_url)
        dungeons = self.parser.parse_dungeon_index_json(response.json())
        return dungeons

    def get_connected_realms(self, region):
        """Gets list of connected realms (realm clusters)."""
        url_factory = UrlFactory(self.access_token, region=region)
        realm_index_url = url_factory.get_connected_realm_index_url()
        response = requests.get(realm_index_url)
        cluster_ids = self.parser.parse_connected_realm_index_json(response.json())
        return cluster_ids
