"""This module contains the class definitions of the Schedule and System class.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import Protocol
    from .graph import GraphNodeBase
    from .routines import RoutineABC

from typing import Any, Mapping

from .graph import GraphNodeID, GraphNodeNONE, GraphNodeMeta
from .interface import Propagator
from .routines import PropagationRoutine, RegularRoutine
from .utils import FrozenDict


class System:
    """Class representing the time-dependent quantum system.

    Each schedule is associated with exactly one time-dependent system. The
    `System` object encapsulates all the information about the time evolution
    of the system, i.e. at any system time, the quantum state and the
    hamiltonian are known. It also provides the methods necessary to propagate
    the system in time.
    """

    def __init__(self, start_time: float, initial_state, sys_params: dict,
                 propagator: Propagator = None):
        """Construct new physical system.

        The system is constructed from initial time, initial state and system
        parameters.
        Optionally, an instance of the `Propagator` interface can be passed.

        Args:
            start_time (float): The start time of the system.
            initial_state (Any): The initial state.
            sys_params (dict): General system parameters.
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
        self._sys_params = sys_params

    @property
    def parameters(self):
        """General parameters of the system."""
        return FrozenDict(self._sys_params)

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

    def set_system_parameters(self, parameters: Mapping):
        self._sys_params = parameters


class Schedule:
    """Class representing a schedule of the protocol."""
    def __init__(self, protocol: Protocol, root_options: dict):
        self._protocol = protocol
        root_class = GraphNodeMeta.fromRank(0, self._protocol._RANK_NAMES)
        self._root_node: GraphNodeBase = root_class(
            GraphNodeNONE(), root_options)
        self._external_options = {}
        try:
            self.start_time = self.root._options["start_time"]
        except KeyError:
            self.start_time = 0.0
        try:
            self.label = self.root._options["label"]
        except KeyError:
            self.label = None
        self.routines: tuple[RoutineABC] = ()
        self.results: dict[str, dict[float, Any]] = {}
        self.graph_initialized = False
        self.system_initialized = False

    def __repr__(self) -> str:
        return self.map.values().__str__()

    def __len__(self) -> int:
        return len(self.map.values())

    @property
    def depth(self):
        """Number of ranks in the graph."""
        return len(max(self.map.keys(), key=lambda ID: len(ID.tuple)).tuple)

    @property
    def leafs(self) -> tuple[GraphNodeBase]:
        return self.get_rank(-1)

    @property
    def map(self):
        return self.root.map

    @property
    def num_nodes(self):
        """Amount of nodes in the graph."""
        return len(self.map)

    @property
    def options(self) -> dict:
        return self.root._options

    @property
    def root(self) -> GraphNodeBase:
        return self._root_node

    def _reinitialize_system(self):
        init_state = self._system.psi
        if hasattr(self._system, "_propagator"):
            prop = self._system._propagator
        else:
            prop = None
        sys_params = self._system._sys_params
        self.initialize_system(init_state, sys_params, prop)

    def get_node(self, ID: GraphNodeID) -> GraphNodeBase:
        """Returns node with given tuple as ID.tuple, if it exists"""
        try:
            return self.map[ID]
        except KeyError:
            print(f"Node with ID {ID} not in graph.")
            return GraphNodeNONE()

    def get_node_from_tuple(self, ID_tuple: tuple) -> GraphNodeBase:
        """Returns node with given tuple as ID.tuple, if it exists"""
        ID = GraphNodeID(ID_tuple)
        return self.get_node(ID)

    def get_rank(self, rank: int) -> tuple[GraphNodeBase]:
        """Return all nodes with given rank. 'rank' -1 returns the leafs"""
        if rank == -1:
            rank = self.depth - 1

        def filter_func(node: GraphNodeBase) -> bool:
            return node.ID.rank == rank

        return tuple(filter(filter_func, self.map.values()))

    def initialize_system(self, initial_state, system_parameters: dict,
                          propagator: Propagator = None):
        """Initialize the physical system of the schedule.

        Optionally, also sets a propagator for the system. Without propagator,
        only non-propagating stages can be performed.

        Args:
            initial_state (Any): The initial state.
            system_parameters (dict, optional): General parameters of the
                system.
            hamiltonian (Any): The hamiltonian, can be callable for
                time-dependent hamiltonians.
            propagator (Propagator): An instance of the Propagator interface.
        """

        self._system = System(self.start_time, initial_state,
                              system_parameters, propagator)
        self.system_initialized = True

    def make_routines(self):
        if not self.system_initialized:
            raise ValueError("System must be initialized, first."
                             " Call .initialize_system().")

        for node in self.get_rank(-1):
            if node.options["name"] == "PROPAGATE":
                self.routines += (PropagationRoutine(node, self),)
            else:
                self.routines += (RegularRoutine(node, self),)

    def replace_node(self, ID: GraphNodeID, options: dict) -> None:
        """Replaces node in the graph, updating the parents' children."""
        parent = self.map[ID].parent
        n_children = parent.num_children
        # temporarily truncate children attribute of parent
        # for creation of node with correct ID
        parent_children = list(parent.children)
        parent.children = list(parent.children)[:ID.local]
        new_node = GraphNodeMeta.fromRank(
            ID.rank, self.root._RANK_NAMES)(parent, options)
        self.map[ID] = new_node
        # replace node in original children attribute of parent
        parent_children[ID.local] = new_node
        assert len(parent_children) == n_children
        # put new children back into parent node
        parent.children = tuple(parent_children)

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

    def set_start_time(self, start_time: float):
        """Manually set start time.

        Args:
            start_time (float): The start time of the schedule.
        """
        self.start_time = start_time
        if self.system_initialized:
            self._reinitialize_system()

    def set_system_parameters(self, system_parameters: dict):
        """Set general parameters about the system.

        Provide general parameters of the physical system, e.g. the length of
        a spin chain. During execution of the schedule, the system parameters
        are available for all routines of the schedule.

        Args:
            system_parameters (dict): The system parameters.
        """
        self._system.set_system_parameters(system_parameters)
