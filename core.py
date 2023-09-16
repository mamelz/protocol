"""Module for the main class 'Protocol'."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from numpy import ndarray

import sys
import textwrap
from typing import Any, Union

from .parser_ import ProtocolConfiguration
from .preprocessor import ProtocolPreprocessor
from .schedule import Schedule
from .routines import RoutineABC, PropagationRoutine
from .settings import SETTINGS
from .utils import FrozenDict


class Protocol:
    """The main object of the package, representing a collection of schedules.

    The protocol contains all schedules to be executed. Schedules can be
    initialized by constructing the protocol from a yaml configuration file or
    they can be added to an already existing protocol.
    Upon execution of the protocol, the outputs of all routines, depending on
    configuration, are stored and can be retrieved with the `get_results()`
    method.
    """

    _RANK_NAMES = ("Schedule", "Stage", "Task", "Routine")

    def __init__(self, config_yaml_path: str = None):
        """Construct new protocol from configuration file.

        If no configuration file is given, construct empty protocol.

        Args:
            config_yaml_path (str, optional): Path to configuration file.
                                              Defaults to None.
        """

        if config_yaml_path is not None:
            self._config = ProtocolConfiguration(config_yaml_path)
        else:
            self._config = None

        self._schedules: tuple[Schedule] = ()
        self._label_map: dict[str, int] = {}
        if self._config is not None:
            for options in self._config.schedules:
                self._schedules += (Schedule(self, options),)
        self._live_tracking = ()
        self._results = {}
        self._initialized = False
        self._finalized = False
        self._schedules_performed: tuple[float] = ()

    @property
    def global_options(self) -> dict:
        """Return the global options of the protocol.

        Returns:
            dict: Dictionary containing all keys found, except for 'schedules'.
        """
        res = {}
        for key in self._config:
            if key != "schedules":
                res[key] = self._config[key]

        return res

    @property
    def num_schedules(self):
        """Return the number of schedules registered in the protocol."""
        return len(self._schedules)

    @property
    def schedule_options(self) -> list[dict]:
        """Return a list containing the options of all schedules."""
        return self._config["schedules"]

    def _get_schedule(self, identifier: Union[int, str]) -> Schedule:
        """Return schedule, either with specified number or specified label.

        Args:
            identifier (Union[int, str]): Schedule identifier.

        Raises:
            TypeError: Raised, if identifier is of wrong type.

        Returns:
            Schedule: A schedule of the protocol.
        """
        if isinstance(identifier, int):
            return self._schedules[identifier]
        if isinstance(identifier, str):
            return self._schedules[self._label_map[identifier]]
        raise TypeError("Invalid identifier type.")

    def _preprocessor(self, _start_time=None):
        return ProtocolPreprocessor(self, _start_time)

    def _perform_n(self, id):
        if isinstance(self._results, FrozenDict):
            self._results = dict(self._results)

        graph: Schedule = self._get_schedule(id)
        if isinstance(id, str):
            schedule_idx = self._label_map[id]
        else:
            schedule_idx = id

        num_stages = len(graph.get_rank(1))
        assert isinstance(graph, Schedule)
        for i, routine in enumerate(graph.ROUTINES):
            assert isinstance(routine, RoutineABC)
            stage_idx = routine._node.parent_of_rank(1).ID.local + 1

            if isinstance(routine, PropagationRoutine):
                prop_string = f"PROPAGATE BY {routine.timestep:3.4f}"
                name_string = (f">>>>>>>>>> {prop_string:^29} >>>>>>>>>>")
            else:
                name_string = (f"{routine._TYPE:>10}"
                               f" {routine.store_token:<20}")
            schedule_name = schedule_idx + 1 if graph.label is None else (
                f"'{graph.label}'")
            text_prefix = " | ".join([
                f"SCHEDULE {schedule_name:>6}:",
                f"STAGE {stage_idx:>3}/{num_stages:<3}",
                f"ROUTINE {i + 1:>{len(str(len(graph.ROUTINES)))}}"  # no comma
                f"/{len(graph.ROUTINES)}",
                f"TIME {f'{graph._system.time:.4f}':>10}",
                f"{name_string}"])
            textwrapper = textwrap.TextWrapper(width=250,
                                               initial_indent=text_prefix)
            output = routine(graph._system)
            if routine.live_tracking:
                output_text = textwrapper.fill(f": {output[1]}")
            else:
                output_text = text_prefix
            print(output_text)
            sys.stdout.flush()

            if output is None:
                continue

            if output[0] not in graph.RESULTS:
                graph.RESULTS[output[0]] = {graph._system.time: output[1]}
            else:
                graph.RESULTS[output[0]].update(
                    {graph._system.time: output[1]})

        if graph.label is not None:
            self._results[graph.label] = graph.RESULTS
        self._results[schedule_idx] = graph.RESULTS
        self._results = FrozenDict(self._results)
        self._schedules_performed += (schedule_idx,)
        return

    def add_schedule(self, schedule_options: dict, **tstate_args):
        """Add a schedule to the protocol, configured by `schedule_options`.

        Optionally, initialize the timed state of the schedule.

        Args:
            schedule_options (dict): The options of the schedule.

        Raises:
            ValueError: Raised when `schedule_options` specify label which is
                        already used by another schedule.

        Returns:
            Schedule: The newly added Schedule.
        """
        graph = Schedule(self, schedule_options)
        if tstate_args is not None:
            graph.init_tstate(**tstate_args)
        self._schedules += (graph,)
        if graph.label is not None:
            if graph.label in self._label_map:
                raise ValueError(f"Graph label {graph.label} already exists.")
            self._label_map[graph.label] = len(self._schedules) - 1

        return graph

    def duplicate_schedule(self, schedule_id: Union[str, int], **tstate_args):
        """Duplicate a schedule identified by `schedule_id`.

        Args:
            schedule_id (Union[str, int]): The label or index of an already
                                           registered schedule.

        Returns:
            Schedule: The duplicated Schedule.
        """
        return self.add_schedule(
            self._get_schedule(schedule_id).root._options, **tstate_args)

    def finalize(self):
        """Construct the routines of the protocol, preparing it for execution.

        Raises:
            ValueError: Raised, if protocol is not initialized.
        """
        if not self._initialized:
            raise ValueError("Protocol must be initialized, first.")

        for graph in self._schedules:
            graph.make_routines()
            for routine in graph.ROUTINES:
                if routine.store_token in self._live_tracking:
                    routine.enable_live_tracking()
        self._finalized = True

    def get_options(self, key: str):
        """Return value of global option `key`.

        Args:
            key (str): The name of the global option to return.

        Returns:
            Any: The value of the option.
        """
        return self.global_options[key]

    def get_results(self, quantities: tuple = (), schedule_id=None)\
            -> FrozenDict[str, dict[str, dict[float, Any]]]:
        """Return results after execution of the protocol.

        Return the time-resolved outputs of routines of a schedule that
        were performed during execution.
        If no schedule is specified, return a dictionary containing all
        schedules by index or label, if available.
        Quantities can be addressed by their store token, if set up
        in the protocol configuration.
        If no quantity is specified, the dictionary contains all
        calculated quantities for each schedule.

        Args:
            quantities (Sequence[str]): Sequence of names of routine outputs.
            schedule_id (tuple): Tuple of labels and/or indices of schedules.

        Returns:
            FrozenDict[str, dict[str, dict[float, Any]]]:
                Immutable dictionary-like object, containing the desired
                outputs. The first key specifies the schedule, the second key
                specifies the time corresponding to the outputs.
        """
        output_dict = {}
        if schedule_id is None:
            graphs = self._schedules_performed
        else:
            graphs = tuple(schedule_id)

        for identifier in graphs:
            key = self._get_schedule(identifier).label
            if key is None:
                key = identifier
            output_dict[key] = {}

        if schedule_id is not None and (
                schedule_id not in output_dict):
            assert len(output_dict.values()) == 0
            output_dict[schedule_id] = output_dict.values()[0]

        if quantities == ():
            for graph_idt in output_dict.keys():
                output_dict[graph_idt] = self._get_schedule(graph_idt).RESULTS
        else:
            for graph_idt in output_dict.keys():
                for qname in quantities:
                    output_dict[graph_idt][qname] = self._get_schedule(
                        graph_idt).RESULTS[qname]
        return FrozenDict(output_dict)

    def initialize(self, force_start_time: float = None):
        """Initialize protocol after at least one schedule was added.

        Optionally, force a start time for all schedules.
        Also checks if all library settings have been set.

        Args:
            force_start_time (float, optional): The start time to force for all
                schedules. Defaults to None.

        Raises:
            ValueError: Raised, if a library setting is missing.
            ValueError: Raised, if no schedules are set.
            ValueError: Raised, if a schedule is not initialized with a
                system.
        """
        if not SETTINGS.check():
            raise ValueError("Library settings not complete.")
        if len(self._schedules) == 0:
            raise ValueError("Protocol does not contain any schedules.")
        for i, graph in enumerate(self._schedules):
            graph = self._schedules[i]
            id = f"'{graph.label}'" if graph.label is not None else i
            if graph._system is None:
                raise ValueError(f"System of schedule {id} not set.")

        self._preprocessor(_start_time=force_start_time).run()
        self._initialized = True
        return

    def perform(self, schedule_id=None):
        """Perform all schedules. Optionally, perform a specified schedule.

        Args:
            schedule_id (str | int, optional): Identifier for schedule.
                                               Defaults to None.

        Raises:
            ValueError: Raised, if the protocol was not ready for execution.
        """
        if not self._finalized:
            raise ValueError("Protocol must be finalized, first.")

        if schedule_id is None:
            for i in range(self.num_schedules):
                self._perform_n(i)
        else:
            self._perform_n(schedule_id)
        return

    def schedule(self, identifier: Union[int, str]) -> Schedule:
        """Return schedule, either with specified number or specified label.

        Args:
            identifier (Union[int, str]): Schedule identifier.

        Raises:
            TypeError: Raised, if identifier is of wrong type.

        Returns:
            Schedule: A schedule of the protocol.
        """
        return self._get_schedule(identifier)

    def set_global_options(self, config: dict):
        """Set global options of the protocol.

        Args:
            config (dict): Dictionary containing options to set.

        Raises:
            ValueError: Raised, if options contain the keyword 'schedules'.
        """
        if "schedules" in config:
            raise ValueError("Global options cannot contain key 'schedules'.")
        self._config.update(config)
        return

    def set_live_tracking(self, names: Union[str, tuple[str]]):
        """Enable live tracking for the routines specified by `names`.

        All routines with the specified names will print their result in the
        output stream during execution of the protocol. Routines can be
        specified by their name or store token.

        Args:
            names (Union[str, tuple[str]]): The names of the routines to be
                                            live-tracked.
        """
        if isinstance(names, str):
            names = (names,)
        self._live_tracking = names
        return

    def set_tstate(self, schedule_id: Union[int, str], state: ndarray,
                   propagator_factory, label=None):
        """Set up the time-dependent state of a schedule.

        This method sets the initial state of the schedule. Furthermore,
        a factory method is passed that generates the propagator for the state.

        Args:
            schedule_id (Union[int, str]): Schedule identifier.
            state (ndarray): The initial state for this schedule.
            propagator_factory (_type_): Factory method that generates an
                implementation of the `Propagator` interface.
            label (_type_, optional): Label of the state. Defaults to None.
        """
        schedule = self._get_schedule(schedule_id)
        schedule.init_tstate(state, propagator_factory, label)
        if schedule.label is not None:
            self._label_map[schedule.label] = self._schedules.index(schedule)
        return
