"""
Module containing all available keywords of the yaml file with their valid
data types or possible entries.
"""


SCHEDULE_KEYWORDS_MANDATORY = {
    "stages": list,
    "start_time": float
}

SCHEDULE_KEYWORDS_OPTIONAL = {
    "global_options": dict,
}

STAGE_KEYWORDS_MANDATORY = {
    "tasks": list
}

STAGE_KEYWORDS_OPTIONAL = {
    "global_options": dict,
    "monitoring": list,
    "monitoring_stepsize": float,
    "propagation_numsteps": int,
    "propagation_time": float,
    "type": ("evolution", "sweep", "default"),
}

TASK_KEYWORDS_MANDATORY = {
    "routines": list
}

TASK_KEYWORDS_OPTIONAL = {
    "global_options": dict
}

ROUTINE_KEYWORDS_MANDATORY = {
    "kwargs": dict,
    "name": str
}

ROUTINE_KEYWORDS_OPTIONAL = {
    "output": bool,
    "store_token": str,
    "time": float
}
