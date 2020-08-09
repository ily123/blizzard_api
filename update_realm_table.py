import sys
import requests
import pandas as pd
import blizzard_api
import blizzard_credentials
import mplusdb
import logging


class Driver:
    """Class to update realm table in the MDB."""
    __region_encoder = {'us': 1, 'kr': 2, 'eu': 3, 'tw': 4}

    def __init__(self, region):
        self.region = region
        self.region_code = self.__region_encoder[region]
        self.access_token = self.get_access_token()
        self.cluster_ids = None
        self.call_factory = blizzard_api.CallFactory(region = region, 
            access_token = self.access_token)
        self.parser = blizzard_api.ResponseParser()
        self.mdb_handle = mplusdb.MplusDatabase('.db_config')
        self.realms = None
    

    @staticmethod
    def get_access_token():
        """Fetches Blizzard's API access token."""
        authorization = blizzard_credentials.Credentials('.api_tokens')
        access_token = authorization.access_token
        return access_token

    def get_cluster_ids(self):
        """Fetch list of realm clusters in region."""
        realm_index_call = self.call_factory.get_connected_realm_index_call()
        response = requests.get(realm_index_call)
        if response.status_code != 200:
            print('Something has gone wrong with fetching Blizz data.')
            print('Status code:', response.status_code)
            print('Reason:', respose.reason)
            sys.exit()
        realm_index_json = response.json()
        cluster_ids = self.parser.parse_connected_realm_index_json(
            realm_index_json)
        self.cluster_ids = cluster_ids

    def query_each_cluster(self):
        """Query each realm cluster to get individual realm information."""
        if not self.cluster_ids:
            raise Exception('cluster list is empty; get cluster ids first')
        realms = []
        for cluster_id in self.cluster_ids:
            cluster_json = self.get_realm_cluster_data(cluster_id) 
            realm_records = self.parser.parse_connected_realm_json(
                cluster_json)
            realms = realms + realm_records
        self.realms = realms

    def get_realm_cluster_data(self, cluster_id):
        """Queries realm cluster for its substituent realms info."""
        realm_call = self.call_factory.get_connected_realm_call(
            realm_id = cluster_id)
        response = requests.get(realm_call)
        if response.status_code != 200:
            print("Fetch failed for realm %d (code %d)" % (cluster_id,
                response.status_code))
            sys.exit()
        return response.json()
    
    def collate_realms_data_as_df(self):
        """Aggs realms records into a pandas df."""
        if not self.realms:
            raise Exception('realms records has not fetched')
        realm_data = []
        for realm in self.realms:
            realm_data.append(realm.get_data_for_database_table_as_dict())
        return pd.DataFrame(realm_data)

    def update_mdb_to_latest_data(self):
        """Update MDBi with newly-fetched data, if different."""
        latest_realms_data = self.collate_realms_data_as_df()
        current_realms_data = self.fetch_mdb_realm_table()
        region_mask = current_realms_data.region == self.region_code
        current_realms_data = current_realms_data[region_mask]
       
        #patch for error Blizzard introduced on Aug 5 2020. Will fix later. 
        if self.region == 'eu':
            mask = latest_realms_data.cluster_id == 567
            latest_realms_data = latest_realms_data[~mask]

        # if the latest realm count is different from what's in the DB, 
        # it can be one of two things:
        # 1) Blizzard released a new realm - hasn't happened in ~8 years
        # 2) Blizzard erased an existing realm - has never happened
        # So I'll just make an exception for this very unlikely scenario
        # and if it ever happens i'll write the logic for it then (lay-hay-zee)
        if len(current_realms_data) != len(latest_realms_data):

            print('These realms are not found in one of the tables:')
            print(pd.concat([current_realms_data,
                     latest_realms_data]).drop_duplicates(keep=False))
            raise Exception(('Number of realms has changed: '
                 'Has blizzard deleted/added a shard? Check the news!'))

        # The change that is likely to happen is different realms merging
        # into a single cluster (happens a lot, as WoW's population gets
        # smaller). So we will check if cluster ids have been changed,
        # and then update the database. (Note: a stand-alone realm has
        # its cluster_id = realm_id. A realm merged with other realms
        # gets a new cluster_id that is shared within the realm cluster.)
        reassigned = self.get_cluster_diff(current_realms_data,
            latest_realms_data) 
        if len(reassigned) == 0:
            return 'Nothing to change in region %s' % self.region
        else:
            self.update_cluster_assignment(reassigned)
            return 'cluster id updated for realms: %s' % ','.join(
                list(reassigned.name))

    def get_cluster_diff(self, current_realms_data, latest_realms_data):
        """Returns realms whose cluster ids have changed."""
        merged = pd.merge(
            current_realms_data[['name', 'realm_id', 'cluster_id']],
            latest_realms_data[['name', 'realm_id', 'cluster_id']],
            how='outer',
            left_on = ['realm_id', 'name'],
            right_on = ['realm_id', 'name'], suffixes=('_current', '_latest'))
        merged['cluster_reassigned'] = \
            merged.cluster_id_current != merged.cluster_id_latest
        reassigned = merged[merged.cluster_reassigned]
        if len(reassigned) == 0:
            return []
        else:
            return reassigned 

    def update_cluster_assignment(self, reassigned):
        """Updates database table with new cluster ids."""
        conn = self.mdb_handle.connect()
        cursor = conn.cursor()        
        reassigned.to_dict('list')
        for realm in reassigned.to_dict('index').values():
            name = realm['name']
            realm_id = realm['realm_id']
            new_cluster_id = realm['cluster_id_latest']
            sql_templ = ('UPDATE realm SET cluster_id = %s '
                         'WHERE realm_id = %s and region = %s')
            sql_query = sql_templ % (new_cluster_id, realm_id,
                self.region_code)
            cursor.execute(sql_query)
        conn.commit()
        cursor.close()
        conn.close()

    def fetch_mdb_realm_table(self):
        """Fetches realm table from MDB."""
        realms = self.mdb_handle.get_utility_table('realm')
        return realms 


def setup_logger(log_fp):
    """Sets up logger for the script."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(log_fp)
    formatter = logging.Formatter(
        '%(asctime)s : %(name)s : %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
    

def main():
    log_fp = 'logs/realm_update.log'
    logger = setup_logger(log_fp)
    regions = ['us', 'kr', 'tw']
    regions = ['eu']
    for region in regions:
        logger.info('updating realm for region %s' % region)
        driver = Driver(region) 
        driver.get_cluster_ids()    
        driver.query_each_cluster()
        result_msg = driver.update_mdb_to_latest_data()
        logger.info(result_msg)
    print('Realm update done. See log at %s' % log_fp)


if __name__ == '__main__':
    main()
