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
            }
        },
        "Schedule": {
            "default":
                _usr_graph_cfg.ranks["Schedule"].types["default"].dictionary
        },
        "Task": {
            "default": {
                "mandatory": {
                    "name": {
                        "types": (str,)
                    }
                },
                "optional": _usr_graph_cfg.ranks["Task"].types[
                    "default"].options.optional
            }
        }
    },
    "hierarchy": {
        "NONE": -1,
        "file": 0,
        "Schedule": 1,
        "Task": 1,
    },
    "allowed_children": {
        "NONE": {
            "NONE": {
                "file": ("yaml",)
            }
        },
        "file": {
            "yaml": {
                "Schedule": ("default",),
                "Task": ("default",)
            }
        },
        # inner structure of the entries is handled by builder
        "Schedule": {
            "default": {}
        },
        "Task": {
            "default": {},
        }
    }
}
