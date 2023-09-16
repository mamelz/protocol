"""
Module containing all available keywords of the yaml file with their valid
data types or possible entries.
"""


_SCHEDULE_KEYWORDS_MANDATORY = {
    "stages": list,
    "start_time": float
}

_SCHEDULE_KEYWORDS_OPTIONAL = {
    "global_options": dict,
}

_STAGE_KEYWORDS_MANDATORY = {
    "tasks": list
}

_STAGE_KEYWORDS_OPTIONAL = {
    "global_options": dict,
    "monitoring": list,
    "monitoring_stepsize": float,
    "monitoring_numsteps": int,
    "propagation_time": float,
    "type": ("evolution", "sweep", "default"),
}

_TASK_KEYWORDS_MANDATORY = {
    "routines": list
}

_TASK_KEYWORDS_OPTIONAL = {
    "global_options": dict
}

_ROUTINE_KEYWORDS_MANDATORY = {
    "kwargs": dict,
    "name": str
}

_ROUTINE_KEYWORDS_OPTIONAL = {
    "output": bool,
    "store_token": str,
    "time": float
}

KEYWORDS = {
    "schedule": {
        "mandatory": _SCHEDULE_KEYWORDS_MANDATORY,
        "optional": _SCHEDULE_KEYWORDS_OPTIONAL
    },
    "stage": {
        "mandatory": _STAGE_KEYWORDS_MANDATORY,
        "optional": _STAGE_KEYWORDS_OPTIONAL
    },
    "task": {
        "mandatory": _TASK_KEYWORDS_MANDATORY,
        "optional": _TASK_KEYWORDS_OPTIONAL
    },
    "routine": {
        "mandatory": _ROUTINE_KEYWORDS_MANDATORY,
        "optional": _ROUTINE_KEYWORDS_OPTIONAL
    }
}
