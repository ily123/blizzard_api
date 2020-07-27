"""Module for uploading data to M+ MySQL database."""
import mysql.connector


class MplusDB():
    """Class for working with M+ MySQL database."""

    def __init__(self, config_file_path):
        """Inits with database config file."""
        self.credentials = self.parse_config_file(config_file_path)
        self.connection = None
        
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
        """Connects to the database."""
        conn = mysql.connector.connect(**self.credentials) 
        self.connection = conn
        return conn

    def insert_row(self, table='run', row):
        """Inserts single row into table."""
        cursor = self.connection.cursor()

        query_template = 'INSERT INTO {table_name} ({columns}) VALUES ({values})'

        query = query_template.format(
            table_name = self.table_name,
            columns = columns,
            values = values)
        #cursor.execute('INSERT 
