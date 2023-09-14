"""
Module containing all available keywords of the yaml file with their valid
data types or possible entries.
"""


SCHEDULE_KEYWORDS = {
    "global_options": dict,
    "start_time": float,
    "stages": list,
}

STAGE_KEYWORDS = {
    "global_options": dict,
    "type": ("evolution", "sweep", "default"),
    "propagation_time": float,
    "monitoring_stepsize": float,
    "monitoring": list,
    "tasks": list
}

TASK_KEYWORDS = {
    "global_options": dict,
    "routines": list
}

ROUTINE_KEYWORDS = {
    "name": str,
    "time": float,
    "kwargs": dict,
    "output": bool,
    "store_token": str
}
