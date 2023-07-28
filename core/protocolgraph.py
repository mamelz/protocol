"""Wrapper class for implementing the graph as attribute
of 'Protocol' object.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from numpy import ndarray
    from ..core import Protocol
    from ..graph import GraphNodeBase
    from ..interface import PropagatorFactory
    from ..routines import RoutineABC

from ..interface import UserTState
from ..graph import GraphNodeID, GraphNodeNONE, GraphNodeMeta
from ..routines import PropagationRoutine, RegularRoutine


class ProtocolGraph:
    """Class representing a schedule of the protocol"""
    def __init__(self, protocol: Protocol, root_node: GraphNodeBase,
                 state: ndarray, propagator_factory: PropagatorFactory,
                 label=None):
        self._protocol = protocol
        self._root_node = root_node
        self.tstate = UserTState(self.options["start_time"], state,
                                 propagator_factory, label=label)
        self.ROUTINES: tuple[RoutineABC] = ()
        self.RESULTS: dict[float, dict] = {}
        self.graph_ready = False

    def __repr__(self) -> str:
        return self.map.values().__str__()

    def __len__(self) -> int:
        return len(self.map.values())

    @property
    def label(self):
        return self.tstate.label

    def makeRoutines(self):
        if not self.graph_ready:
            raise ValueError("ProtocolGraph must be configured, first."
                             " Call .preprocessor().configure()")

        for node in self.getRank(-1):
            if node.options["name"] == "PROPAGATE":
                self.ROUTINES += (PropagationRoutine(node, self._protocol),)
            else:
                self.ROUTINES += (RegularRoutine(node, self._protocol),)

    @property
    def options(self) -> dict:
        return self.root._options

    @property
    def root(self) -> GraphNodeBase:
        return self._root_node

    @property
    def leafs(self) -> tuple[GraphNodeBase]:
        return self.getRank(-1)

    @property
    def map(self):
        return self.root.map

    @property
    def n_nodes(self):
        """Amount of nodes in the graph."""
        return len(self.map)

    @property
    def depth(self):
        """Number of ranks in the graph."""
        return len(max(self.map.keys(), key=lambda ID: len(ID.tuple)).tuple)

    def getRank(self, rank: int) -> tuple[GraphNodeBase]:
        """Return all nodes with given rank. 'rank' -1 returns the leafs"""
        if rank == -1:
            rank = self.depth - 1

        def filter_func(node: GraphNodeBase) -> bool:
            return node.ID.rank == rank

        return tuple(filter(filter_func, self.map.values()))

    def getNode(self, ID: GraphNodeID) -> GraphNodeBase:
        """Returns node with given tuple as ID.tuple, if it exists"""
        try:
            return self.map[ID]
        except KeyError:
            print(f"Node with ID {ID} not in graph.")
            return GraphNodeNONE()

    def getNodeFromTuple(self, ID_tuple: tuple) -> GraphNodeBase:
        """Returns node with given tuple as ID.tuple, if it exists"""
        ID = GraphNodeID(ID_tuple)
        return self.getNode(ID)

    def replaceNode(self, ID: GraphNodeID, options: dict) -> None:
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
