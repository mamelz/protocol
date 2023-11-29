from ...builder.graph_classes.user_spec import USER_GRAPH_CONFIG_DICT as _ucfg
from ...graph.spec import GraphSpecification


_usr_graph_cfg = GraphSpecification(_ucfg)
INPUT_CONFIG_DICT = {
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
        "schedule": {
            "default": {
                **_usr_graph_cfg.ranks["Schedule"].types["default"].dictionary
            }
        },
        "task": {
            "default": {
                "mandatory": {
                    "name": {
                        "types": (str,)
                    },
                    **_usr_graph_cfg.ranks["Task"].types[
                        "default"].options.mandatory
                },
                "optional": _usr_graph_cfg.ranks["Task"].types[
                    "default"].options.optional
            }
        },
        "routine": {
            "task-regular": {
                **_usr_graph_cfg.ranks["Routine"].types["regular"].dictionary
            },
            "task-evolution": {
                "mandatory": {
                    **_usr_graph_cfg.ranks["Routine"].types[
                        "evolution"].options.mandatory
                },
                "optional": {
                    "tasktime": {
                        "types": (float,),
                        "default": 0.0
                    },
                    **_usr_graph_cfg.ranks["Routine"].types[
                        "evolution"].options.optional,
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
