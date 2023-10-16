"""This module contains the class definitions of the Schedule and System class.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # from .core import Protocol
    from .graph.core import GraphRoot

import sys
import textwrap
import yaml
from typing import Any, Sequence

from .graph import GraphNode, GraphNodeID, GraphNodeNONE
from .interface import Propagator
from . import preprocessor
from .routines import (
    Routine,
    EvolutionRegularRoutine,
    MonitoringRoutine,
    PropagationRoutine,
    RegularRoutine
    )


class System:
    """Class representing the time-dependent quantum system.

    Each schedule is associated with exactly one time-dependent system. The
    `System` object encapsulates all the information about the time evolution
    of the system, i.e. at any system time, the quantum state and the
    hamiltonian are known. It also provides the methods necessary to propagate
    the system in time.
    """

    def __init__(self, start_time: float,
                 initial_state,
                 positional_args: dict = {},
                 propagator: Propagator = None):
        """Construct new physical system.

        The system is constructed from initial time, initial state and system
        parameters.
        Optionally, an instance of the `Propagator` interface can be passed.

        Args:
            start_time (float): The start time of the system.
            initial_state (Any): The initial state.
            positional_args (dict): Dictionary containing additional positional
                arguments for routines.
            propagator (Propagator, optional): An instance of the Propagator
                interface. Defaults to None.

        Raises:
            TypeError: Raised, when the propagator does not implement the
                interface.
        """
        if propagator is not None:
            if not isinstance(propagator, Propagator):
                raise TypeError("Propagator does not implement interface.")
            self._propagator = propagator

        self._time = start_time
        self.psi = initial_state
        self.positional_args = positional_args

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


class Schedule:
    """Class representing a schedule."""

    @classmethod
    def from_file(cls, yaml_path: str, label: str = None):
        """Construct schedule from path to yaml configuration file.

        If the file contains multiple schedule configurations, returns a list
        of all schedules.

        Args:
            yaml_path (str): Path to configuration file.
            label (str, optional): Label for the schedule. Defaults to None.

        Returns:
            Schedule | list[Schedule]: The schedule(s).
        """
        with open(yaml_path, "r") as stream:
            config = yaml.safe_load(stream)

        try:
            sched_cfg = config["schedules"]
        except KeyError:
            sched_cfg = config

        if len(sched_cfg) > 1:
            return [cls(cfg, label) for cfg in sched_cfg]

        return cls(sched_cfg[0], label)

    def __init__(self, configuration: dict, label: str = None):
        """Construct schedule from configuration dictionary."""
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
    def depth(self):
        """Return the number of ranks in the graph."""
        node = self._root_node
        while node.num_children > 0:
            node = node.children[0]

        return node.rank + 1

    @property
    def leafs(self) -> tuple[GraphNode]:
        return self.root.leafs

    @property
    def _map(self):
        return self.root.map

    @property
    def _num_stages(self):
        return len(list(self.root.get_generation(1)))

    @property
    def num_nodes(self):
        """Amount of nodes in the graph."""
        return len(self._map)

    @property
    def options(self) -> dict:
        return self.root._options

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
        routines = [None]*len(self.leafs)
        for i, node in enumerate(self.leafs):
            stage_idx = node.parent_of_rank(1).ID.local + 1
            match node.type:
                case "propagation":
                    routine = PropagationRoutine(node._options)
                    routine.stage_idx = stage_idx
                    routines[i] = routine
                case "evolution":
                    routine = EvolutionRegularRoutine(node._options, system)
                    routine.stage_idx = stage_idx
                    routines[i] = routine
                case "monitoring":
                    routine = MonitoringRoutine(node._options, system)
                    routine.stage_idx = stage_idx
                    routines[i] = routine
                case "regular":
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
        pos_args = self._system.positional_args
        self.initialize_system(init_state, pos_args, prop)

    def disable_live_tracking(self, routine_names: Sequence[str] | str):
        """Disable live tracking for the specified routines."""
        for name in tuple(routine_names):
            self._live_tracking[name] = False

    def enable_live_tracking(self, routine_names: Sequence[str] | str):
        """Enable live tracking for the specified routines."""
        for name in tuple(routine_names):
            self._live_tracking[name] = True

    def get_node(self, node_id: GraphNodeID | tuple) -> GraphNode:
        """Returns node with given tuple as ID.tuple, if it exists"""
        if not isinstance(node_id, GraphNodeID):
            id_key = GraphNodeID(node_id)
        try:
            return self._map[id_key]
        except KeyError:
            print(f"Node with ID {id_key.tuple} not in graph.")
            return None

#    def get_system_parameters(self):
#        """Return system parameters."""
#        return self._system.parameters

    def initialize_system(self, initial_state, positional_args: dict = {},
                          propagator: Propagator = None):
        """Initialize the physical system of the schedule.

        Optionally, also sets a propagator for the system. Without propagator,
        only non-propagating stages can be performed.

        Args:
            initial_state (Any): The initial state.
            positional_args (tuple): Tuple containing additional positional
                arguments for routines. The first positional argument is always
                the quantum state itself if the routine needs system
                information at all.
            propagator (Propagator): An instance of the Propagator interface.
        """

        self._system = System(self.start_time, initial_state,
                              positional_args, propagator)
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
            print(output_text)
            sys.stdout.flush()

            if not routine.store:
                continue

            if output[0] not in self.results:
                self.results[output[0]] = {
                    self._system.time: output[1]}
            else:
                self.results[output[0]].update(
                    {self._system.time: output[1]})

    def set_external_kwargs(self, kwargs: dict):
        """
        Set external keyword arguments for routines of given name.

        Routines will infer the parameter, if the respective entry in their
        kwargs dictionary contains the 'EXTERNAL' keyword (case sensitive).

        Args:
            kwargs (dict): The dictionary specifying the name of the routine
                and the keyword argument to set. Format of input is:
                {<function_name>: {<kwarg_name>: <kwarg_value>}}
        """
        self._external_kwargs = kwargs
        self._root_node.options["external"] = self._external_kwargs

#    def set_label(self, label: str):
#        """Set a label for the schedule."""
#        self.label = label

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

        preprocessor.main(self.root)
        self._make_routines()
        for rout in self._routines:
            if rout.store_token in self._live_tracking:
                rout.set_live_tracking(self._live_tracking[rout.store_token])

        self._ready_for_execution = True

    def set_positional_args(self, positional_args: tuple):
        """Set the positional arguments for routines.

        Here, general external information like system parameters can be made
        available to the routines when calling the functions. The user-defined
        functions need to take these additional arguments at second position
        after the quantum state.

        Args:
            positional_args (tuple): Tuple containing arbitrary data for
            function calls.
        """
        self._system.positional_args = positional_args
