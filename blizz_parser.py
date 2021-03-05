"""Functions to parse Blizzard json strings.

Usage example:

    import parser

    response = requests.get(leaderboard_url)
    leaderboard = parser.parse_mplus_leaderboard(response.json())
"""
import re
from typing import List, Tuple

import utils
from utils import Utils

SPEC_UTILS = utils.Specs()
SCORER = utils.Scorer()


def _get_realm_id_from_url(connected_realm_url: str) -> int:
    """Parsess realm ID from the realm url."""
    cap = re.findall("connected-realm\/(\d+)\?", connected_realm_url)
    realm_id = int(cap[0])
    return realm_id


def parse_timeperiod_index_json(json: dict) -> List[int]:
    """Retrieves time period ids from periond index call json."""
    period_ids = []
    for period in json["periods"]:
        period_ids.append(period["id"])
    return period_ids


def parse_timeperiod_json(json: dict) -> Tuple[int, int]:
    """Retrieves start and end timestamps from period json."""
    start = json["start_timestamp"]
    end = json["end_timestamp"]
    return start, end


def parse_connected_realm_index_json(json: dict) -> List[int]:
    """Unrolls json from a connected realm index call."""
    # the json supplies list of url calls to individual realms
    # we just want the realm ids contained in the urls
    realm_urls = [realm["href"] for realm in json["connected_realms"]]
    realm_ids = []
    for realm_url in realm_urls:
        realm_ids.append(_get_realm_id_from_url(realm_url))
    return realm_ids


def parse_connected_realm_json(json) -> List[dict]:
    """Parses connected realm call json output."""
    realms_in_cluster = []
    for realm_json in json["realms"]:
        realm = RealmRecord(realm_json)
        realms_in_cluster.append(realm.get_as_dict())
    return realms_in_cluster


def parse_spec_index_json(json: dict) -> List[dict]:
    """Parses spec index call response."""
    specs = []
    for spec in json["character_specializations"]:
        id_ = spec["id"]
        name = spec["name"]
        specs.append(dict(spec_id=id_, spec_name=name))
    return specs


def parse_spec_json(json: dict) -> dict:
    """Parses playable spec json."""
    spec_id = json["id"]
    spec_name = json["name"].lower()
    class_id = json["playable_class"]["id"]
    class_name = json["playable_class"]["name"].lower()
    role = json["role"]["type"].lower()
    spec_info = dict(
        class_name=class_name,
        class_id=class_id,
        spec_name=spec_name,
        spec_id=spec_id,
        role=role,
    )
    return spec_info


def parse_dungeon_index_json(json: dict) -> List[dict]:
    """Parses current patch dungeons index json."""
    dungeons = []
    for dungeon in json["dungeons"]:
        dungeons.append({"id": dungeon["id"], "name": dungeon["name"]})
    return dungeons


class RealmRecord:
    """Container/parser for realm/shard info."""

    def __init__(self, json: dict) -> None:
        """Inits with realm json component of realm id call return."""
        self.json = json
        self._parse_json()
        self.primary_key = self._generate_primary_key()

    def _parse_json(self) -> None:
        """Unrolls the realm json."""
        self.realm_id = self.json["id"]
        self.region = self.json["region"]["id"]
        cluster_url = self.json["connected_realm"]["href"]
        self.cluster_id = _get_realm_id_from_url(cluster_url)
        self.name = self.json["name"]
        self.timezone = self.json["timezone"]
        self.name_slug = self.json["slug"]
        self.locale = self.json["locale"]

    def _generate_primary_key(self) -> str:
        """Generates a unique key for record.

        This will serve as PRIMARY KEY in the db table.
        """
        primary_key = "%s%s%s" % (self.region, self.cluster_id, self.realm_id)
        return primary_key

    def get_as_dict(self) -> dict:
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


class RosterMember:
    """Container for player character from a key run."""

    # a class is an overkill for this? should be a method that produces a NamedTuple

    def __init__(self, profile) -> None:
        """Inits with profile element of the 'members' json."""
        self._parse_profile(profile)

    def _parse_profile(self, profile) -> None:
        """Parses character features (name, realm, etc)."""
        self.name = profile["profile"]["name"]
        self.id_ = profile["profile"]["id"]
        self.vanity_realm_id = profile["profile"]["realm"]["id"]
        self.faction = profile["faction"]["type"]
        self.spec = profile["specialization"]["id"]


