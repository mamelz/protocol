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
    from .spec import GraphSpecification

import copy
import functools
import itertools
import json
import numpy as np
from abc import (
    ABCMeta,
    abstractmethod,
    )
from collections import UserDict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import cache
from itertools import chain


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


class NodeChildren(Sequence):

    def __init__(self, children_iterable):
        self._tuple: tuple[GraphNode] = tuple(children_iterable)
        self._id_arr = self._calculate_id_arr()

    def __getitem__(self, idx):
        return self._tuple[idx]

    def __iter__(self):
        return iter(self._tuple)

    def __len__(self):
        return self._id_arr.size

    def _calculate_id_arr(self) -> np.ndarray:
        return np.array(tuple(id(ch) for ch in self._tuple),
                        copy=False)

    @property
    def tuple(self):
        return self._tuple

    @tuple.setter
    def tuple(self, new: tuple[GraphNode]):
        self._tuple = new
        self._id_arr = self._calculate_id_arr()

    def index(self, node):
        """Return index of the given node in the children tuple."""
        return np.where(self._id_arr == id(node))[0][0]


class GraphNodeOptions(UserDict):
    """
    Dictionary-like class that automatically infers option from parent
    nodes if it is not found in current node. However, setting and deleting
    options acts only on the current node.
    """
    def __init__(self, node: GraphNode, node_options: dict):
        self._node = node
        super().__init__(node_options)
        self.data: dict = node_options

    def __str__(self):
        return str(self.data)

    def __getitem__(self, __key: str):
        try:
            return super().__getitem__(__key)
        except KeyError:
            if self._node.isroot:
                raise KeyError(f"Option {__key} not found.")

            rname = self._node.rank_name().lower()
            try:
                return self._node.parent.options[
                    "global_options"][rname][__key]
            except KeyError:
                raise KeyError(f"Option {__key} not found.")

    @property
    def local(self):
        return self.data


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


class GraphNodeMeta(GraphNodeABCMeta):
    """Meta class for creation of node classes."""
    def __new__(mcls, name, bases, attrs, *,
                graph_spec: GraphSpecification = None
                ) -> GraphNode:
        if len(bases) == 0:
            raise ValueError("Must be subclass of at least one"
                             " GraphNode class.")
        for base in bases:
            if not issubclass(base, GraphNode):
                raise TypeError("Must only subclass GraphNode classes.")

        return super().__new__(mcls, name, bases, attrs)

    def __init__(cls, name, bases, attrs,
                 graph_spec: GraphSpecification = None):
        super().__init__(name, bases, attrs)
        if graph_spec is not None:
            cls._GRAPH_SPEC = graph_spec
        else:
            cls._GRAPH_SPEC = bases[0]._GRAPH_SPEC

        if not hasattr(cls, "_CHILD_TYPE"):
            cls._CHILD_TYPE = cls


