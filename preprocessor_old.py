"""Module containing classes for preprocessing of protocol options."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import Protocol
    from .graph import GraphNode
    from .schedule import Schedule

from abc import ABC, abstractmethod
import numpy as np


class PreprocessorABC(ABC):
    """
    Interface for Preprocessors. They process options
    of the given objects, modifying them if needed.
    """
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def run(self):
        """Performs the preprocessing."""
        pass


class ProtocolPreprocessor(PreprocessorABC):
    """Class for preprocessing the entire protocol."""
    def __init__(self, protocol: Protocol, forced_start_time: float = None):
        self._protocol = protocol
        self._graph_preprocessors: tuple[SchedulePreprocessor] = ()
        self._start_time = forced_start_time
        for schedule in self._protocol._schedules:
            self._graph_preprocessors += (
                SchedulePreprocessor(schedule, self._start_time),)

    def run(self):
        for preproc in self._graph_preprocessors:
            preproc.run()
        return


class SchedulePreprocessor(PreprocessorABC):
    """Class for preprocessing a schedule of a protocol."""
    def __init__(self, schedule: Schedule, forced_start_time: float = None):
        self._schedule = schedule
        self._forced_start_time = forced_start_time
        self._graph_preprocessor = GraphPreprocessor(
            self._schedule.root, self._schedule.start_time)

    def run(self):
        if self._forced_start_time is not None:
            self._schedule.set_start_time(self._forced_start_time)
            self._schedule._reinitialize_system()
        if not self._schedule._system_initialized:
            raise RuntimeError("System not initialized.")

        if not hasattr(self._schedule._system, "_propagator"):
            for stage in self._schedule.get_rank(1):
                if stage._options["type"] == "evolution":
                    raise ValueError("Schedule contains evolution stages but"
                                     " no propagator was set.")
        self._graph_preprocessor.run()
        for routine in self._schedule.leafs:
            if "kwargs" not in routine._options:
                routine._options["kwargs"] = {}
        self._schedule.graph_initialized = True
        return


class GraphPreprocessor(PreprocessorABC):
    """Class for preprocessing a schedule node of a graph."""
    def __init__(self, graph: GraphNode, start_time: float):
        self._graph = graph
        self._start_time = start_time
        self._stage_preprocessors = (
            StagePreprocessor(stage) for stage in self._graph.children)

    def run(self):
        start_time = self._start_time
        for preproc in self._stage_preprocessors:
            preproc.set_start_time(start_time)
            start_time = preproc.run()
        return


class StagePreprocessor(PreprocessorABC):
    """
    Class for preprocessing a stage node. In evolution stages, monitoring and
    propagation routines will automatically be created.
    """
    @classmethod
    def check_node_empty(cls, node: GraphNode):
        if node.isleaf:
            return node._options == {}
        if node.num_children == 0:
            return True
        for child in node.children:
            if not cls.check_node_empty(child):
                return False
        return True

    def __init__(self, stage: GraphNode):
        self._stage = stage
        self._start_time = None

    def _process_evolution(self):
        propagation_time = self._stage.options["propagation_time"]

        if all(key in self._stage._options for key in
               ("monitoring_stepsize", "monitoring_numsteps")):
            raise ValueError("Only one of 'monitoring_stepsize' and"
                             " 'monitoring_numsteps' can be specified.")

        if all(key not in self._stage._options for key in
               ("monitoring_stepsize", "monitoring_numsteps")):
            raise ValueError("One of 'monitoring_stepsize' and"
                             "'monitoring_numsteps' must be specified.")

        try:
            propagation_stepsize = self._stage.options["monitoring_stepsize"]
            propagation_numsteps = int(propagation_time //
                                       propagation_stepsize) + 1
        except KeyError:
            pass
        try:
            propagation_numsteps = self._stage.options["monitoring_numsteps"]
        except KeyError:
            pass

        stage_stop_time = self._start_time + propagation_time

        try:
            monitoring_routines: tuple[dict] =\
                self._stage.options["monitoring"]
        except KeyError:
            monitoring_routines = []
        for routine in monitoring_routines:
            routine["type"] = "MONITORING"
        monitoring_routines = tuple(monitoring_routines)

        extra_routine_times = (self._start_time,)
        last_routine_time = None
        for task in self._stage.children:
            for routine in task.children:
                routine.options["type"] = "evolution"
                routine_time = routine.options["time"]
                if routine_time < self._start_time or (
                        routine_time > stage_stop_time):
                    raise ValueError(
                        f"Stage {self._stage.ID.local}: Routine time outside"
                        " of stage time range.")
                if last_routine_time is not None and (
                        routine_time < last_routine_time):
                    raise ValueError(
                        f"Stage {self._stage.ID.local}: Routine times between"
                        " tasks must not overlap.")
                extra_routine_times += (routine_time,)
            last_routine_time = routine_time

        timesteps_arr = np.array(extra_routine_times)
        monitoring_arr = ()
        if monitoring_routines != ():
            monitoring_arr = np.linspace(self._start_time,
                                         self._start_time + propagation_time,
                                         propagation_numsteps,
                                         endpoint=True)
            timesteps_arr = np.append(timesteps_arr, monitoring_arr)
            timesteps_arr = np.unique(timesteps_arr)
        timesteps_gen = (time for time in timesteps_arr)

        # Creates options for propagation routine of given stepsize.
        def propagation_routine(timestep: float):
            return {
                "type": "propagation",
                "routine_name": "PROPAGATE",
                "step": timestep,
            }

        new_routines_dict = {task.ID: () for task in self._stage.children}
        time = next(timesteps_gen)
        prior_time = time
        _first_loop_token = True
        _monitoring_token = True
        for task in self._stage.children:
            for routine in task.children:
                if routine.options["time"] > prior_time and (
                        not _first_loop_token):
                    time = next(timesteps_gen)
                while time < routine.options["time"]:
                    if not _first_loop_token and prior_time != time:
                        new_routines_dict[task.ID] += (propagation_routine(
                            time - prior_time),)
                        _monitoring_token = True
                    if time in monitoring_arr and _monitoring_token:
                        new_routines_dict[task.ID] += monitoring_routines
                    _monitoring_token = False
                    _first_loop_token = False
                    prior_time = time
                    time = next(timesteps_gen)

                if prior_time != time:
                    new_routines_dict[task.ID] += (propagation_routine(
                        time - prior_time),)
                    _monitoring_token = True
                if time in monitoring_arr and _monitoring_token:
                    new_routines_dict[task.ID] += monitoring_routines
                    _monitoring_token = False
                new_routines_dict[task.ID] += (routine._options,)
                prior_time = time
                _first_loop_token = False

        # if stage configuration contained no tasks, add empty task to create
        # routines
        if self._stage.num_children == 0:
            self._stage.add_children_from_options()
            last_task_id = self._stage.children[-1].ID
            new_routines_dict = {last_task_id: ()}
            for time in timesteps_arr:
                if prior_time != time:
                    new_routines_dict[last_task_id] += (
                        propagation_routine(time - prior_time),)
                new_routines_dict[last_task_id] += monitoring_routines
                prior_time = time
        # if stage configuration contained tasks, create remaining routines
        # in last task
        else:
            last_task_id = self._stage.children[-1].ID
            for time in timesteps_gen:
                new_routines_dict[last_task_id] += (
                    propagation_routine(time - prior_time),)
                new_routines_dict[last_task_id] += monitoring_routines
                prior_time = time

        for task in self._stage.children:
            task.add_children_from_options(new_routines_dict[task.ID])

        # at end of time evolution, always return state
        self._stage.children[-1].add_children_from_options(
            {"routine_name": "_return_state",
             "store_token": "LAST_STATE",
             "TYPE": "AUTOMATIC",
             "type": "regular"})
        return stage_stop_time

    # TODO
    def _process_sweep(self):
        raise NotImplementedError

    def set_start_time(self, time: float):
        self._start_time = time

    def run(self) -> float:
        """
        Configures stage options for time evolution, if necessary.
        Returns the time of the last timestep of the stage, returns the
        start time if the stage is not an evolution stage.
        """
        if self._start_time is None:
            raise ValueError("Stage start time must be set, first.")

        for routine in self._stage.leafs:
            routine._options["TYPE"] = "USER"

        try:
            stage_type = self._stage.options["type"]
        except KeyError:
            stage_type = "default"

        if stage_type == "evolution":
            return self._process_evolution()

        elif stage_type == "sweep":
            return self._process_sweep()

        return self._start_time
