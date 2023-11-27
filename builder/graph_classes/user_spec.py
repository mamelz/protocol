USER_GRAPH_CONFIG_DICT = {
    "ranks": {
        "NONE": {
            "NONE": {}
        },
        "Schedule": {
            "default": {
                "mandatory": {
                    "stages": {
                        "types": (list,)
                    }
                },
                "optional": {
                    "global_options": {
                        "types": (dict,),
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
                        "types": (list,),
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
                "optional-exclusive": (
                    {
                        "monitoring_stepsize": {
                            "types": (float,),
                            "default": None
                            },
                        "monitoring_numsteps": {
                            "types": (int,),
                            "default": None
                            }
                    },
                )
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
            },
            "predefined": {
                "mandatory": {
                    "name": {
                        "types": (str,)
                    }
                },
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
                    "store_token": {
                        "types": (str,),
                        "default": ""
                    },
                    "tag": {
                        "types": (str,),
                        "default": "USER"
                    }
                }
            },
            "evolution": {
                "mandatory": {
                    "routine_name": {
                        "types": (str,),
                    }
                },
                "mandatory-exclusive": (
                    {
                        "time": {
                            "types": (float,)
                        },
                        "localtime": {
                            "types": (float,)
                        }
                    },
                ),
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
                    "store_token": {
                        "types": (str,),
                        "default": ""
                    },
                    "tag": {
                        "types": (str,),
                        "default": "USER"
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
                    "store_token": {
                        "types": (str,),
                        "default": ""
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
        "NONE": -1,
        "Schedule": 0,
        "Stage": 1,
        "Task": 2,
        "Routine": 3
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
                "Task": ("default",),
                "Routine": ("regular",)
            }
        },
        "Stage": {
            "regular": {
                "Task": ("default", "predefined"),
                "Routine": ("regular")
            },
            "evolution": {
                "Task": ("default", "predefined"),
                "Routine": ("evolution", "monitoring", "propagation")
            }
        },
        "Task": {
            "default": {
                "Task": ("default",
                         "predefined"),
                "Routine": ("evolution",
                            "regular")
            },
            "predefined": ()
        },
        "Routine": {
            "regular": (),
            "evolution": (),
            "monitoring": (),
            "propagation": ()
        }
    }
}
