RUN_GRAPH_CONFIG_DICT = {
    "ranks": {
        "NONE": {
            "NONE": {}
        },
        "Schedule": {
            "default": {}
            },
        "Stage": {
            "regular": {},
            "evolution": {
                "mandatory": {
                    "propagation_time": {
                        "types": (float,)
                    },
                    "num_routines": {
                        "types": (int,)
                    },
                },
            },
        },
        "Routine": {
            "regular": {
                "mandatory": {
                    "routine_name": {
                        "types": (str,),
                    },
                    "args": {
                        "types": (tuple,)
                    },
                    "description": {
                        "types": (str,)
                    },
                    "kwargs": {
                        "types": (dict,)
                    },
                    "live_tracking": {
                        "types": (bool,)
                    },
                    "store": {
                        "types": (bool,)
                    },
                    "store_token": {
                        "types": (str,)
                    },
                    "tag": {
                        "types": (str,)
                    }
                }
            },
            "evolution": {
                "mandatory": {
                    "routine_name": {
                        "types": (str,)
                    },
                    "time": {
                        "types": (float,)
                    },
                    "args": {
                        "types": (tuple,)
                    },
                    "description": {
                        "types": (str,)
                    },
                    "kwargs": {
                        "types": (dict,)
                    },
                    "live_tracking": {
                        "types": (bool,)
                    },
                    "store": {
                        "types": (bool,)
                    },
                    "store_token": {
                        "types": (str,)
                    },
                    "tag": {
                        "types": (str,)
                    }
                }
            },
            "monitoring": {
                "mandatory": {
                    "routine_name": {
                        "types": (str,)
                    },
                    "store_token": {
                        "types": (str,)
                    },
                    "time": {
                        "types": (float,)
                    }
                },
                "optional": {
                    "args": {
                        "types": (list,),
                        "default": ()
                    },
                    "description": {
                        "types": (str,),
                        "default": "no description"
                    },
                    "kwargs": {
                        "types": (dict,),
                        "default": {}
                    },
                    "live_tracking": {
                        "types": (bool,),
                        "default": False
                    },
                    "store": {
                        "types": (bool,),
                        "default": True
                    },
                    "tag": {
                        "types": (str,),
                        "default": "MONITORING"
                    }
                }
            },
            "propagation": {
                "mandatory": {
                    "time": {
                        "types": (float,)
                    },
                    "step": {
                        "types": (float,)
                    }
                }
            }
        }
    },
    "hierarchy": {
        "NONE": -1,
        "Schedule": 0,
        "Stage": 1,
        "Routine": 2
    },
    "allowed_children": {
        "NONE": {
            "NONE": {
                "Schedule": ("default",)
            }
        },
        "Schedule": {
            "default": {
                "Stage": ("default",),
            }
        },
        "Stage": {
            "regular": {
                "Routine": ("regular")
            },
            "evolution": {
                "Routine": ("evolution", "propagation")
            }
        },
        "Routine": {
            "regular": (),
            "evolution": (),
            "monitoring": (),
            "propagation": ()
        }
    }
}
