"""This module contains the class definitions of the Schedule and System class.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import Protocol
    from .graph.core import GraphRoot

from typing import Any, Sequence

from .graph import GraphNode, GraphNodeID, GraphNodeNONE
from .interface import Propagator
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
    """Class representing a schedule of the protocol."""
    def __init__(self, protocol: Protocol, root_options: dict):
        self._protocol = protocol
        self._root_node: GraphRoot = GraphNode(GraphNodeNONE(), root_options)
        self._external_options = {}
        try:
            self.start_time = self.root._options["start_time"]
        except KeyError:
            self.start_time = 0.0
        try:
            self.label = self.root._options["label"]
        except KeyError:
            self.label = None
        self._routines: tuple[Routine] = ()
        self.results: dict[str, dict[float, Any]] = {}
        self._system_initialized = False

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
    def num_nodes(self):
        """Amount of nodes in the graph."""
        return len(self._map)

    @property
    def options(self) -> dict:
        return self.root._options

    @property
    def root(self) -> GraphRoot:
        return self._root_node

    def _reinitialize_system(self):
        init_state = self._system.psi
        if hasattr(self._system, "_propagator"):
            prop = self._system._propagator
        else:
            prop = None
        pos_args = self._system.positional_args
        self.initialize_system(init_state, pos_args, prop)

    def get_global_option(self, key):
        """Return global option of protocol."""
        return self._protocol.get_option(key)

    def get_node(self, node_id: GraphNodeID | tuple) -> GraphNode:
        """Returns node with given tuple as ID.tuple, if it exists"""
        if not isinstance(node_id, GraphNodeID):
            id_key = GraphNodeID(node_id)
        try:
            return self._map[id_key]
        except KeyError:
            print(f"Node with ID {id_key.tuple} not in graph.")
            return None

    def get_system_parameters(self):
        """Return system parameters."""
        return self._system.parameters

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
                    # self._routines += (routine,)
                case "evolution":
                    routine = EvolutionRegularRoutine(node._options, system)
                    routine.stage_idx = stage_idx
                    routines[i] = routine
                    # self._routines += (routine,)
                case "monitoring":
                    routine = MonitoringRoutine(node._options, system)
                    routine.stage_idx = stage_idx
                    routines[i] = routine
                    # self._routines += (routine,)
                case "regular":
                    routine = RegularRoutine(node._options, system)
                    routine.stage_idx = stage_idx
                    routines[i] = routine
                    # self._routines += (routine,)

        self._routines = tuple(routines)

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

    def set_label(self, label: str):
        """Set a label for the schedule."""
        self.label = label

    def enable_live_tracking(self, routine_names: Sequence[str] | str):
        """Enable live tracking for the specified routines."""

    def set_start_time(self, start_time: float):
        """Manually set start time.

        Args:
            start_time (float): The start time of the schedule.
        """
        self.start_time = start_time
        if self._system_initialized:
            self._reinitialize_system()

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
