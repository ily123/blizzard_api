"""Utility methods."""
import re

import pandas as pd


def get_dungeon_timers():
    """Returns timer for dungeon in ms."""
    dungeon_timers = {
        197: 2000000,  # placeholder for 197
        244: 1800000,
        245: 1980000,
        246: 2160000,
        247: 2340000,
        248: 2340000,
        249: 2520000,
        250: 2160000,
        251: 1980000,
        252: 2520000,
        353: 2160000,
        369: 2280000,
        370: 1920000,
        375: 1800000,
        376: 2160000,
        377: 2580000,
        378: 1860000,
        379: 2280000,
        380: 2460000,
        381: 2340000,
        382: 2220000,
    }
    return dungeon_timers


class Utils:
    """Collection of utility methods."""

    @staticmethod
    def get_realm_id_from_url(connected_realm_url):
        """Parsess realm ID from the json."""
        cap = re.findall("connected-realm\/(\d+)\?", connected_realm_url)
        realm_id = cap[0]
        return realm_id

    @staticmethod
    def encode_region(region_slug):
        """Converts region token string into an int code."""
        codes = {"us": 1, "kr": 2, "eu": 3, "tw": "4"}
        return codes[region_slug.lower()]

    @staticmethod
    def get_region_from_url(url):
        """Extracts region from call url."""
        pattern = re.compile("namespace=(dynamic|static)-(\w{2})$")
        cap = pattern.search(url)
        region_slug = cap[2]
        return region_slug

    @staticmethod
    def get_all_spec_ids():
        """Return sorted list of all specs ids."""
        # fmt: off
        specs = [
            62, 63, 64, 65, 66, 70, 71, 72, 73,
            102, 103, 104, 105, 250, 251, 252, 253,
            254, 255, 256, 257, 258, 259, 260, 261,
            262, 263, 264, 265, 266, 267, 268, 269,
            270, 577, 581,
        ]
        # fmt: on
        return specs

    @staticmethod
    def istimed(dungeon, duration):
        """Checks if run has been timed."""
        timer_in_ms = get_dungeon_timers()
        return int(duration) <= timer_in_ms[int(dungeon)]


class Scorer:
    def __init__(self):
        """Inits with dungeon timer dict attr."""
        self.dungeon_timers = get_dungeon_timers()

    def get_ratio_user_vs_base_timer(self, user_time, user_dungeon):
        default_time = self.dungeon_timers[user_dungeon]
        return user_time / default_time

    def get_score(self, user_time, user_dungeon, dungeon_level):
        """Calculates points awarded for run."""
        ratio = self.get_ratio_user_vs_base_timer(user_time, user_dungeon)

        base_points = self.get_base_score(dungeon_level)
        final_score = 0
        if ratio <= 1.0:  # successful timer
            bonus = self.get_bonus_points(ratio, base_points)
            final_score = base_points + bonus
        else:
            penalty = self.get_penalty_points(ratio, base_points)
            final_score = base_points - penalty
        if final_score < 10:
            final_score = 10
        return final_score

    def get_bonus_points(self, ratio, base_points):
        """Calculates bonus points gained for faster-than-timer completion."""
        flat_bonus = (1 - ratio) * 0.085
        chest_bonus = 0
        if ratio <= 0.6:
            chest_bonus = 0.03
        elif ratio <= 0.8:
            chest_bonus = 0.015
        pct_bonus = flat_bonus + chest_bonus
        bonus_points = base_points * pct_bonus
        return bonus_points

    def get_penalty_points(self, ratio, base_points):
        """Calculates penalty points for failed timer."""
        base_penatly_points = base_points * 0.1
        additional_penalty_points = (ratio - 1) * (0.24 * base_points * 0.9)
        total_penalty = base_penatly_points + additional_penalty_points
        return total_penalty

    def get_base_score(self, dungeon_level):
        """Calculates score for key level."""
        if dungeon_level <= 10:
            return 10 * dungeon_level
        else:
            return 100 * 1.1 ** (dungeon_level - 10)


class ClassColors:
    def __init__(self):
        # https://wow.gamepedia.com/Class_colors
        self.class_rgb_color = {
            "death knight": (196, 31, 59),
            "demon hunter": (163, 48, 201),
            "death_knight": (196, 31, 59),
            "demon_hunter": (163, 48, 201),
            "druid": (255, 125, 10),
            "hunter": (169, 210, 113),
            "mage": (64, 199, 235),
            "monk": (0, 255, 150),
            "paladin": (245, 140, 186),
            "priest": (255, 255, 255),
            "rogue": (255, 245, 105),
            "shaman": (0, 112, 222),
            "warlock": (135, 135, 237),
            "warrior": (199, 156, 110),
        }

    def get_rbg(self, class_name):
        """Returns color for given class."""
        return self.class_rgb_color[class_name.lower()]


