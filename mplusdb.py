"""Module for uploading data to the M+ MySQL database."""
import configparser
from typing import List, Optional

import mysql.connector
import pandas as pd


class MplusDatabase(object):
    """Class for working with M+ MySQL database."""

    __utility_tables = ["realm", "region", "dungeon", "spec", "period"]
    __table_fields = {  # these are used to formulate batch inserts queries
        "period": ["region", "id", "start_timestamp", "end_timestamp"],
        "run": [
            "id",
            "dungeon",
            "level",
            "period",
            "timestamp",
            "duration",
            "faction",
            "region",
            "score",
            "istimed",
            "composition",
        ],
        "roster": ["run_id", "character_id", "name", "spec", "realm"],
        "run_composition": [
            "run_id",
            "mage_arcane",
            "mage_fire",
            "mage_frost",
            "paladin_holy",
            "paladin_protection",
            "paladin_retribution",
            "warrior_arms",
            "warrior_fury",
            "warrior_protection",
            "druid_balance",
            "druid_feral",
            "druid_guardian",
            "druid_restoration",
            "death_knight_blood",
            "death_knight_frost",
            "death_knight_unholy",
            "hunter_beast_mastery",
            "hunter_marksmanship",
            "hunter_survival",
            "priest_discipline",
            "priest_holy",
            "priest_shadow",
            "rogue_assassination",
            "rogue_outlaw",
            "rogue_subtlety",
            "shaman_elemental",
            "shaman_enhancement",
            "shaman_restoration",
            "warlock_affliction",
            "warlock_demonology",
            "warlock_destruction",
            "monk_brewmaster",
            "monk_windwalker",
            "monk_mistweaver",
            "demon_hunter_havoc",
            "demon_hunter_vengeance",
        ],
    }  # is this time to move these into their own container?

    def __init__(self, config_file_path):
        """Inits with database config file."""
        # self.credentials = self.parse_config_file(config_file_path)
        parser = configparser.ConfigParser()
        parser.read(config_file_path)
        self.credentials = {}
        self.credentials["user"] = parser["DATABASE"]["user"]
        self.credentials["password"] = parser["DATABASE"]["password"]
        self.credentials["host"] = parser["DATABASE"]["host"]
        self.credentials["database"] = "keyruns"

    def connect(self):
        """Connects to the database.

        Returns
        -------
        conn : mysql.connector connection
            open connection to the MDB.
        """
        conn = mysql.connector.connect(**self.credentials)
        return conn

    def insert(self, table, data):
        """Batch-inserts list of rows into database.

        Warning: make sure row fields align with fields in the table.
        """
        if not isinstance(data, list):
            raise TypeError("Supply data as a list of rows")
        fields = self.get_table_fields(table)
        connection = self.connect()
        cursor = connection.cursor()
        try:
            query = (
                "INSERT IGNORE into {table} ({table_fields}) VALUES ({blanks})"
            ).format(
                table=table,
                table_fields=",".join(fields),
                blanks=",".join(["%s" for i in range(0, len(fields))]),
            )
            # executemany supposedly batches data into a single query
            cursor.executemany(query, data)
            connection.commit()
        except Exception as error:
            raise Exception("Problem with inserting data into MDB: [%s]" % error)
        finally:
            cursor.close()
            connection.close()

    def send_query_to_mdb(self, query, isfetch=False) -> Optional[List[tuple]]:
        """Sends non-insert query to MDB."""
        result = None
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute("use keyruns")
            cursor.execute(query)
            if isfetch:
                result = cursor.fetchall()
            conn.commit()
        except Exception as error:
            print("ERROR CONNECTING TO MDB: ", error)
        finally:
            conn.close()
        return result

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
              'period' : period id to region and timestamp

        Returns
        -------
        data : pd.DataFrame
            response the database sent back, formatted as pandas df
        """
        if table not in self.__utility_tables:
            raise ValueError("%s is not a legal utility table." % table)
        data, columns = None, None
        connection = self.connect()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT * from %s" % table)
            data = cursor.fetchall()
            columns = cursor.column_names
        except:
            raise Exception("Problem retrieving util table.")
        finally:
            cursor.close()
            connection.close()
        return pd.DataFrame(data, columns=columns)

    def pull_existing_run_ids(self, region: int, period: int) -> List[int]:
        """Pulls id column from the 'run' table for specified period/region."""
        query = "SELECT id FROM run WHERE region=%d and period=%d" % (region, period)
        run_ids = self.send_query_to_mdb(query=query, isfetch=True)
        run_ids = [int(item[0]) for item in run_ids]
        return run_ids

    def update_summary_spec_table(self, period_start, period_end) -> None:
        """Updates 'summary_spec' table with runs from specified period band."""
        # at some point, I need to make this method more flexible wrt period clause
        update_query = """
            INSERT INTO summary_spec
            SELECT period, spec, level, count(level) as count
            FROM run
            INNER JOIN roster on run.id = roster.run_id
            WHERE run.period BETWEEN %d AND %d
            GROUP BY period, spec, level
            ON DUPLICATE KEY UPDATE count=VALUES(count);
        """
        update_query = update_query % (period_start, period_end)
        self.send_query_to_mdb(update_query)

    def get_summary_spec_table_as_df(self) -> pd.DataFrame:
        """Exports summary_spec table formatted for front-end.

        The summary table is grouped by by spec/level/season."""
        query = "SELECT * from summary_spec;"
        data_ = self.send_query_to_mdb(query, isfetch=True)
        data = pd.DataFrame(data_, columns=["period", "spec", "level", "count"])
        data["season"] = "unknown"
        data.loc[(data.period) >= 734 & (data.period <= 771), "season"] = "bfa4"
        data.loc[data.period >= 772, "season"] = "bfa4_postpatch"
        data_grouped = (
            data[["season", "spec", "level", "count"]]
            .groupby(["season", "spec", "level"])
            .sum()
        )
        data_grouped.reset_index(inplace=True)
        return data_grouped

    def get_weekly_top500(self):
        """Aggs 'period_rank' view by spec/period.

        The view needs to be pre-configured.
        """
        query = """
            SELECT period, dungeon, spec, count(spec) FROM period_rank
            LEFT JOIN roster
            ON period_rank.id = roster.run_id
            GROUP BY period, dungeon, spec
        """
        data = self.send_query_to_mdb(query, isfetch=True)
        return data
