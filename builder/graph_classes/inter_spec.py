INTER_GRAPH_CONFIG_DICT = {
    "ranks": {
        "NONE": {
            "NONE": {}
        },
        "Schedule": {
            "default": {
                "mandatory": {
                    "start_time": {
                        "types": (float,)
                    }
                }
            }
        },
        "Stage": {
            "regular": {
                "mandatory": {
                    "num_routines": {
                        "types": (int,)
                    }
                }
            },
            "evolution": {
                "mandatory": {
                    "propagation_time": {
                        "types": (float,)
                    },
                    "start_time": {
                        "types": (float,)
                    },
                    "monitoring": {
                        "types": (list,)
                    },
                    "monitoring_numsteps": {
                        "types": (int,)
                    },
                    "num_routines": {
                        "types": (int,)
                    }
                }
            }
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
                    "time": {
                        "types": (float,)
                    },
                    "args": {
                        "types": (list,)
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
                "Stage": ("regular", "evolution"),
            }
        },
        "Stage": {
            "regular": {
                "Routine": ("regular",)
            },
            "evolution": {
                "Routine": ("evolution",)
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
