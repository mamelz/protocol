"""General library settings."""
import os

_FUNCTIONS_PATH = os.getenv("PROTOCOL_FUNCTIONS_PATH")
_SETTINGS_DICT = {
    "VERBOSE": False,
    "FUNCTIONS_PATH": _FUNCTIONS_PATH,
}


class Settings:
    """Class for general library settings."""
    VERBOSE: bool = False
    FUNCTIONS_PATH: str = None

    def __init__(self, dict: dict):
        self._settings = dict
        self._set_options_from_dict()
        for key in self.__annotations__:
            setattr(self, key, self._settings[key])

    def _set_options_from_dict(self):
        for key, opt in self._settings.items():
            if key not in self.__annotations__:
                raise KeyError(f"Unknown settings key '{key}'.")
            setattr(self, key, opt)
        return

    def check(self):
        """Check if library settings are complete. Returns bool."""
        _missing = ()
        for key in self.__annotations__:
            if getattr(self, key) is None:
                _missing += (key,)
        if len(_missing) > 0:
            print(f"Missing settings: {[key for key in _missing]}")
            return False
        return True

    def set_option(self, key, value):
        self._settings[key] = value
        self._set_options_from_dict()


SETTINGS = Settings(_SETTINGS_DICT)
