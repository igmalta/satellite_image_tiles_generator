import logging
import os
from typing import Union

import toml


class Conf:

    def __init__(self, config_file_path: str = "config.toml") -> None:
        self.config_file_path = config_file_path

    def load_conf_file(self):

        if not os.path.exists(self.config_file_path):
            logging.error(f"Could not find configuration file at: file [{self.config_file_path}]")

        return toml.load(self.config_file_path)

    def get_section(self, section_name: str) -> dict:
        config = self.load_conf_file()

        try:
            return config.get(section_name)
        except KeyError as e:
            logging.error(e)

    def get_property(self, section_name: str, prop_name: str) -> Union[str, list]:
        config = self.get_section(section_name)

        try:
            return config.get(prop_name)
        except KeyError as e:
            logging.error(e)
