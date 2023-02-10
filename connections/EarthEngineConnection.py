import logging

import ee
from google.oauth2.service_account import Credentials

from conf.config import Conf


class EarthEngineConnection:

    def __init__(self) -> None:
        self.earth_engine_account = Conf().get_section("earth_engine_account")

    def _credentials(self) -> Credentials:
        return ee.ServiceAccountCredentials(
            self.earth_engine_account.get("service_account"),
            self.earth_engine_account.get("private_key_json"))

    def get_ee_connection(self):
        try:
            return ee.Initialize(self._credentials())
        except Exception as e:
            logging.error("Can't get connection from Earth Engine")
            logging.error(f"Exception {e}", exc_info=True)
