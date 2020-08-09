"""Module for uploading data to M+ MySQL database."""
import mysql.connector
import pandas as pd

class MplusDatabase():
    """Class for working with M+ MySQL database."""
    __utility_tables = ['realm', 'region', 'dungeon']

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
        

    def get_utility_table(self, table):
        """Retrieves utility table from the database in SELECT * fashion.
        
        Params
        ------
        table : str
            name of the utility table:
              'realm' : mapping of realm names, ids, and cluter ids
              'dungeon' : mapping of dungeon names and ids
              'region' : mapping of region tokens to ids
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
