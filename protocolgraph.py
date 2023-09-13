"""Wrapper class for implementing the graph as attribute
of 'Protocol' object.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from numpy import ndarray
    from .core import Protocol
    from .graph import GraphNodeBase
    from .interface import TimedState
    from .routines import RoutineABC

from typing import Any

from .graph import GraphNodeID, GraphNodeNONE, GraphNodeMeta
from .interface import UserTState
from .routines import PropagationRoutine, RegularRoutine


class ProtocolGraph:
    """Class representing a schedule of the protocol"""
    def __init__(self, protocol: Protocol, root_options: dict):
        self._protocol = protocol
        root_class = GraphNodeMeta.fromRank(0, self._protocol._RANK_NAMES)
        self._root_node = root_class(GraphNodeNONE(), root_options)
        self._external_options = {}
        self.tstate: TimedState = None
        self.ROUTINES: tuple[RoutineABC] = ()
        self.RESULTS: dict[str, dict[float, Any]] = {}
        self.graph_ready = False

    def __repr__(self) -> str:
        return self.map.values().__str__()

    def __len__(self) -> int:
        return len(self.map.values())

    @property
    def depth(self):
        """Number of ranks in the graph."""
        return len(max(self.map.keys(), key=lambda ID: len(ID.tuple)).tuple)

    @property
    def label(self):
        if self.tstate is not None:
            return self.tstate.label
        return

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

    def init_tstate(self, state: ndarray, propagator_factory, label):
        self.tstate = UserTState(self.options["start_time"], state,
                                 propagator_factory, label=label)

    def make_routines(self):
        if not self.graph_ready:
            raise ValueError("ProtocolGraph must be configured, first."
                             " Call .preprocessor().configure()")

        for node in self.get_rank(-1):
            if node.options["name"] == "PROPAGATE":
                self.ROUTINES += (PropagationRoutine(node, self._protocol),)
            else:
                self.ROUTINES += (RegularRoutine(node, self._protocol),)

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
        Sets keyword arguments for routines of given name. Routines will
        infer the parameter, if the respective entry in the config file
        contains the 'EXTERNAL' keyword (case sensitive).
        Format of input is:
        {<function_name>: {<kwarg_name>: <kwarg_value>}}
        """
        self._external_kwargs = kwargs
        self._root_node.options["external"] = self._external_kwargs
