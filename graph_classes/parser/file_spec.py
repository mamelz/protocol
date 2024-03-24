from ..builder.user_spec import USER_GRAPH_CONFIG_DICT as _ucfg


FILE_CONFIG_DICT = {
    "ranks": {
        "NONE": {
            "NONE": {}
        },
        "file": {
            "yaml": {
                "optional": {
                    "schedules": {
                        "types": (list,),
                        "default": []
                    },
                    "tasks": {
                        "types": (list,),
                        "default": []
                    }
                }
            },
        },
        "task": {
            "default": {
                "mandatory": {
                    "name": {
                        "types": (str,)
                    },
                    **_ucfg["ranks"]["Task"]["default"]["mandatory"]
                },
                "optional": _ucfg["ranks"]["Task"]["default"]["optional"]
            }
        },
        "routine": {
            "task-regular": {
                **_ucfg["ranks"]["Routine"]["regular"]
            },
            "task-evolution": {
                "mandatory": {
                    **_ucfg["ranks"]["Routine"]["evolution"]["mandatory"]
                },
                "optional": {
                    "tasktime": {
                        "types": (float,),
                        "default": 0.0
                    },
                    **_ucfg["ranks"]["Routine"]["evolution"]["optional"],
                    "tag": {
                        "types": (str,),
                        "default": "TASK"
                    }
                }
            }
        }
    },
    "hierarchy": {
        "NONE": -1,
        "file": 0,
        "schedule": 1,
        "task": 1,
        "routine": 2
    },
    "allowed_children": {
        "NONE": {
            "NONE": {
                "file": ("yaml",)
            }
        },
        "file": {
            "yaml": {
                "schedule": ("default",),
                "task": ("default",)
            }
        },
        "schedule": {
            "default": {}
        },
        "task": {
            "default": {
                "routine": ("task-regular", "task-evolution")
            }
        },
        "routine": {
            "task-regular": {},
            "task-evolution": {}
        }
    }
}
