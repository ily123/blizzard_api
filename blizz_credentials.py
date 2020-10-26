"""Module for generating Blizzard API access token.

    Usage
    -----

    import blizz_credentials

    fp = "client_info.ini"
    auth = blizz_credentials.Credentials(fp)
    api_token = auth.access_token

"""


import configparser
import os.path
import time
from typing import Dict

import requests


class Credentials:
    """Blizzard API token getter.

    Attributes
    ----------
        access_token : str
            Blizzard API access token (generated on init)
    """

    def __init__(self, auth_tokens_fp: str):
        """Inits with .ini file containing OAuth client tokens.

        Parameter
        ---------
        auth_tokens_fp : str
            path to .ini file formated as follows:

            [BLIZZARD]
            client_id = client_id_string
            client_secret = client_secret_sting
        """
        self.query_attempts = 0
        self.credentials = self._parse_client_id_and_secret(auth_tokens_fp)
        self.access_token = self._create_access_token()

    @staticmethod
    def _parse_client_id_and_secret(auth_tokens_fp: str) -> Dict[str, str]:
        """Loads Blizzard OAuth client id and secret from a .ini file.

        Parameters
        ----------
        auth_tokens_fp : str
            file path of the .ini file with client id and secret

        Returns
        -------
        credentials : dict
            dictionary containing client id and secret
        """
        if not os.path.exists(auth_tokens_fp):
            raise FileNotFoundError("Config file not found '%s'" % auth_tokens_fp)
        parser = configparser.ConfigParser()
        parser.read(auth_tokens_fp)
        credentials = {
            "client_id": parser["BLIZZARD"]["client_id"],
            "client_secret": parser["BLIZZARD"]["client_secret"],
        }
        return credentials

    @staticmethod
    def _query_blizzard(credentials: Dict[str, str]) -> requests.Response:
        """Sends auth token request to Blizzard.

        Parameters
        ----------
        credentials : dict
            dict containing client id and secret

        Returns
        -------
        response
            requests response object
        """
        region = "us"
        client_id = credentials["client_id"]
        client_secret = credentials["client_secret"]
        data = {"grant_type": "client_credentials"}
        response = requests.post(
            "https://%s.battle.net/oauth/token" % region,
            data=data,
            auth=(client_id, client_secret),
        )
        return response

    def _create_access_token(self) -> str:
        """Given a credentials dict, generates OAuth access token.

        Returns
        -------
        access_token : str
            OAuth access tokens that allows us to make calls to
            Blizzard API.
        """
        response = None
        try:
            response = self._query_blizzard(self.credentials)
        except BaseException as e:
            self.query_attempts += 1
            print("Error getting auth token: ", str(e))
            if self.query_attempts < 5:
                print("Sleep 1, then retry. Re-try %d" % self.query_attempts)
                time.sleep(1)
                response = self._query_blizzard(self.credentials)
            else:
                raise ConnectionError("Tried 5 times and failed to get auth token.")
        access_token = response.json()["access_token"]
        return access_token
