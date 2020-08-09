"""Module for handling Blizzard API client secret and access token.""" 


import requests


class Credentials():

    def __init__(self, tokens_fp):
        """Inits with path to security tokens."""
        self.credentials = self.get_client_id_and_secret(tokens_fp) 
        self.access_token = self.create_access_token(self.credentials)

    @staticmethod
    def get_client_id_and_secret(tokens_file_path):
        """Loads Blizzard OAuth client id and secret from a text file.
        
        File must be stricktly formatted as two tab-delimited lines:
        
            client_id     client_id_string
            client_secret client_secret_sting
            
        Parameters
        ----------
        tokens_file_path : str
            file path of the file with client id and secret
            
        Returns
        -------
        credentials : dict
            dictionary containing client id and secret
        """
        
        credentials = {'client_id':None, 'client_secret':None}
        file = open(tokens_file_path, 'r')
        line = file.readline()
        while line:
            cargo = line.split()[1]
            if 'client_id' in line:
                credentials['client_id'] = cargo
            elif 'client_secret' in line:
                credentials['client_secret'] = cargo
            line = file.readline()
        file.close()
        return credentials
    
    @staticmethod
    def create_access_token(credentials):
        """Given a credentials dict, generates OAuth access token.
        
        Parameters
        ----------
        credentials : dict
            dict containing client id and secret
        
        Returns
        -------
        access_token : str
            OAuth access tokens that allows us to make calls to
            Blizzard API.
        """
        region = 'us'
        client_id = credentials['client_id']
        client_secret = credentials['client_secret']
        data = { 'grant_type': 'client_credentials' }
        response = requests.post('https://%s.battle.net/oauth/token' % region,
                                 data=data, auth=(client_id, client_secret))
        access_token = response.json()['access_token']
        return access_token 
