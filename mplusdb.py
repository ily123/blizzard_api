"""Module for uploading data to M+ MySQL database."""
import mysql.connector
import pandas as pd

class MplusDatabase():
    """Class for working with M+ MySQL database."""
    __utility_tables = ['realm', 'region', 'dungeon', 'spec']
    __main_tables = ['period']
    __table_fields = { #these are used to formulate batch inserts queries
        'period' : ['region', 'id', 'start_timestamp', 'end_timestamp'],
        'run' : ['id', 'dungeon', 'level', 'period', 'timestamp', 
                 'duration', 'faction', 'region'],
        'roster' : ['run_id', 'character_id', 'name', 'spec', 'realm'],
        'run_composition' : [
            'run_id',
            'mage_arcane',
            'mage_fire',
            'mage_frost',
            'paladin_holy',
            'paladin_protection',
            'paladin_retribution',
            'warrior_arms',
            'warrior_fury',
            'warrior_protection',
            'druid_balance',
            'druid_feral',
            'druid_guardian',
            'druid_restoration',
            'death_knight_blood',
            'death_knight_frost',
            'death_knight_unholy',
            'hunter_beast_mastery',
            'hunter_marksmanship',
            'hunter_survival',
            'priest_discipline',
            'priest_holy',
            'priest_shadow',
            'rogue_assassination',
            'rogue_outlaw',
            'rogue_subtlety',
            'shaman_elemental',
            'shaman_enhancement',
            'shaman_restoration',
            'warlock_affliction',
            'warlock_demonology',
            'warlock_destruction',
            'monk_brewmaster',
            'monk_windwalker',
            'monk_mistweaver',
            'demon_hunter_havoc',
            'demon_hunter_vengeance'
        ]
    } #is this time to move these into their own container?   

    def __init__(self, config_file_path):
        """Inits with database config file."""
        self.credentials = self.parse_config_file(config_file_path)
        
    @staticmethod 
    def parse_config_file(file_path):
        """Parses config file."""
        credentials = {}
        with open(file_path, 'r') as config_file:
            for line in config_file:
                content = line.split()[1]
                if 'user' in line: 
                    credentials['user'] = content
                if 'password' in line:
                    credentials['password'] = content
                if 'host' in line:
                    credentials['host'] = content
        credentials['database'] = 'keyruns'
        return credentials

    def connect(self):
        """Connects to the database.
        
        Returns
        -------
        conn : mysql.connector connection
            open connection to the MDB.
        """
        conn = mysql.connector.connect(**self.credentials) 
        return conn

    def execute_insert_query(self, query):
        """Execute insert or update query aganist the database."""
        connection = self.connect()
        cursor = connection.cursor()
        try:
            cursor.execute(query)
            connection.commit()
        except:
          raise Exception('Problem inserting data.') 
        finally:
            cursor.close()
            connection.close() 
        
    def insert(self, table, data):
        """Batch-inserts list of rows into database.

        Warning: make sure row fields align with fields in the table.
        """
        if not isinstance(data, list):
            raise TypeError('Supply data as a list of rows')
        fields = self.get_table_fields(table)
        connection = self.connect()
        cursor = connection.cursor()
        try:
            query = ('INSERT IGNORE into {table} '
                     '({table_fields}) '
                     'VALUES ({blanks})').format(table = table,
                table_fields = ','.join(fields),
                blanks = ','.join(['%s' for i in range(0, len(fields))]))
            #executemany supposedly batches data into a single query
            cursor.executemany(query, data)
            connection.commit()
        except:
            raise Exception('Problem with inserting data into MDB.')
        finally:
            cursor.close()
            connection.close() 

    def raw_batch_insert(self, query, data):
        """Batch-inserts list of data according to provided query."""
        connection = self.connect()
        cursor = connection.cursor()
        try:
            cursor.executemany(query, data)
            connection.commit()
        except:
            raise Exception('Problem with inserting data into MDB.')
        finally:
            cursor.close()
            connection.close() 
    
    def get_table_fields(self, table):
        """Returns fieds in table, in correct order.
        
        The table schemas are set up by hand and correspond to MDB.
        """
        return self.__table_fields[table]

    def get_utility_table(self, table):
        """Retrieves utility table from the database in SELECT * fashion.
        
        Params
        ------
        table : str
            name of the utility table:
              'realm' : mapping of realm names, ids, and cluter ids
              'dungeon' : mapping of dungeon names and ids
              'region' : mapping of region tokens to ids
              'spec' : mapping of class-spec ids and names
        Returns
        -------
        data : pd.DataFrame
            response the database sent back, formatted as pandas df
        """
        if table not in self.__utility_tables:
            raise ValueError('%s is not a legal utility table.' % table)
        data, columns = None, None
        connection = self.connect()
        cursor = connection.cursor()
        try:
            cursor.execute('SELECT * from %s' % table)
            data = cursor.fetchall()
            columns = cursor.column_names
        except:
          raise Exception('Problem retrieving util table.') 
        finally:
            cursor.close()
            connection.close() 
        return pd.DataFrame(data, columns = columns)

    def close_connection(self):
        """Closes the open connection to MDB.""" 
        self.connection.close()
