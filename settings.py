"""General library settings."""
import os


_FUNCTIONS_PATH = os.getenv("PROTOCOL_FUNCTIONS_PATH")
_GRAPH_CONFIG_DICT = {
    "ranks": {
        "Schedule": {
            "default": {
                "mandatory": {},
                "optional": {
                    "global_options": {
                        "types": (dict,),
                        "default": {}
                    },
                    "stages": {
                        "types": (list,),
                        "default": {}
                    },
                    "start_time": {
                        "types": (float,),
                        "default": 0.0
                    }
                }
            }
        },
        "Stage": {
            "regular": {
                "mandatory": {},
                "optional": {
                    "global_options": {
                        "types": (dict,),
                        "default": {}
                    },
                    "tasks": {
                        "types": (dict,),
                        "default": {}
                    },
                }
            },
            "evolution": {
                "mandatory": {
                    "propagation_time": {
                        "types": (float,)
                    },
                },
                "optional": {
                    "global_options": {
                        "types": (dict,),
                        "default": {}
                    },
                    "monitoring": {
                        "types": (list,),
                        "default": []
                    },
                    "tasks": {
                        "types": (list,),
                        "default": []
                    }
                },
                "optional-exclusive": [
                    {
                        "monitoring_stepsize": {
                            "types": (float,),
                            "default": None
                        }
                    },
                    {
                        "monitoring_numsteps": {
                            "types": (int,),
                            "default": None
                        }
                    }
                ]
            }
        },
        "Task": {
            "default": {
                "mandatory": {},
                "optional": {
                    "global_options": {
                        "types": (dict,),
                        "default": {}
                    },
                    "routines": {
                        "types": (list,),
                        "default": []
                    }
                }
            }
        },
        "Routine": {
            "regular": {
                "mandatory": {
                    "routine_name": {
                        "types": (str,),
                    }
                },
                "optional": {
                    "args": {
                        "types": (list,),
                        "default": ()
                    },
                    "description": {
                        "types": (str,),
                        "default": None
                    },
                    "kwargs": {
                        "types": (dict,),
                        "default": {}
                    },
                    "live_tracking": {
                        "types": (bool,),
                        "default": False
                    },
#                    "output": {
#                        "types": (bool,),
#                        "default": True
#                    },
                    "store": {
                        "types": (bool,),
                        "default": True
                    },
                    "store_token": {
                        "types": (str,),
                        "default": None
                    },
                    "tag": {
                        "types": (str,),
                        "default": None
                    }
                }
            },
            "evolution": {
                "mandatory": {
                    "routine_name": {
                        "types": (str,),
                    },
                    "time": {
                        "types": (float,),
                    }
                },
                "optional": {
                    "args": {
                        "types": (list,),
                        "default": ()
                    },
                    "description": {
                        "types": (str,),
                        "default": None
                    },
                    "kwargs": {
                        "types": (dict,),
                        "default": {}
                    },
                    "live_tracking": {
                        "types": (bool,),
                        "default": False
                    },
#                    "output": {
#                        "types": (bool,),
#                        "default": True
#                    },
                    "store": {
                        "types": (bool,),
                        "default": True
                    },
                    "store_token": {
                        "types": (str,),
                        "default": None
                    },
                    "tag": {
                        "types": (str,),
                        "default": None
                    }
                }
            },
            "monitoring": {
                "mandatory": {
                    "routine_name": {
                        "types": (str,)
                    }
                },
                "optional": {
                    "args": {
                        "types": (list,),
                        "default": ()
                    },
                    "description": {
                        "types": (str,),
                        "default": None
                    },
                    "kwargs": {
                        "types": (dict,),
                        "default": {}
                    },
                    "live_tracking": {
                        "types": (bool,),
                        "default": False
                    },
#                    "output": {
#                        "types": (bool,),
#                        "default": True
#                    },
                    "store": {
                        "types": (bool,),
                        "default": True
                    },
                    "store_token": {
                        "types": (str,),
                        "default": None
                    },
                }
            },
            "propagation": {
                "mandatory": {
                    "step": {
                        "types": (float,)
                    }
                },
                "optional": {
                    "TYPE": {
                        "types": (str,),
                        "default": None
                    }
                }
            }
        }
    },
    "hierarchy": {
        0: "Schedule",
        1: "Stage",
        2: "Task",
        3: "Routine"
    },
    "allowed_types": {
        "NONE": {
            "NONE": {
                "Schedule"
            }
        },
        "Schedule": {
            "default": {
                "Stage": ("regular", "evolution"),
                "Task": ("default",),
                "Routine": ("regular",)
            }
        },
        "Stage": {
            "regular": {
                "Task": ("default",),
                "Routine": ("regular")
            },
            "evolution": {
                "Task": ("default",),
                "Routine": ("evolution", "monitoring", "propagation")
            }
        },
        "Task": {
            "default": {
                "Routine": ("evolution",
                            "monitoring",
                            "propagation",
                            "regular")
            }
        }
    }
}

_SETTINGS = {
    "VERBOSE": False,
    "FUNCTIONS_PATH": _FUNCTIONS_PATH,
    "GRAPH_CONFIG": _GRAPH_CONFIG_DICT
}


class Settings:
    """Class for general library settings."""
    VERBOSE: bool = False
    FUNCTIONS_PATH: str = None
    GRAPH_CONFIG: dict

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


SETTINGS = Settings(_SETTINGS)
