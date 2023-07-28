"""Module implementing a dictionary-like class for the configuration
dictionary of a protocol, as parsed from the YAML file.
"""
from collections import UserDict
import yaml


class ProtocolConfiguration(UserDict):
    """Class for parsing options from YAML file."""
    _MANDATORY_KEYS = ("schedules", "io_options", "global_schedule_options")

    def __init__(self, yaml_path: str):
        if not yaml_path.upper().endswith(".YAML"):
            raise ValueError(f"Config file {yaml_path} is not"
                             " in YAML format.")
        self._path = yaml_path
        with open(self._path, "r") as stream:
            raw_options = yaml.safe_load(stream)
        super().__init__(raw_options)
        for key in self._MANDATORY_KEYS:
            if key in raw_options:
                continue
            self[key] = {}

    @property
    def global_options(self):
        global_options = {}
        for key in self._MANDATORY_KEYS:
            if key == "schedules":
                continue
            global_options[key] = self[key]
        return global_options

    def _generic_option_get(self, option_name):
        return self[option_name]

    def _generic_option_set(self, option_name, new_option):
        self[option_name] = new_option
        return

    @property
    def schedules(self):
        return self._generic_option_get("schedules")

    @schedules.setter
    def schedules(self, input):
        self._generic_option_set("schedules", input)
        return

    @property
    def io_options(self):
        return self._generic_option_get("io_options")

    @io_options.setter
    def io_options(self, input):
        self._generic_option_set("io_options", input)
        return

    @property
    def global_schedule_options(self):
        return self._generic_option_get("global_schedule_options")

    @global_schedule_options.setter
    def global_schedule_options(self, input):
        self._generic_option_set("global_schedule_options", input)
        return
