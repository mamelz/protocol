"""General library settings."""
import os
from types import FunctionType


_FUNCTIONS_PATH = os.getenv("PROTOCOL_FUNCTIONS_PATH")

_SETTINGS = {
    "VERBOSE": False,
    "FUNCTIONS_PATH": _FUNCTIONS_PATH,
}


class Settings:
    """Class for general library settings."""
    VERBOSE = False
    FUNCTIONS_PATH: str = None

    @classmethod
    @property
    def _KEYS(cls):
        _keys = ()
        # find class attributes that are not methods
        for key, att in cls.__dict__.items():
            if key.startswith("__") or key == "_KEYS":
                continue
            if type(att) is FunctionType:   # ignore methods
                continue
            _keys += (key,)
        return _keys

    def __init__(self, dict: dict):
        self._settings = dict
        self._setOptionsFromDict()
        for key in self._KEYS:
            setattr(self, key, self._settings[key])

    def _setOptionsFromDict(self):
        for key, opt in self._settings.items():
            if key not in self._KEYS:
                raise KeyError(f"Unknown settings key '{key}'.")
            setattr(self, key, opt)
        return

    def check(self):
        """Check if library settings are complete. Returns bool."""
        _missing = ()
        for key in self._KEYS:
            if getattr(self, key) is None:
                _missing += (key,)
        if len(_missing) > 0:
            print(f"Missing settings: {[key for key in _missing]}")
            return False
        return True

    def setOption(self, key, value):
        self._settings[key] = value
        self._setOptionsFromDict()


SETTINGS = Settings(_SETTINGS)
