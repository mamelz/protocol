"""Module defining the API."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .builder.graph_classes.run import RunGraphRoot
    from .routine.classes import Routine
    from .inputparser.graph_classes.yaml import YAMLTaskNode

import copy
import textwrap
from typing import Any, Sequence

from .builder.graph_classes.user import UserGraphRoot
from .builder.main import GraphBuilder
from .inputparser.main import YAMLParser
from .essentials import Performable, Propagator, System
from .routine.classes import PropagationRoutine
from .routine.generator import RoutineGenerator


class Protocol(Performable):
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
    def _map(self) -> dict[str, Schedule]:
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
        new_sched: Schedule = source_sched.duplicate(target_label)
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

    def build(self, schedule_labels: Sequence[str] = None,
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
            sch.build(start_time)


class Schedule(Performable):
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
        sched_cfg, tasks = YAMLParser().parse_from_file(yaml_path)
        if len(sched_cfg) > 1:
            if label is not None:
                raise ValueError("When mutiple schedules are defined, label"
                                 " must be None")
            return (cls(cfg, label) for cfg in sched_cfg)

        return cls(sched_cfg[0], label, tasks)

    def __init__(self, sched_cfg: dict, label: str = None,
                 predef_tasks: dict = {}):
        """Construct schedule from configuration dictionary."""
        super().__init__()
        self._configuration = sched_cfg
        self._user_graph = UserGraphRoot(sched_cfg)
        self._predef_tasks: dict[str, YAMLTaskNode] = predef_tasks
        self._run_graph: RunGraphRoot = None
        if label is not None:
            self.label = label
        else:
            try:
                self.label = self._user_graph.options["label"]
            except KeyError:
                self.label = "no label"

        self._live_tracking: dict[str, Routine] = {}
        self._ready_for_execution = False
        self.results: dict[str, dict[float, Any]] = {}
        self._routines: tuple[Routine] = ()
        self._system_initialized = False
        if "start_time" not in self._user_graph.options.local:
            self.start_time = 0.0

    @property
    def num_routines(self):
        return self._run_graph.num_routines

    @property
    def num_stages(self):
        return self._run_graph.num_stages

    @property
    def start_time(self) -> float:
        """The initial time of the system."""
        return self._user_graph.start_time

    @start_time.setter
    def start_time(self, new: float):
        self._user_graph.start_time = new
        if self._system_initialized:
            self._reinitialize_system()

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

    def duplicate(self, label: str) -> Schedule:
        """Return a copy of self with different label."""
        copy_sched = copy.deepcopy(self)
        copy_sched.label = label

        return copy_sched

    def enable_live_tracking(self, routines: Sequence[str] | str):
        """Enable live tracking for the specified routines.

        Routines are referred to by their store token. If no store token is
        set, use the routine name.
        """
        if isinstance(routines, str):
            routines = (routines,)

        self._set_live_tracking(routines, True)

    def initialize_system(self, initial_state, sys_vars: dict = {},
                          propagator: Propagator = None):
        """Initialize the physical system of the schedule.

        Optionally, also sets a propagator for the system. Without propagator,
        only non-propagating stages can be performed.

        Args:
            initial_state (Any): The initial state.
            sys_vars (dict): Dictionary containing additional positional
                arguments for routines.
            propagator (Propagator): An instance of the Propagator interface.
        """

        self._system = System(self.start_time, initial_state,
                              sys_vars, propagator)
        self._system_initialized = True

    def perform(self):
        """Execute all routines and collect results."""
        if not self._ready_for_execution:
            raise ValueError("Schedule is not set up for execution. "
                             "Call .build().")

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
                f"STAGE {stage_idx:>3}/{self.num_stages:<3}",
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

    def build(self, start_time=None):
        """Build the run graph and generate all routines.

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

        builder = GraphBuilder(self._predef_tasks)
        self._run_graph = builder.build(self._user_graph)
        rout_gen = RoutineGenerator()
        self._routines = rout_gen.make(self._system, self._run_graph)
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