class GraphNode(metaclass=GraphNodeABCMeta):
    """Abstract base class for nodes of the graph."""

    _GRAPH_SPEC: GraphSpecification
    _CHILD_TYPE: GraphNodeMeta
    isroot = False

    def __init__(self, parent: GraphNode, options: dict, rank: int = None):
        self._spec = None
        if rank is None:
            rank = parent.rank + 1
        self._rank = rank
        self._parent = parent
        self._children = NodeChildren(())
        self._options = options
        self._node_options = GraphNodeOptions(self, self._options)
        self._post_init()

    def __iter__(self):
        """Iterator cycling through all nodes of local graph."""
        return iter(self.map.values())

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}: {self.rank_name().capitalize()}:"
            f" {self.ID}")

    @abstractmethod
    def _post_init(self):
        raise NotImplementedError

    def make_child(self, opts: dict) -> GraphNodeMeta:
        return self._CHILD_TYPE(self, opts)

    def _set_children_tuple(self, new: Iterable[GraphNode]):
        if not isinstance(new, tuple):
            new = tuple(iter(new))

        for node in new:
            if not isinstance(node, self._CHILD_TYPE):
                raise TypeError(
                    f"Node {node} has incompatible type.")

        for node in new:
            if node.parent is not self:
                raise ValueError("New nodes must have self as parent.")

        self._children.tuple = new

    @property
    def spec(self) -> GraphSpecification | None:
        return self._spec

    @property
    def children(self) -> NodeChildren:
        return self._children

    @children.setter
    def children(self, new: Iterable[GraphNode]):
        self._set_children_tuple(new)
        self.root.register_children_mutation(self)

    @children.deleter
    def children(self):
        self._set_children_tuple(())

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
    def isleaf(self) -> bool:
        """
        True when this node is a leaf node, i.e. has lowest possible rank.
        """
        return self.rank == self.leaf_rank

    @cache
    def _get_children_index(self, children: NodeChildren):
        return children.index(self)

    @property
    def ID(self) -> GraphNodeID:
        return GraphNodeID(
            (*self.parent.ID.tuple, self._get_children_index(
                self.parent.children)))

    @property
    def leafs(self) -> tuple[GraphNode]:
        """The lowest-rank child nodes that originate from this node."""
        if self.rank + 1 == self.leaf_rank:
            return self.children.tuple

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
        return self._node_options

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
            return self.options.local["type"]
        except KeyError:
            return None

    @type.setter
    def type(self, new: str):
        if self.type is not None:
            raise ValueError(
                f"Node type already set to {self.type}")
        self.options.local["type"] = new
        self._spec = self._GRAPH_SPEC.ranks[self.rank_name()].types[self.type]

    def _local_map(self) -> dict:
        """Return map of self and all subordinate nodes."""
        return dict(zip(self._it_id, self._it))

    def add_children(self, add: Iterable[GraphNode]):
        self.children = chain(self.children, add)

    def add_children_from_options(self, options: Iterable[dict] | dict = {}):
        """Create new child nodes and append them to this node's children.

        Empty dicionaries as options generate empty child nodes.

        Args:
            options (Sequence[dict] | dict): The options of the new child
                nodes.
        """
        if not isinstance(options, Iterable):
            self.children = (
                *self.children, self._CHILD_TYPE(self, options))
            return
        else:
            self.children = chain(self.children,
                                  (self.make_child(opt) for opt in options))
            return

    def clear_children(self):
        """Sets 'children' attribute to empty tuple."""
        del self.children

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

    def goto(self, *target_id: tuple[int]) -> Self:
        """Return node with given ID."""
        if not isinstance(target_id, tuple):
            raise TypeError

        common_rank = 0
        for i, (j, k) in tuple(enumerate(zip(self.ID, target_id)))[1:]:
            if j != k:
                common_rank = i - 1
                break
        node = self.parent_of_rank(common_rank)
        for idx in target_id[common_rank + 1:]:
            node = node.children[idx]
        return node

    def next(self, minrank=0, __i=0) -> Self:
        """
        The next node, the immediate sibling to the right. Parameter '__i' is
        for internal use.
        """
        if (self.ID.local < self.parent.num_children - 1) and (
                self.rank > minrank):
            if __i == 0:
                return self.parent.children[self.ID.local + 1]
            else:
                result: GraphNode = self.parent.children[self.ID.local + 1]
                while __i > 0:
                    __i -= 1
                    result = result.children[0]
                return result
        elif self.rank > minrank:
            return self.parent.next(minrank=minrank, __i=__i + 1)
        else:
            raise IndexError

    def parent_of_rank(self, n) -> Self:
        """Returns the parent with specified rank."""
        return self.get_parent(self.rank - n)

    def previous(self, __i=0) -> Self:
        """
        The previous node, the immediate sibling to the left. Parameter '__i'
        is for internal use.
        """
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
        if hasattr(self, "_rankname"):
            return self._rankname

        rank_dict = {v: k for k, v in self._GRAPH_SPEC.hierarchy.items()}
        if rank is None:
            return rank_dict[self.rank]
        else:
            return rank_dict[rank]

    def replace_child(self, index: int, new: Sequence[GraphNode]):
        """Replace a child with one or several nodes."""
        children_left = self.children[:index]
        children_right = self.children[index + 1:]
        self.children = tuple(itertools.chain(
            children_left,
            new,
            children_right
        ))

    def replace_child_from_options(self, index: int, options: Sequence[dict]):
        """Replace a child with one or several nodes constructed from
        sequence of options."""
        children_left = self.children[:index]
        children_right = self.children[index + 1:]
        new_children = (self._CHILD_TYPE(self, opts) for opts in options)
        complete_it = itertools.chain(children_left,
                                      new_children,
                                      children_right)
        self.children = tuple(itertools.chain.from_iterable(complete_it))

    def set_children(self, new: Iterable[GraphNode], quiet=False):
        """Set children to tuple of nodes. If 'quiet' is True,
        the child mutation will not be registered at the root.
        """
        if not quiet:
            self.children = new
        else:
            self._set_children_tuple(new)

    def set_children_from_options(self, options: Sequence[dict], quiet=False):
        """Replace all children from sequence of options.

        This deletes all children of the node and constructs new one from the
        options. Options can be empty dictionaries.
        Args:
            options (Sequence[dict]): The options of the new children.
        """
        ch_tup = tuple(self._CHILD_TYPE(self, opts) for opts in options)
        if not quiet:
            self.children = ch_tup
        else:
            self._set_children_tuple(ch_tup)


class GraphRootABCMeta(GraphNodeMeta, ABCMeta):

    def __new__(mcls, name, bases, attrs):
        return ABCMeta.__new__(mcls, name, bases, attrs)

    def __init__(cls, name, bases, attrs):
        ABCMeta.__init__(cls, name, bases, attrs)


class GraphRootMeta(GraphRootABCMeta):

    def __new__(mcls, name, bases: tuple[GraphNodeMeta], attrs):
        return super().__new__(
            mcls, name, bases, attrs)

    def __init__(cls, name, bases: tuple[GraphNodeMeta], attrs):
        super().__init__(name, bases, attrs)
        cls._CHILD_TYPE = bases[1]


class GraphRoot(GraphNode, metaclass=GraphRootABCMeta):
    """Class for the root node of a graph.

    Contains the additional property .map and provides functionality to
    ensure integrity of the graph options throughout execution.
    """

    isroot = True
    ID = GraphNodeID((0,))

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

            self._mutated_nodes_ids = set()
        else:               # need to reconstruct all entries
            self._make_map()

    def copy(self) -> Self:
        """Return a deep copy of the GraphRoot object, includes all children.
        """
        return copy.deepcopy(self)

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
        """Register a mutation of the .children attribute."""
        self._mutated_nodes_ids.add(node.ID)
