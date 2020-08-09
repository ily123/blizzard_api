import mplus_db
import time
import requests
import blizzard_api
import sys

access_token = 'USptz7Deyvaqd7Dumh2HE4yHTPM32R9hiA'


#query and parse the existing table


def populate_realm_table():
    
    regions = ['us', 'eu', 'kr', 'tw']
    
    realm_records = []
    for region in regions:

        call_factory = blizzard_api.BlizzardCallFactory(region = region, 
            access_token = access_token)
        realm_index_call = call_factory.get_connected_realm_index_call()
        
        response = requests.get(realm_index_call)
        if response.status_code != 200:
            print('Something has gone wrong')
            print(response.status_code)
            print(respose.reason)
            sys.exit()
        
        realm_index_json = response.json()
        parser = blizzard_api.BlizzardJsonParser()
        realm_ids = parser.parse_connected_realm_index_json(realm_index_json)

        print('There are %d realms in region [%s]:' % (len(realm_ids),
                                                       region.upper()))

        realm_jsons = []
        for i, cluster_id in enumerate(realm_ids):
            print('\r----Quering Blizzard API for each realm.... %d out of %d'
                % (i+1, len(realm_ids)), end = '')
            realm_call = call_factory.get_connected_realm_call(
                realm_id = cluster_id)
            response = requests.get(realm_call)
            if response.status_code != 200:
                print("Fetch failed for realm %d (code %d)" % (cluster_id,
                    response.status_code))
            realm_jsons.append(response.json())
            time.sleep(0.1)
        print('')   

        for i, json in enumerate(realm_jsons):
            print('\r----Parsing response content............... %d out of %d'
                % (i+1, len(realm_jsons)), end = '')
            realm_records_ = parser.parse_connected_realm_json(json)
            for record in realm_records_:
                realm_records.append(record)
        print('') 
        print('*')
    print('Aggregating data for SQL insert query') 
    realm_formatter = blizzard_api.RealmRecordSQLFormatter(realm_records)
    realm_values_as_sql_string = realm_formatter.generate_sql_value_string()
    realm_query = blizzard_api.QueryFactory().construct_insert_query(
        destination_table='realm', values = realm_values_as_sql_string)
    
    print('*\nConnecting to MDB')
    mdb = mplus_db.MplusDB('.db_config')
    conn = mdb.connect()
    cursor = conn.cursor()
    print('*\nInserting realm data into MDB')
    cursor.execute(realm_query)
    cursor.close()
    conn.commit()
    conn.close()
    
    print('*\nSuccess? I think..... Exiting.')

if __name__ == '__main__':
    populate_realm_table()