class Specs:
    """Container for spec meta data.

    These are hard-coded. AFAIK, Blizzard never changes them.
    """

    def __init__(self):
        """Init of list of dict, where each dict is a spec."""
        class_colors = ClassColors()
        self.specs = []
        for row in self.get_specs():
            spec = dict(
                class_name=row[0],
                class_id=row[1],
                spec_name=row[2],
                spec_id=row[3],
                role=row[4],
                token=row[5],
                shorthand=row[6],
                color=class_colors.get_rbg(row[0]),
            )
            self.specs.append(spec)

    # I am not using a df here because the data is small
    # and df will just add overhead that isn't worth it
    def get_color(self, spec_id):
        """Get color for spec using spec id."""
        for spec in self.specs:
            if spec["spec_id"] == spec_id:
                return spec["color"]
        raise ValueError("spec id not found in spec table")

    def get_class_name(self, spec_id):
        """Get class name given a spec id."""
        for spec in self.specs:
            if spec["spec_id"] == spec_id:
                return spec["class_name"]
        raise ValueError("spec id not found in spec table")

    def get_spec_name(self, spec_id):
        """Get class name given a spec id."""
        for spec in self.specs:
            if spec["spec_id"] == spec_id:
                return spec["spec_name"]
        raise ValueError("spec id not found in spec table")

    def get_role(self, spec_id):
        """Get class name given a spec id."""
        for spec in self.specs:
            if spec["spec_id"] == spec_id:
                return spec["role"]
        raise ValueError("spec id not found in spec table")

    def get_spec_ids_for_role(self, role):
        """Get list of spec ids for role."""
        valid_roles = ["tank", "healer", "mdps", "rdps"]
        if role not in valid_roles:
            raise ValueError("Spec role invalid. Must be one of: %s")
        role_specs = []
        for spec in self.specs:
            if spec["role"] == role:
                role_specs.append(spec["spec_id"])
        return role_specs

    def get_shorthand(self, spec_id):
        """Returns one-letter code for spec given spec id."""
        for spec in self.specs:
            if spec["spec_id"] == spec_id:
                return spec["shorthand"]

    @staticmethod
    def get_specs():
        """Returns nested list of spec meta data."""
        # fmt: off
        return [
            ['death knight', 6, 'blood', 250, 'tank', 'death_knight_blood', 'a'],
            ['death knight', 6, 'frost', 251, 'mdps', 'death_knight_frost', 'b'],
            ['death knight', 6, 'unholy', 252, 'mdps', 'death_knight_unholy', 'c'],
            ['demon hunter', 12, 'havoc', 577, 'mdps', 'demon_hunter_havoc', 'd'],
            ['demon hunter', 12, 'vengeance', 581, 'tank', 'demon_hunter_vengeance', 'e'],
            ['druid', 11, 'balance', 102, 'rdps', 'druid_balance', 'f'],
            ['druid', 11, 'feral', 103, 'mdps', 'druid_feral', 'g'],
            ['druid', 11, 'guardian', 104, 'tank', 'druid_guardian', 'h'],
            ['druid', 11, 'restoration', 105, 'healer', 'druid_restoration', 'i'],
            ['hunter', 3, 'beast mastery', 253, 'rdps', 'hunter_beast_mastery', 'j'],
            ['hunter', 3, 'marksmanship', 254, 'rdps', 'hunter_marksmanship', 'k'],
            ['hunter', 3, 'survival', 255, 'mdps', 'hunter_survival', 'l'],
            ['mage', 8, 'arcane', 62, 'rdps', 'mage_arcane', 'm'],
            ['mage', 8, 'fire', 63, 'rdps', 'mage_fire', 'n'],
            ['mage', 8, 'frost', 64, 'rdps', 'mage_frost', 'o'],
            ['monk', 10, 'brewmaster', 268, 'tank', 'monk_brewmaster', 'p'],
            ['monk', 10, 'mistweaver', 270, 'healer', 'monk_mistweaver', 'q'],
            ['monk', 10, 'windwalker', 269, 'mdps', 'monk_windwalker', 'r'],
            ['paladin', 2, 'holy', 65, 'healer', 'paladin_holy', 's'],
            ['paladin', 2, 'protection', 66, 'tank', 'paladin_protection', 't'],
            ['paladin', 2, 'retribution', 70, 'mdps', 'paladin_retribution', 'u'],
            ['priest', 5, 'discipline', 256, 'healer', 'priest_discipline', 'v'],
            ['priest', 5, 'holy', 257, 'healer', 'priest_holy', 'w'],
            ['priest', 5, 'shadow', 258, 'rdps', 'priest_shadow', 'x'],
            ['rogue', 4, 'assassination', 259, 'mdps', 'rogue_assassination', 'y'],
            ['rogue', 4, 'outlaw', 260, 'mdps', 'rogue_outlaw', 'z'],
            ['rogue', 4, 'subtlety', 261, 'mdps', 'rogue_subtlety', 'A'],
            ['shaman', 7, 'elemental', 262, 'rdps', 'shaman_elemental', 'B'],
            ['shaman', 7, 'enhancement', 263, 'mdps', 'shaman_enhancement', 'C'],
            ['shaman', 7, 'restoration', 264, 'healer', 'shaman_restoration', 'D'],
            ['warlock', 9, 'affliction', 265, 'rdps', 'warlock_affliction', 'F'],
            ['warlock', 9, 'demonology', 266, 'rdps', 'warlock_demonology', 'G'],
            ['warlock', 9, 'destruction', 267, 'rdps', 'warlock_destruction', 'H'],
            ['warrior', 1, 'arms', 71, 'mdps', 'warrior_arms', 'I'],
            ['warrior', 1, 'fury', 72, 'mdps', 'warrior_fury', 'J'],
            ['warrior', 1, 'protection', 73, 'tank', 'warrior_protection', 'K']
        ]
        # fmt: on
