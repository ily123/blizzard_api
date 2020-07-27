"""Classes to query and parse Blizzard's WOW API."""
import re


class BlizzardJsonParser():
    """Parse leaderboards Json."""

    def __init__(self, json):
        """Inits with rolled-up json string."""
        self.json = json
        self.set_sql_value_template()        
        self.get_meta_features()
        self.destination_table = 'run'
 
    def get_meta_features(self):
        #for key in self.json.keys():
        #    if 'leading' in key:
        #        continue
        #    print(key)
        #    print(self.json[key])
        #    print('-'*38) 
        self.api_call = self.json['_links']['self']['href']
        self.period = self.json['period']
        self.realm = self.get_realm_id_from_url(
                            self.json['connected_realm']['href'])
        self.dungeon = self.json['map_challenge_mode_id']
        
    @staticmethod
    def get_realm_id_from_url(connected_realm_url):
        """Parsess realm ID from the json."""
        cap = re.findall('connected-realm\/(\d+)\?', connected_realm_url)       
        realm_id = cap[0]
        return realm_id
        
    def parse_keyrun_json(self):
        """Parses the key runs component of the json."""
        keyruns = []
        values = []
        for keyrun_json in self.json['leading_groups']:
            keyrun = KeyRunRecord(keyrun_json)
            keyruns.append(keyrun)
            value = self.generate_sql_value(keyrun)
            values.append(value)
        insert_query = self.construct_sql_query(values)
        return insert_query

    def generate_sql_value(self, keyrun):
        """Crates VALUE component of SQL insert query."""
        value = self.sql_value_template.format(
                    run_id = keyrun.run_id,
                    dungeon = self.dungeon,
                    region = 0,
                    faction = 0,
                    key_level = keyrun.keystone_level,
                    completed_timestamp = keyrun.completed_timestamp,
                    duration_in_ms = keyrun.duration_in_ms,
                    character1_id = keyrun.members[0],
                    character2_id = keyrun.members[1],
                    character3_id = keyrun.members[2],
                    character4_id = keyrun.members[3],
                    character5_id = keyrun.members[4]
            )
        return value
    
    def construct_sql_query(self, values):
        """Creates data-complete SQL INSERT query."""
        query = 'INSERT IGNORE INTO %s VALUES %s' % (self.destination_table,
                                              ','.join(values))

        return query

    def set_sql_value_template(self):    
        """Creates template for VALUE() component of SQL insert query."""
        template = ['(',
                    '{run_id},{dungeon},{region},{faction},{key_level},',
                    '{completed_timestamp},{duration_in_ms},',
                    '{character1_id},',
                    '{character2_id},',
                    '{character3_id},',
                    '{character4_id},',
                    '{character5_id}',
                    ')'
                   ]
        self.sql_value_template = ''.join(template)
                    
#id | dungeon | region | faction | key_level | completed_timestamp | duration_in_ms | character1_id | character2_id | character3_id | character4_id | character5_id 

class KeyRunRecord():
    """Container for a m+ run."""

    def __init__(self, key_run_json):
        """Inits record with key run json."""
        self.key_run_json = key_run_json
        self.parse_json()
        self.run_id = self.generate_id()
#        print(key_run_json.keys())

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
        member_ids.sort()
        return member_ids

    def generate_id(self):
        """Create a unique record for the run.

        This will serve as the PRIMARY KEY in the SQL database.
        """
        
        truncated_timestamp = str(self.completed_timestamp)[0:-3]
        first_party_member_id = str(self.members[0])
        run_id = truncated_timestamp + first_party_member_id
        run_id = int(run_id)
        return run_id
