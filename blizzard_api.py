"""Classes to query and parse Blizzard's WOW API."""


class BlizzardJsonParser():
    """Parse leaderboards Json."""

    def __init__(self, json):
        """Inits with rolled-up json string."""
        self.json = json
        for key in json.keys():
            print(key)

    def parse_keyrun_json(self):
        """Parses the key runs component of the json."""
        for keyrun_json in self.json['leading_groups'][0:1]:
            keyrun = KeyRunRecord(keyrun_json)
            return keyrun


class KeyRunRecord():
    """Container for a m+ run."""

    def __init__(self, key_run_json):
        """Inits record with key run json."""
        self.key_run_json = key_run_json
        self.parse_json()
        print(key_run_json.keys())

    def parse_json(self):
        """Parses the key run json string."""
        self.duration_in_ms = self.key_run_json['duration']
        self.completed_timestamp = self.key_run_json['completed_timestamp']
        self.keystone_level = self.key_run_json['keystone_level']
        self.members = self.parse_members(self.key_run_json['members'])

    def parse_members(self, members):
        """Parse member element of the json."""
        member_ids = []
        for member in members:
            character_id = member['profile']['id']
            member_ids.append(character_id)
        return member_ids
