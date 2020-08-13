"""Utility methods."""
import re

class Utils:
    """Collection of utility methods."""

    @staticmethod
    def get_realm_id_from_url(connected_realm_url):
        """Parsess realm ID from the json."""
        cap = re.findall('connected-realm\/(\d+)\?', connected_realm_url)       
        realm_id = cap[0]
        return realm_id
   
    @staticmethod
    def encode_region(region_slug):
        """Converts region token string into an int code."""
        codes = {'us': 1, 'kr': 2, 'eu': 3, 'tw': '4'}
        return codes[region_slug.lower()]

    @staticmethod
    def get_region_from_url(url):
        """Extracts region from call url."""
        pattern = re.compile('namespace=(dynamic|static)-(\w{2})$')
        cap = pattern.search(url)
        region_slug = cap[2]
        return region_slug

