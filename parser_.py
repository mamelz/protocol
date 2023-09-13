"""Module implementing a dictionary-like class for the configuration
dictionary of a protocol, as parsed from the YAML file.
"""
from collections import UserDict
import yaml


class ProtocolConfiguration(UserDict):
    """Class representing the configuration of the protocol,
    parsed from YAML file.
    """
    _MANDATORY_KEYS = ("schedules",)

    def __init__(self, yaml_path: str):
        if not yaml_path.upper().endswith(".YAML"):
            raise ValueError(f"Config file {yaml_path} is not"
                             " in YAML format.")
        self._path = yaml_path
        with open(self._path, "r") as stream:
            options_dict = yaml.safe_load(stream)
        super().__init__(options_dict)
        for key in self._MANDATORY_KEYS:
            if key not in options_dict:
                raise ValueError("Protocol configuration is"
                                 f" missing key '{key}'")

    @property
    def global_options(self):
        global_options = {}
        for key in self._MANDATORY_KEYS:
            if key == "schedules":
                continue
            global_options[key] = self[key]
        return global_options

    @property
    def global_schedule_options(self):
        return self["global_schedule_options"]

    @global_schedule_options.setter
    def global_schedule_options(self, input):
        self["global_schedule_options"] = input
        return

    @property
    def schedules(self):
        return self["schedules"]

    @schedules.setter
    def schedules(self, input):
        self["schedules"] = input
        return
