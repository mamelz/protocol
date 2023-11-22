from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..graph.core import GraphNode

import itertools

import numpy as np

from .errors import (
    StageProcessingError
)


def process_evolution(stage: GraphNode):
    OPTIONS: dict = stage._options
    propagation_time = OPTIONS["propagation_time"]
    start_time = stage.root._options["start_time"]
    propagation_numsteps = _get_numsteps(OPTIONS)
    stop_time = start_time + propagation_time

    monitoring_routines = _get_monitoring_options(OPTIONS)
    extra_routine_times = _get_extra_routine_times(
        start_time, stop_time, stage)
    mon_routine_times = ()
    if monitoring_routines != ():
        mon_routine_times = np.linspace(start_time,
                                        stop_time,
                                        propagation_numsteps,
                                        endpoint=True)
    timesteps_gen = _make_timesteps_gen(extra_routine_times,
                                        mon_routine_times)

    def propagation_routine(timestep: float):
        return {
            "type": "propagation",
            "step": timestep,
        }

    if stage.num_children != 0:
        new_routines_dict = _make_new_routines_dict(stage, timesteps_gen,
                                                    monitoring_routines,
                                                    mon_routine_times,
                                                    propagation_routine)
    # if stage configuration contained no tasks, create routines in empty task
    else:
        stage.add_children_from_options()
        new_rout_tup = ()
        prior_time = start_time
        for time in _make_timesteps_gen(extra_routine_times,
                                        mon_routine_times):
            if prior_time != time:
                new_rout_tup += (
                    propagation_routine(time - prior_time),)
            new_rout_tup += monitoring_routines
            prior_time = time

        new_routines_dict = {stage.children[0].ID: new_rout_tup}

    for task in stage.children:
        task.set_children_from_options(new_routines_dict[task.ID])

    # at end of time evolution, always return state
    stage.children[-1].add_children_from_options(
        {"routine_name": "_return_state",
         "time": stop_time,
         "store_token": "LAST_STATE",
         "tag": "AUTOMATIC",
         "type": "evolution"})

    return stop_time


def _get_numsteps(options: dict) -> int:
    propagation_time = options["propagation_time"]
    try:
        propagation_stepsize = options["monitoring_stepsize"]
        propagation_numsteps = int(propagation_time //
                                   propagation_stepsize) + 1
    except KeyError:
        try:
            propagation_numsteps = options["monitoring_numsteps"]
        except KeyError:
            pass

    return propagation_numsteps


def _get_monitoring_options(options: dict):
    try:
        mon_rout_opts: tuple[dict] = options["monitoring"]
    except KeyError:
        mon_rout_opts = []
    for rout_opts in mon_rout_opts:
        rout_opts["type"] = "monitoring"

    return tuple(mon_rout_opts)


def _get_extra_routine_times(start_time, stop_time, stage: GraphNode):
    ext_rout_times = (start_time,)
    last_rout_time = None

    for routine in stage.leafs:
        routine_time = routine._options["time"]
        if not start_time <= routine_time <= stop_time:
            raise StageProcessingError(
                f"Stage {stage.ID}: Routine time outside"
                " of stage time range.")
        if last_rout_time is not None and (routine_time < last_rout_time):
            raise StageProcessingError(
                f"Stage {stage.ID}: Routine times between"
                " tasks must not overlap.")
        ext_rout_times += (routine_time,)
        last_rout_time = routine_time

    return ext_rout_times


def _make_timesteps_gen(ext_rout_times, mon_time_arr):
    timesteps_arr = np.array(ext_rout_times)
    timesteps_arr = np.append(timesteps_arr, mon_time_arr)
    timesteps_arr = np.unique(timesteps_arr)

    return (time for time in timesteps_arr)


def _make_new_routines_dict(stage: GraphNode, tsteps, mon_routs,
                            mon_rout_times, propagation_routine):

    new_routines_dict = {task.ID: () for task in stage.children}
    time = next(tsteps)
    prior_time = time
    _first_loop_token = True
    _monitoring_token = True
    for task in stage.children:
        for routine in task.children:
            if routine._options["time"] > prior_time and (
                    not _first_loop_token):
                time = next(tsteps)
            while time < routine.options["time"]:
                if not _first_loop_token and prior_time != time:
                    new_routines_dict[task.ID] += (propagation_routine(
                        time - prior_time),)
                    _monitoring_token = True
                if time in mon_rout_times and _monitoring_token:
                    new_routines_dict[task.ID] += mon_routs
                _monitoring_token = False
                _first_loop_token = False
                prior_time = time
                time = next(tsteps)

            if prior_time != time:
                new_routines_dict[task.ID] += (propagation_routine(
                    time - prior_time),)
                _monitoring_token = True
            if time in mon_rout_times and _monitoring_token:
                new_routines_dict[task.ID] += mon_routs
                _monitoring_token = False
            new_routines_dict[task.ID] += (routine._options,)
            prior_time = time
            _first_loop_token = False

    # create remaining timesteps in last task
    def delta_t_gen():
        nonlocal prior_time
        for time in tsteps:
            yield time - prior_time
            prior_time = time

    remaining_routs_gen = ((propagation_routine(delta_t), *mon_routs)
                           for delta_t in delta_t_gen())
    new_routines_dict[stage.children[-1].ID] += tuple(
        itertools.chain.from_iterable(remaining_routs_gen))

    return new_routines_dict
