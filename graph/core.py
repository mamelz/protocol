"""Module implementing a class representing a tree graph. The purpose of the
graph is to store options from a nested dictionary as found in a YAML file,
while preserving the hierarchical structure.
The main attribute of any node of the graph is a dictionary-like object
called 'options'. If a necessary option of a node is missing, it is inferred
from its parent nodes, if available.
"""
from __future__ import annotations

import functools
import json
from collections import UserDict
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Mapping

from . import GRAPH_CONFIG


@dataclass(frozen=True)
class GraphNodeID:
    """Unique ID for nodes of the graph."""
    _tuple: tuple

    def __iter__(self):
        return iter(self._tuple)

    def __repr__(self):
        return f"ID {self._tuple}"

    def __str__(self):
        return f"{self.tuple}"

    @functools.cached_property
    def tuple(self):
        return self._tuple

    @functools.cached_property
    def local(self):
        """
        The index of the node in the local tree, i.e. the index
        in the parent's children list.
        """
        return self.tuple[-1]

    @functools.cached_property
    def parent(self):
        """ID of the parent node."""
        return GraphNodeID(self.tuple[:-1])

    @functools.cached_property
    def rank(self):
        return len(self.tuple) - 1


NoneID = GraphNodeID(())


class GraphNodeMeta(type):
    """Meta class for creation of node classes."""
    _CONFIG = GRAPH_CONFIG

    def __new__(mcls, name, bases, attrs, rank: int = None):
        new_attrs = {
            "_RANK_NAMES": mcls._CONFIG.rank_map,
            "_LEAF_RANK": mcls._CONFIG.depth - 1
        }
        attrs.update(new_attrs)
        if rank is None:
            return super().__new__(mcls, name, bases, attrs)

        cls_name = f"{mcls._CONFIG.rank_map[rank].capitalize()}Node"
        if rank < mcls._CONFIG.depth - 1:
            attrs.update({f"{mcls._CONFIG.rank_map[rank + 1].lower()}s":
                         property(lambda obj: obj._children)})
        attrs["_RANK"] = rank
        bases = (GraphNode,) if rank != 0 else (GraphRoot,)
        return super().__new__(mcls, cls_name, bases, attrs)

    def __call__(cls: GraphNodeMeta,
                 parent: GraphNode | GraphNodeNONE,
                 options: Mapping):
        rank = parent.rank + 1
        if rank - 1 == cls._LEAF_RANK:
            raise ValueError("Cannot create children of leaf nodes.")
        name = cls.__name__
        bases = cls.__bases__
        attrs = {}
        cls = GraphNodeMeta.__new__(GraphNodeMeta, name, bases, attrs,
                                    rank=rank)
        obj: GraphNode = cls.__new__(cls, parent, options)
#        obj._RANK = rank
        cls.__init__(obj, parent, options)
        return obj


class GraphNode(metaclass=GraphNodeMeta):
    """Base class for nodes of the graph."""
    @classmethod
    def rank_name(cls, rank=None) -> str:
        """
        The name of a specified rank. If rank is None, returns rank name
        of node.
        """
        if rank is None:
            return cls._RANK_NAMES[cls._RANK]
        elif rank <= cls._LEAF_RANK:
            return cls._RANK_NAMES[rank]
        else:
            return ""

    def __init__(self, parent: GraphNode, options: dict):
        self._RANK = parent.rank + 1
        self._parent = parent
        self.__children = ()
        self._options = options
        if not self.isleaf:
            try:
                self.__children = tuple(
                    GraphNode(self, opts) for opts in self._options[
                        f"{self.rank_name(self.rank + 1).lower()}s"])
            except KeyError:
                pass

    def __iter__(self):
        """Iterator cycling through all nodes of local graph."""
        return iter(self.map.values())
#        self.__it = iter(self._it)
#        return self

#    def __next__(self):
#        return next(self.__it)

    def __repr__(self) -> str:
        return f"{self.rank_name(self.rank).capitalize()}: {self.ID}"

    @property
    def _children(self):
        return self.__children

    @_children.setter
    def _children(self, new_ch):
        self.__children = new_ch
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
        if parent.ID == NoneID:
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
        return type(self)._LEAF_RANK

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
    def parent(self) -> GraphNode:
        return self._parent

    @property
    def rank(self) -> int:
        """The rank index of the node."""
        return self._RANK

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

    def add_children_from_options(self, options: Sequence[dict] | dict = {}
                                  ) -> None:
        """Create new child nodes and append them to this node's children.

        Empty dicionaries as options generate empty child nodes.

        Args:
            options (Sequence[dict] | dict): The options of the new child
                nodes.
        """
        if not isinstance(options, Sequence):
            self._children = (
                *self._children, GraphNode(self, options))
            return
        else:
            self._children = (
                *self._children,
                *(GraphNode(self, opts) for opts in options))
            return

    def clear_children(self):
        """Sets 'children' attribute to empty tuple."""
        self._children = ()

    def get_parent(self, n: int = 1) -> GraphNode:
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

    def goto(self, target_id: GraphNodeID | Sequence) -> GraphNode:
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

    def next(self, minrank=0, _i=0) -> GraphNode:
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

    def parent_of_rank(self, n) -> GraphNode:
        """Returns the parent with specified rank."""
        return self.get_parent(self.rank - n)

    def previous(self, __i=0) -> GraphNode:
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

    def set_children_from_options(self, options: Sequence[dict] = ({},)
                                  ) -> None:
        """Replace all children from sequence of options.

        This deletes all children of the node and constructs new one from the
        options. Options can be empty dictionaries.
        Args:
            options (Sequence[dict]): The options of the new children.
        """
        self._children = tuple(GraphNode(self, opts)
                               for opts in options)
        return


class GraphRoot(GraphNode, metaclass=GraphNodeMeta):
    """Class for the root node of a graph.

    Contains the additional attribute ._map and provides functionality to
    ensure integrity of the graph options throughout execution.
    """

    def __new__(cls, *args, **kwargs):
        self = object.__new__(cls)
        self._mutated_nodes_ids = set()
        return self

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mutated_nodes_ids = set()
        self._make_map()

    @property
    def map(self) -> dict:
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
                print({par: self.goto(par)})
                self._map.update(self.goto(par)._local_map())
        else:               # need to reconstruct all entries
            print(self._mutated_nodes_ids)
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

    def register_children_mutation(self, node: GraphNode):
        """Register a mutation of the ._children attribute."""
        self._mutated_nodes_ids.add(node.ID)


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
        return f"NONE: {self.ID}"

    def rank_name(self):
        return "NONE"


class GraphNodeOptions(UserDict):
    """
    Dictionary-like class that automatically infers option from parent
    nodes if it is not found in current node. However, setting and deleting
    options acts only on the current node.
    """
    def __init__(self, node: GraphNode):
        self._node = node
        super().__init__(self._node._options)
        self.data = self._node._options

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