class KeyRun:
    """Container/parser for individual m+ run."""

    def __init__(self, key_run_json, region, dungeon) -> None:
        """Inits record with key run json."""
        self.key_run_json = key_run_json
        self.region = region
        self.dungeon = dungeon
        self._parse_json()
        self.score = self._get_score()
        self.istimed = self._istimed()

    def _parse_json(self) -> None:
        """Parses the key run json string."""
        self.duration_in_ms = self.key_run_json["duration"]
        self.completed_timestamp = self.key_run_json["completed_timestamp"]
        self.keystone_level = self.key_run_json["keystone_level"]
        self.roster = self._parse_roster(self.key_run_json["members"])
        faction = self.roster[0].faction.lower()
        self.faction = 0 if "alliance" in faction else 1
        self.run_id = self._generate_id()
        self.composition = self._get_comp()

    def _get_comp(self) -> str:
        """Generates 5-letter signature for roster spec composition."""
        sig = []
        for member in self.roster:
            sig.append(SPEC_UTILS.get_shorthand(member.spec))
        return "".join(sorted(sig))

    @staticmethod
    def _parse_roster(members) -> List[RosterMember]:
        """Extracts player info as a list of RosterMember objects."""
        roster = []
        for member in members:
            roster.append(RosterMember(member))
        return roster

    def _generate_id(self) -> int:
        """Creates a unique record id for the run."""

        # This will serve as the PRIMARY KEY in the MySQL table. Uniqueness is
        # achieved by combining the truncated timestamp with character
        # id of the first player. Character ids are loosely region-unique, and
        # the same player id can't appear in two different keys at the same
        # time witin a region.

        timestamp = str(self.completed_timestamp)[1:-4]
        smallest_member_id = min([member.id_ for member in self.roster])
        run_id = int(
            "%s%s%s" % (timestamp, self.region, str(smallest_member_id).zfill(10))
        )
        if run_id >= 18446744073709551615:  # max 64 bit int
            raise ValueError("Oh oh. The run id exceeds 64-bit int limit.")
        return run_id

    def _get_score(self) -> float:
        """Calculate points awarded by run."""
        score = SCORER.get_score(self.duration_in_ms, self.dungeon, self.keystone_level)
        return score

    def _istimed(self) -> bool:
        """Checks if the run was timed."""
        return Utils.istimed(dungeon=self.dungeon, duration=self.duration_in_ms)

    def get_roster_as_tuple_list(self) -> List[tuple]:
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

    def get_composition_vector(self) -> tuple:
        """Construct one-hot style vector to repsent spec composition."""
        specs = Utils().get_all_spec_ids()
        comp_vector = [0 for i in range(len(specs))]
        for member in self.roster:
            spec_index = specs.index(member.spec)
            comp_vector[spec_index] += 1
        comp_vector.insert(0, self.run_id)
        return tuple(comp_vector)


class KeyRunLeaderboard:
    """Container/parser for Key Run leaderboard."""

    def __init__(self, json) -> None:
        self.json = json
        self._parse_meta_features()
        self.keyruns = self._parse_key_runs()

    def _parse_meta_features(self) -> None:
        """Extracts leaderboard regon-level data."""
        self.api_call_url = self.json["_links"]["self"]["href"]
        self.period = self.json["period"]
        self.realm = _get_realm_id_from_url(self.json["connected_realm"]["href"])
        self.dungeon = self.json["map_challenge_mode_id"]
        region_slug = Utils().get_region_from_url(self.api_call_url)
        self.region = Utils().encode_region(region_slug)
        self.affixes = sorted(
            [
                int(affix["keystone_affix"]["id"])
                for affix in self.json["keystone_affixes"]
            ]
        )

    def _parse_key_runs(self) -> List[KeyRun]:
        """Unrolls runs/groups component into list of key run records.

        Parses the 'leading_groups' component of the json, which
        contains a ranking of up to 500 individual key runs.

        If 'leading_groups' missing returns [].
        """
        if "leading_groups" not in self.json.keys():
            return []
        keyruns = []
        for keyrun_json in self.json["leading_groups"]:
            keyrun = KeyRun(keyrun_json, self.region, self.dungeon)
            keyruns.append(keyrun)
        return keyruns

    def get_runs_as_tuple_list(self) -> List[tuple]:  # annotation is tricky here
        """Return leaderboard as list of tuples, where each tuple is a run.

        This list is meant to be fed to an SQL connector for a batch insert.
        """
        runs = []
        if self.keyruns == []:
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
                run.score,
                run.istimed,
                run.composition,
            )
            runs.append(tpl)
        return runs

    def get_rosters_as_tuple_list(self) -> List[tuple]:
        """Returns roster data collated as list of tuples."""
        rosters = []
        for run in self.keyruns:
            tpl = run.get_roster_as_tuple_list()
            rosters.extend(tpl)
        return rosters

    def get_run_comps_as_vector_list(self) -> List[tuple]:
        """Return roster class/spec composition as list of lists."""
        comps = []
        for run in self.keyruns:
            comp = run.get_composition_vector()
            comps.append(comp)
        return comps
