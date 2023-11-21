"""Module implementing a class representing a tree graph. The purpose of the
graph is to store options from a nested dictionary as found in a YAML file,
while preserving the hierarchical structure.
The main attribute of any node of the graph is a dictionary-like object
called 'options'. If a necessary option of a node is missing, it is inferred
from its parent nodes, if available.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Self
if TYPE_CHECKING:
    from .config import GraphSpecification

import functools
import json
from abc import (
    ABCMeta,
    abstractmethod,
    abstractclassmethod
    )
from collections import UserDict
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import chain

import numpy as np


@dataclass(frozen=True, slots=True)
class GraphNodeID:
    """Unique ID for nodes of the graph."""
    tuple: tuple
    local: int = field(init=False)
    rank: int = field(init=False)

    def __post_init__(self):
        try:
            object.__setattr__(self, "local", self.tuple[-1])
        except IndexError:
            object.__setattr__(self, "local", None)
        object.__setattr__(self, "rank", len(self.tuple) - 1)

    def __iter__(self):
        return iter(self.tuple)

    def __repr__(self):
        return f"ID {self.tuple}"

    def __str__(self):
        return f"{self.tuple}"


NoneID = GraphNodeID(())


@dataclass(frozen=True)
class GraphNodeNONE:
    """Dummy node acting as parent for the root."""
    children = ()
    ID: GraphNodeID = GraphNodeID(())
    num_children = 0
    rank: int = -1
    type = "NONE"

    def __init__(self, *_):
        pass

    def __repr__(self) -> str:
        return f"NONE_Node: {self.ID}"

    def rank_name(self):
        return "NONE"


class GraphNodeABCMeta(ABCMeta):
    pass
    #def __new__(mcls, name, bases, attrs):
    #    return super().__new__(mcls, name, bases, attrs)

    #def __init__(cls, name, bases, attrs):
    #    return super().__init__(name, bases, attrs)


class GraphNodeMeta(GraphNodeABCMeta):
    """Meta class for creation of node classes."""
    def __new__(mcls, name, bases, attrs, *, graph_spec: GraphSpecification
                ) -> GraphNode:
        if len(bases) == 0:
            raise ValueError("Must be subclass of at least one"
                             " GraphNode class.")
        for base in bases:
            if not issubclass(base, GraphNode):
                raise TypeError("Must only subclass GraphNode class.")

        return super().__new__(mcls, name, bases, attrs)

    def __init__(cls, name, bases, attrs, graph_spec: GraphSpecification):
        super().__init__(name, bases, attrs)
        cls._GRAPH_SPEC = graph_spec
        cls._CHILD_TYPE = cls


class GraphNode(metaclass=ABCMeta):
    """Abstract base class for nodes of the graph."""

    _GRAPH_SPEC: GraphSpecification
    _CHILD_TYPE: GraphNodeMeta

    @classmethod
    def make_child(cls, parent, options, rank) -> Self:
        return cls(parent, options, rank)

    def __init__(self, parent: GraphNode, options: dict, rank: int = None):
        if rank is None:
            rank = parent.rank + 1
        self._rank = rank
        self._parent = parent
        self.__children = ()
        self._options = options
        if not self.isleaf:
            try:
                self.__children = NodeChildren(
                    self._CHILD_TYPE(self, opts) for opts in self._options[
                        f"{self.rank_name(self.rank + 1).lower()}s"])
            except KeyError:
                pass

    def __iter__(self):
        """Iterator cycling through all nodes of local graph."""
        return iter(self.map.values())

    def __repr__(self) -> str:
        return f"{self.rank_name(self.rank).capitalize()}: {self.ID}"

    @property
    def _children(self):
        return self.__children

    @_children.setter
    def _children(self, new_ch):
        self.__children = NodeChildren(new_ch)
        self.root.register_children_mutation(self)

    @property
    def _it(self):
        if self.rank == self.leaf_rank - 1:
            return chain((self,), self.children)
        return chain((self,), *(ch._it for ch in self.children))

    @property
    def _it_id(self):
        if self.rank == self.leaf_rank - 1:
            return chain((self.ID,), (ch.ID for ch in self.children))
        return chain((self.ID,), *(ch._it_id for ch in self.children))

    @property
    def ancestors(self):
        """Return parents up to root."""
        if self.rank == 0:
            return ()

        def anc_gen():
            node = self.parent
            while True:
                yield node
                if node.isroot:
                    break
                node = node.parent
        return tuple(anc_gen())

    @property
    def children(self) -> tuple[GraphNode]:
        return self._children

    @property
    def external_options(self) -> dict:
        """External routine options, not defined by yaml file."""
        try:
            return self._options["external"]
        except KeyError:
            if self.rank == 0:
                raise KeyError("No external options set.")
            return self.parent.external_options

    @property
    def isleaf(self) -> bool:
        """
        True when this node is a leaf node, i.e. has lowest possible rank.
        """
        return self.rank == self.leaf_rank

    @property
    def isroot(self) -> bool:
        """True, if node is the root node of the graph, i.e. has rank 0."""
        return self.rank == 0

    @property
    def ID(self) -> GraphNodeID:
        parent = self.parent
        if parent.ID.local is None:
            return GraphNodeID((0,))
        return GraphNodeID(
            (*parent.ID.tuple, parent.children.index(self)))

    @property
    def leafs(self) -> tuple[GraphNode]:
        """The lowest-rank child nodes that originate from this node."""
        if self.rank + 1 == self.leaf_rank:
            return self.children

        leafs_tuple = ()
        for child in self.children:
            leafs_tuple += child.leafs
        return leafs_tuple

    @property
    def leaf_rank(self) -> int:
        return max(self._GRAPH_SPEC.hierarchy.values())

    @property
    def map(self) -> dict[GraphNodeID, GraphNode]:
        return self.root.map

    @property
    def num_children(self):
        """The number of children of this node."""
        return len(self.children)

    @property
    def options(self):
        return GraphNodeOptions(self)

    @property
    def parent(self) -> Self:
        return self._parent

    @property
    def rank(self) -> int:
        """The rank index of the node."""
        return self._rank

    @functools.cached_property
    def root(self) -> GraphRoot:
        """Returns the highest-rank parent node."""
        return self.parent_of_rank(0)

    @property
    def type(self) -> str:
        try:
            return self._options["type"]
        except KeyError:
            return None

    @type.setter
    def type(self, new: str):
        if self.type is not None:
            raise ValueError(
                f"Node type already set to {self.type}")
        self._options["type"] = new

    def _local_map(self) -> dict:
        """Return map of self and all subordinate nodes."""
        return dict(zip(self._it_id, self._it))

    def add_children_from_options(self, options: Sequence[dict] | dict = {}):
        """Create new child nodes and append them to this node's children.

        Empty dicionaries as options generate empty child nodes.

        Args:
            options (Sequence[dict] | dict): The options of the new child
                nodes.
        """
        if not isinstance(options, Sequence):
            self._children = (
                *self._children, type(self)(self, options))
            return
        else:
            self._children = (
                *self._children,
                *(type(self)(self, opts) for opts in options))
            return

    def clear_children(self):
        """Sets 'children' attribute to empty tuple."""
        self._children = ()

    def get_parent(self, n: int = 1) -> Self:
        """
        Returns n-th parent node, default is n=1 corresponding to the direct
        parent.
        """
        if n > self.rank:
            raise ValueError("n cannot be greater than rank.")
        if n == 1:
            return self._parent
        parent = self
        while parent.rank > self.rank - n:
            parent = parent._parent
        return parent

    def goto(self, target_id: GraphNodeID | Sequence) -> Self:
        """Return node with given ID."""
        common_rank = 0
        for i, (j, k) in tuple(enumerate(zip(self.ID, target_id)))[1:]:
            if j != k:
                common_rank = i - 1
                break
        node = self.parent_of_rank(common_rank)
        for idx in tuple(target_id)[common_rank + 1:]:
            node = node.children[idx]
        return node

    def next(self, minrank=0, _i=0) -> Self:
        """
        The next node, the immediate sibling to the right. Parameter '__i' is
        for internal use.
        """
        if (self.ID.local < self.parent.num_children - 1) and (
                self.rank > minrank):
            if _i == 0:
                return self.parent.children[self.ID.local + 1]
            else:
                result: GraphNode = self.parent.children[self.ID.local + 1]
                while _i > 0:
                    _i -= 1
                    result = result.children[0]
                return result
        elif self.rank > minrank:
            return self.parent.next(minrank=minrank, _i=_i + 1)
        else:
            raise IndexError

    def parent_of_rank(self, n) -> Self:
        """Returns the parent with specified rank."""
        return self.get_parent(self.rank - n)

    def previous(self, __i=0) -> Self:
        """The previous node, the immediate sibling to the left."""
        if self.ID.local > 0:
            if __i == 0:
                return self.parent.children[self.ID.local - 1]
            else:
                result: GraphNode = self.parent.children[
                    self.ID.local - 1]
                while __i > 0:
                    __i -= 1
                    result = result.children[-1]
                return result
        elif self.rank > 0:
            return self.parent.previous(__i + 1)
        else:
            return None

    def rank_name(self, rank=None) -> str:
        """
        The name of a specified rank. If rank is None, returns rank name
        of node.
        """
        rank_dict = {v: k for k, v in self._GRAPH_SPEC.hierarchy.items()}
        if rank is None:
            return rank_dict[self.rank]
        else:
            return rank_dict[rank]

    def set_children_from_options(self, options: Sequence[dict] = ({},)
                                  ) -> None:
        """Replace all children from sequence of options.

        This deletes all children of the node and constructs new one from the
        options. Options can be empty dictionaries.
        Args:
            options (Sequence[dict]): The options of the new children.
        """
        self._children = tuple(type(self)(self, opts)
                               for opts in options)
        return


class GraphRootMeta(GraphNodeMeta):

    def __new__(mcls, name, bases: tuple[GraphNodeMeta], attrs) -> GraphRoot:
        if len(bases) != 1:
            raise ValueError("GraphRoot class must subclass exactly one class,"
                             " the type of the graph nodes.")
        if not issubclass(bases[0], GraphNode):
            raise TypeError("Base class must be subclass of GraphNode.")
        if issubclass(bases[0], GraphRoot):
            raise TypeError("Base class must not be subclass of GraphRoot.")

        bases += (GraphRoot,)

        return super().__new__(
            mcls, name, bases, attrs, graph_spec=bases[0]._GRAPH_SPEC)

    def __init__(cls, name, bases: tuple[GraphNodeMeta], attrs):
        super().__init__(name, bases, attrs, graph_spec=bases[0]._GRAPH_SPEC)
        cls._CHILD_TYPE = bases[0]


class GraphRoot(GraphNode, metaclass=ABCMeta):
    """Class for the root node of a graph.

    Contains the additional attribute ._map and provides functionality to
    ensure integrity of the graph options throughout execution.
    """
#    def __new__(cls, options: dict):
#        obj = super().__new__(cls, GraphNodeNONE(), options)
#        return obj

    def __init__(self, options: dict):
        super().__init__(GraphNodeNONE(), options)
        self._mutated_nodes_ids = set()
        self._make_map()

    @property
    def map(self) -> dict[GraphNodeID, GraphNode]:
        """Return map of the graph. Refreshes map if needed."""
        if not hasattr(self, "_map"):
            return {}
        self._validate_map()
        return self._map

    def _make_hash(self):
        self._hash = json.dumps(self._map, sort_keys=True)

    def _make_map(self):
        """Write children of all ranks into ._map."""
        self._map = self._local_map()
        self._mutated_nodes_ids: set[GraphNodeID] = set()

    def _validate_map(self):
        """Check if nodes have been mutated and reconstruct parts of the map,
        if needed.
        """
        if not hasattr(self, "_map"):
            self._make_map()
            return
        if self._mutated_nodes_ids == set():
            return

        only_leafs = True
        for node_id in self._mutated_nodes_ids:
            if node_id.rank != self.leaf_rank - 1:
                only_leafs = False
                break
        if only_leafs:      # only reconstructing the parents is sufficient
            for par in self._mutated_nodes_ids:
                self._map.update(self.goto(par)._local_map())
        else:               # need to reconstruct all entries
            self._make_map()
        self._mutated_nodes_ids = set()

    def get_generation(self, rank):
        """Return all nodes of a given rank."""
        node = self.goto((0,)*(rank + 1))
        while node is not None:
            yield node
            try:
                node = node.next()
            except IndexError:
                node = None

    def register_children_mutation(self, node: Self):
        """Register a mutation of the ._children attribute."""
        self._mutated_nodes_ids.add(node.ID)


class NodeChildren(tuple):
    """Thin subclass of tuple to store child nodes.

    The purpose of this class is to accelerate the .index() method that is used
    to infer node IDs in the .ID property of graph nodes. This is achieved by
    storing the object ids of all child nodes in a np.ndarray and using
    np.where() to find the index.
    """
    def __new__(cls, children_iterable, **tup_kwargs):
        return super().__new__(
            cls, children_iterable, **tup_kwargs)

    def __init__(self, _):
        self._id_arr = np.array(tuple(id(ch) for ch in self), copy=False)

    def __len__(self):
        return self._id_arr.size

    def index(self, node):
        """Return index of the given node in the children tuple."""
        return np.where(self._id_arr == id(node))[0][0]


class GraphNodeOptions(UserDict):
    """
    Dictionary-like class that automatically infers option from parent
    nodes if it is not found in current node. However, setting and deleting
    options acts only on the current node.
    """
    def __init__(self, node: GraphNode):
        self._node = node
        super().__init__(self._node._options)
        self.data: dict = self._node._options

    def __getitem__(self, __key: str):
        try:
            return super().__getitem__(__key)
        except KeyError:
            rname = self._node.rank_name().lower()
            for par in self._node.ancestors:
                try:
                    return par.options["global_options"][rname][
                        __key]
                except KeyError:
                    continue
            raise KeyError(f"Option {__key} not found.")

    @property
    def local(self):
        return self.data
