"""Module defining the API."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .graph.core import GraphRoot

import sys
import textwrap
import yaml
from abc import ABC, abstractmethod
from typing import Any, Sequence

from .graph import GraphNode, GraphNodeNONE
from . import preprocessor
from .routines import (
    Routine,
    EvolutionRegularRoutine,
    MonitoringRoutine,
    PropagationRoutine,
    RegularRoutine
    )


class _Performable(ABC):
    """Interface representing an object that can be performed."""

    @abstractmethod
    def __init__(self):
        self._output_str_prefix = None

    @abstractmethod
    def perform(self):
        pass

    @abstractmethod
    def setup(self):
        pass

    def _print_with_prefix(self, out_str):
        if self._output_str_prefix is not None:
            out = " | ".join([self._output_str_prefix, out_str])
        else:
            out = out_str

        print(out)
        sys.stdout.flush()


class _Propagator(ABC):
    """Interface representing a propagator.

    A callable that takes 3 arguments:
    state, time (float), timestep (float).
    It returns the state after time evolution of one timestep.
    """

    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return hasattr(__subclass, "__call__")

    @abstractmethod
    def __call__(self, state: Any, time: float, timestep: float) -> Any:
        """Propagate state from (time) to (time + timestep) and return state.
        """
        raise NotImplementedError


class _System:
    """Class representing the time-dependent quantum system.

    Each schedule is associated with exactly one time-dependent system. The
    `System` object encapsulates all the information about the time evolution
    of the system, i.e. at any system time, the quantum state and the
    hamiltonian are known. It also provides the methods necessary to propagate
    the system in time.
    """

    def __init__(self, start_time: float,
                 initial_state,
                 sys_vars: dict = {},
                 propagator: _Propagator = None):
        """Construct new physical system.

        The system is constructed from initial time, initial state and system
        parameters.
        Optionally, an instance of the `Propagator` interface can be passed.

        Args:
            start_time (float): The start time of the system.
            initial_state (Any): The initial state.
            sys_vars (dict): Dictionary containing system variables entering as
                positional arguments for routines.
            propagator (Propagator, optional): An instance of the Propagator
                interface. Defaults to None.

        Raises:
            TypeError: Raised, when the propagator does not implement the
                interface.
        """
        if propagator is not None:
            if not isinstance(propagator, _Propagator):
                raise TypeError("Propagator does not implement interface.")
            self._propagator = propagator

        self._time = start_time
        self.psi = initial_state
        self.sys_vars = sys_vars

    @property
    def time(self):
        return self._time

    def propagate(self, timestep):
        """Propagate the system by timestep."""
        if not hasattr(self, "_propagator"):
            raise RuntimeError("No propagator was set.")
        self.psi = self._propagator(self.psi, self._time, timestep)
        self._time += timestep
        return


class Protocol(_Performable):
    """A collection of schedules.
    """
    def __init__(self, schedules: Sequence[Schedule], label: str = None):
        """Construct protocol from the given schedules.

        Args:
            schedules (Sequence[Schedule]): The schedules to be contained in
                the protocol.
            label (str, optional): A label for the protocol. Defaults to
                'no label'.

        Raises:
            ValueError: Raised, when two or more schedules have the same label.
        """
        super().__init__()
        if label is None:
            self.label = "no label"
        else:
            self.label = label

        self._schedules = tuple(schedules)
        schedule_labels = set()
        for sch in self._schedules:
            if sch.label in schedule_labels:
                raise ValueError(f"Duplicate schedule label {sch.label}")
            schedule_labels |= set(sch.label)

        self.results = {}

    @property
    def _map(self):
        labels = (sch.label for sch in self._schedules)
        return dict(zip(labels, self._schedules))

    def _select_schedules(self, schedule_labels: Sequence[str] = None):
        if schedule_labels is None:
            return self._schedules
        else:
            return tuple([self._map[label] for label in schedule_labels])

    def add_schedule(self, schedule: Schedule):
        """Add a schedule.

        Args:
            schedule (Schedule): The schedule to add.

        Raises:
            ValueError: Raised, if the label of the schedule already exists.
        """
        if schedule.label in self._map:
            raise ValueError(f"Schedule label {schedule.label} already"
                             " exists.")
        self._schedules += (schedule,)

    def duplicate_schedule(self, source_label: str, target_label: str):
        """Add copy of an already schedule.

        Args:
            source_label (str): Label of the schedule to copy.
            target_label (str): Label of the newly created schedule.
        """
        source_sched = self._map[source_label]
        new_sched = Schedule(source_sched._configuration, target_label)
        new_sched.initialize_system(source_sched._system.psi,
                                    source_sched._system.sys_vars,
                                    source_sched._system._propagator)
        self.add_schedule(new_sched)

    def perform(self, schedule_labels: Sequence[str] = None):
        """Perform the specified schedules. By default performs all schedules.

        Args:
            schedule_labels (Sequence[str], optional): Sequence of labels
                of schedules to be performed. Defaults to None and performs all
                schedules in that case.
        """
        for sch in self._select_schedules(schedule_labels):
            self_label = f"'{self.label}'"
            sch._output_str_prefix = f"PROTOCOL {self_label:>6}"
            sch.perform()
            self.results[sch.label] = sch.results

    def setup(self, schedule_labels: Sequence[str] = None,
              start_time=None):
        """Set up schedules for execution.

        If label is given, sets up the specified schedule. Otherwise, sets up
        all schedules.
        Args:
            schedule_label (Sequence[str], optional): Label of a schedule.
                Defaults to None.
            start_time (float, optional): A start time overriding the schedule
                configuration. Defaults to None.
        """
        for sch in self._select_schedules(schedule_labels):
            sch.setup(start_time)


class Schedule(_Performable):
    """Class representing a schedule."""

    @classmethod
    def from_yaml(cls, yaml_path: str, label: str = None):
        """Construct schedule from path to yaml configuration file.

        If the file contains multiple schedule configurations, returns a list
        of all schedules.

        Args:
            yaml_path (str): Path to configuration file.
            label (str, optional): Label for the schedule. Defaults to None.

        Returns:
            Schedule | tuple[Schedule]: Schedule or tuple of schedule objects.
        """
        with open(yaml_path, "r") as stream:
            config = yaml.safe_load(stream)

        try:
            sched_cfg = config["schedules"]
        except KeyError:
            sched_cfg = config

        if len(sched_cfg) > 1:
            if label is not None:
                raise ValueError("When mutiple schedules are defined, label"
                                 " must be None")
            return (cls(cfg, label) for cfg in sched_cfg)

        return cls(sched_cfg[0], label)

    def __init__(self, configuration: dict, label: str = None):
        """Construct schedule from configuration dictionary."""
        super().__init__()
        self._configuration = configuration
        self._root_node: GraphRoot = GraphNode(GraphNodeNONE(), configuration)
        if label is not None:
            self.label = label
        else:
            try:
                self.label = self.root._options["label"]
            except KeyError:
                self.label = "no_label"

        self._live_tracking: dict[str, Routine] = {}
        self._ready_for_execution = False
        self.results: dict[str, dict[float, Any]] = {}
        self._routines: tuple[Routine] = ()
        self._system_initialized = False
        if "start_time" not in self.root._options:
            self.start_time = 0.0

    def __repr__(self) -> str:
        return self._map.values().__str__()

    @property
    def _map(self):
        return self.root.map

    @property
    def _num_stages(self):
        return len(list(self.root.get_generation(1)))

    @property
    def root(self) -> GraphRoot:
        return self._root_node

    @property
    def start_time(self) -> float:
        """The initial time of the system."""
        return self.root._options["start_time"]

    @start_time.setter
    def start_time(self, new):
        self.root._options["start_time"] = new
        if self._system_initialized:
            self._reinitialize_system()

    def _make_routines(self):
        if not self._system_initialized:
            raise ValueError("System must be initialized, first."
                             " Call .initialize_system().")
        system = self._system
        routines = [None]*len(self.root.leafs)
        for i, node in enumerate(self.root.leafs):
            stage_idx = node.parent_of_rank(1).ID.local + 1
            if node.type == "propagation":
                routine = PropagationRoutine(node._options)
                routine.stage_idx = stage_idx
                routines[i] = routine
            elif node.type == "evolution":
                routine = EvolutionRegularRoutine(node._options, system)
                routine.stage_idx = stage_idx
                routines[i] = routine
            elif node.type == "monitoring":
                routine = MonitoringRoutine(node._options, system)
                routine.stage_idx = stage_idx
                routines[i] = routine
            elif node.type == "regular":
                routine = RegularRoutine(node._options, system)
                routine.stage_idx = stage_idx
                routines[i] = routine

        self._routines = tuple(routines)

    def _reinitialize_system(self):
        init_state = self._system.psi
        if hasattr(self._system, "_propagator"):
            prop = self._system._propagator
        else:
            prop = None
        sys_vars = self._system.sys_vars
        self.initialize_system(init_state, sys_vars, prop)

    def _set_live_tracking(self, routine_names: Sequence[str],
                           true_false: bool):
        if self._ready_for_execution:
            raise ValueError("Cannot set live tracking after"
                             " calling .setup().")

        for name in routine_names:
            self._live_tracking[name] = true_false

    def disable_live_tracking(self, routines: Sequence[str] | str):
        """Disable live tracking for the specified routines.

        Routines are referred to by their store token. If no store token is
        set, use the routine name.
        """
        if isinstance(routines, str):
            routines = (routines,)

        self._set_live_tracking(routines, False)

    def enable_live_tracking(self, routines: Sequence[str] | str):
        """Enable live tracking for the specified routines.

        Routines are referred to by their store token. If no store token is
        set, use the routine name.
        """
        if isinstance(routines, str):
            routines = (routines,)

        self._set_live_tracking(routines, True)

    def initialize_system(self, initial_state, sys_vars: dict = {},
                          propagator: _Propagator = None):
        """Initialize the physical system of the schedule.

        Optionally, also sets a propagator for the system. Without propagator,
        only non-propagating stages can be performed.

        Args:
            initial_state (Any): The initial state.
            sys_vars (dict): Dictionary containing additional positional
                arguments for routines.
            propagator (Propagator): An instance of the Propagator interface.
        """

        self._system = _System(self.start_time, initial_state,
                               sys_vars, propagator)
        self._system_initialized = True

    def perform(self):
        """Execute all routines and collect results."""
        if not self._ready_for_execution:
            raise ValueError("Schedule is not set up for execution. "
                             "Call .setup().")

        for i, routine in enumerate(self._routines):
            stage_idx = routine.stage_idx

            if isinstance(routine, PropagationRoutine):
                prop_string = f"PROPAGATE BY {routine.timestep:3.4f}"
                name_string = (f">>>>>>>>>> {prop_string:^29} >>>>>>>>>>")
            else:
                name_string = (f"{routine.tag:>10}"
                               f" {routine.store_token:<20}")
            schedule_name = f"'{self.label}'"
            text_prefix = " | ".join([
                f"SCHEDULE {schedule_name:>6}:",
                f"STAGE {stage_idx:>3}/{self._num_stages:<3}",
                f"ROUTINE {i + 1:>{len(str(len(self._routines)))}}"
                f"/{len(self._routines)}",
                f"TIME {f'{self._system.time:.4f}':>10}",
                f"{name_string}"])
            textwrapper = textwrap.TextWrapper(width=250,
                                               initial_indent=text_prefix)
            output = routine(self._system)
            if routine.live_tracking:
                output_text = textwrapper.fill(f": {output[1]}")
            else:
                output_text = text_prefix
            self._print_with_prefix(output_text)

            if not routine.store:
                continue

            if output[0] not in self.results:
                self.results[output[0]] = {
                    self._system.time: output[1]}
            else:
                self.results[output[0]].update(
                    {self._system.time: output[1]})

    def setup(self, start_time=None):
        """Set up the schedule for execution.

        Args:
            start_time (float, optional): A start time to override the file
                configuration. Defaults to None.

        Raises:
            ValueError: Raised, if no system is initialized.
        """
        if not self._system_initialized:
            raise ValueError("No system is set for the schedule.")

        if start_time is not None:
            self.start_time = start_time

        preprocessor.process_graph(self.root)
        self._make_routines()
        for rout in self._routines:
            if rout.store_token in self._live_tracking:
                rout.set_live_tracking(self._live_tracking[rout.store_token])

        self._ready_for_execution = True

    def set_system_variables(self, sys_vars: dict):
        """Set global variables of the system.

        Here, general external information like system parameters can be made
        available to the routines. The user-defined functions need to take
        these additional arguments at second position after the quantum state.

        Args:
            positional_args (dict): Dictionary containing arbitrary variables
                for function calls.
        """
        self._system.sys_vars = sys_vars
