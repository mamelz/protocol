"""Module implementing a class representing a tree graph. The purpose of the
graph is to store options from a nested dictionary as found in a YAML file,
while preserving the hierarchical structure.
The main attribute of any node of the graph is a dictionary-like object
called 'options'. If a necessary option of a node is missing, it is passed
down from its parent nodes, if available.
"""
from __future__ import annotations

from collections import UserDict
from dataclasses import dataclass
from typing import Mapping, Union

from .settings import SETTINGS

_VERBOSE = SETTINGS.VERBOSE


@dataclass(frozen=True)
class GraphNodeID:
    """
    Unique immutable ID for nodes of the graph.
    """
    tuple: tuple

    def __str__(self):
        return f"{self.tuple}"

    @property
    def local(self):
        """
        The index of the node in the local tree, i.e. the index
        in the parent's children list.
        """
        return self.tuple[-1]

    @property
    def parent(self):
        """ID of the parent node."""
        return GraphNodeID(self.tuple[:-1])

    @property
    def rank(self):
        return len(self.tuple) - 1


class GraphNodeMeta(type):
    """Meta class for creation of node classes."""
    # _RANK_NAMES: tuple[str]

    @classmethod
    def fromRank(mcls, rank: int, rank_names: tuple) -> GraphNodeBase:
        """Returns class for nodes of rank 'rank'."""
        cls_name = f"{rank_names[rank]}Node"
        attrs = {"_RANK_NAMES": rank_names,
                 "_RANK": rank}
        if rank < len(rank_names) - 1:
            attrs.update({"_CHILD_CLASS": mcls.fromRank(rank + 1,
                                                        rank_names)})
        return mcls.__new__(mcls, cls_name, (GraphNodeBase,), attrs)

    def __call__(cls: GraphNodeMeta,
                 parent: Union[GraphNodeBase, GraphNodeNONE],
                 options: Mapping):

        _leaf_rank = len(cls._RANK_NAMES) - 1

        if parent.rank == _leaf_rank:
            return GraphNodeNONE

        if parent.rank < _leaf_rank - 1:
            child_rank_name = cls._RANK_NAMES[parent.rank + 2]

            def children(obj: GraphNodeBase):
                return obj.children

            setattr(cls, f"{child_rank_name.lower()}s",
                    property(children))

        obj: GraphNodeBase = cls.__new__(cls, parent, options)
        cls.__init__(obj, parent, options)
        assert cls._RANK == obj.rank
        return obj


class GraphNodeBase:
    """Base class for nodes of the graph."""
    _RANK_NAMES: tuple[str]
    _RANK: int
    _CHILD_CLASS: GraphNodeMeta

    @staticmethod
    def _getIDFromParent(parent: Union[GraphNodeBase, GraphNodeNONE])\
            -> GraphNodeID:
        """Infer own ID from the parent node."""
        self_sibling_idx = len(parent.children)
        parent_id_aslist = list(parent.ID.tuple)
        parent_id_aslist.append(self_sibling_idx)
        return GraphNodeID(tuple(parent_id_aslist))

    @classmethod
    def _LEAF_RANK(cls):
        return len(cls._RANK_NAMES) - 1

    @classmethod
    def rank_name(cls, rank=None) -> str:
        """
        The name of a specified rank. If rank is None, returns rank name
        of node.
        """
        if rank is None:
            return cls._RANK_NAMES[cls._RANK]
        elif rank <= cls._LEAF_RANK():
            return cls._RANK_NAMES[rank]
        else:
            return None

    @classmethod
    @property
    def isleaf(cls) -> bool:
        """
        True when this node is a leaf node, i.e. has lowest possible rank.
        """
        return (cls._RANK == cls._LEAF_RANK())

    def __init__(self, parent: GraphNodeBase, options: dict):
        self._parent = parent
        self._options = options
        self._ID = self._getIDFromParent(parent)
        if _VERBOSE:
            print(f"{self.rank_name(self.rank).upper()}: {self.ID}")
        self._children: tuple[GraphNodeBase] = ()
        children_rank_name = self.rank_name(self.rank + 1)
        if children_rank_name is not None:
            try:
                children_options_list =\
                    self.options[f"{children_rank_name.lower()}s"]
            except KeyError:
                children_options_list = []
        else:
            children_options_list = []
        for child_options in children_options_list:
            self.add_child(child_options)

    def __repr__(self) -> str:
        return f"{self.rank_name(self.rank).upper()}_NODE: {self.ID}"

    @property
    def children(self):
        return self._children

    @property
    def external_options(self) -> dict:
        """External routine options, not defined by yaml file."""
        try:
            return self._options["external"]
        except KeyError:
            if self._RANK == 0:
                raise KeyError("No external options set.")
            return self.parent.external_options

    @property
    def leafs(self) -> tuple[GraphNodeBase]:
        """The lowest-rank child nodes that originate from this node."""
        if self.isleaf:
            return (self,)

        leafs_tuple = ()
        for child in self.children:
            leafs_tuple += child.leafs
        return leafs_tuple

    @property
    def leaf_rank(self) -> int:
        return self._LEAF_RANK()

    @property
    def ID(self):
        return self._ID

    @property
    def map(self) -> dict[GraphNodeID, GraphNodeBase]:
        """
        Returns a dictionary, containing the {ID: Node} pairs of the node
        and all lower-rank nodes of the branch.
        """
        result = {}
        result[self.ID] = self
        children_map = {}
        if self.num_children != 0:
            for child in self.children:
                children_map.update(child.map)
        result.update(children_map)
        return result

    @property
    def num_children(self):
        """The number of children of this node."""
        return len(self.children)

    @property
    def options(self):
        return GraphNodeOptions(self)

    @property
    def parent(self):
        return self._parent

    @property
    def rank(self) -> int:
        """The rank index of the node."""
        return self._RANK

    @property
    def root(self) -> GraphNodeBase:
        """Returns the highest-rank parent node."""
        return self.parent_of_rank(0)

    def add_child(self, options=None):
        """
        Adds a child node with given options. If options is None, creates empty
        child node.
        """
        if options is None:
            options = {}
        self._children += (self._CHILD_CLASS(self, options),)
        return

    def clear_children(self):
        """Sets 'children' attribute to empty tuple."""
        self._children = ()

    def get_option(self, key: str, _rank_name: str = None, _evo=False):
        """
        Looks for options with specified key in 'self._options'. If
        self.options does not contain the key, looks for the key in
        the parent node's attribute 'global_options'.
        """
        try:
            if _rank_name is None:
                return self._options[key]
            else:
                if _evo:
                    return self._options["global_options"][
                        _rank_name.lower()]["evolution"][key]
                else:
                    return self._options["global_options"][
                        _rank_name.lower()][key]
        except KeyError:
            if isinstance(self.parent, GraphNodeNONE):
                raise KeyError
            elif _rank_name is None:
                return self.parent.get_option(
                    key, _rank_name=self.rank_name(self.rank), _evo=_evo)
            else:
                return self.parent.get_option(key, _rank_name=_rank_name,
                                              _evo=_evo)

    def get_parent(self, n: int = 1) -> GraphNodeBase:
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

    def next(self, _i=0) -> GraphNodeBase:
        """
        The next node, the immediate sibling to the right. Parameter '_i' is
        for internal use.
        """
        if self.ID.local < len(self.parent.children) - 1:
            if _i == 0:
                return self.parent.children[self.ID.local + 1]
            else:
                result: GraphNodeBase = self.parent.children[
                    self.ID.local + 1]
                while _i > 0:
                    _i -= 1
                    result = result.children[0]
                return result
        elif self.rank > 0:
            return self.parent.next(_i + 1)
        else:
            return GraphNodeNONE()

    def parent_of_rank(self, n) -> GraphNodeBase:
        """Returns the parent with specified rank."""
        return self.get_parent(self.rank - n)

    def previous(self, _i=0) -> GraphNodeBase:
        """
        The previous node, the immediate sibling to the left. Parameter '_i'
        is for internal use.
        """
        if self.ID.local > 0:
            if _i == 0:
                return self.parent.children[self.ID.local - 1]
            else:
                result: GraphNodeBase = self.parent.children[
                    self.ID.local - 1]
                while _i > 0:
                    _i -= 1
                    result = result.children[-1]
                return result
        elif self.rank > 0:
            return self.parent.previous(_i + 1)
        else:
            return GraphNodeNONE()


@dataclass(frozen=True)
class GraphNodeNONE:
    """'None' implementation for GraphNode"""
    rank: int = -1
    ID: GraphNodeID = GraphNodeID(())
    children = ()

    def __init__(self, *_):
        pass

    def __repr__(self) -> str:
        return f"NONE: {self.ID}"


class GraphNodeOptions(UserDict):
    """
    Dictionary-like class that automatically infers option from parent
    nodes if it is not found in current node. However, setting and deleting
    options acts only on the current node.
    """
    def __init__(self, node: GraphNodeBase):
        self._node = node
        super().__init__(self._node._options)

    def __getitem__(self, __key: str):
        try:
            return self._node._options[__key]
        except KeyError:
            pass
        try:
            evolution = self._node.get_option("evolution")
        except KeyError:
            evolution = False

        if evolution:
            return self._node.get_option(__key, _evo=True)
        else:
            return self._node.get_option(__key)

    def __setitem__(self, __key: str, __value) -> None:
        return self._node._options.__setitem__(__key, __value)

    def __delitem__(self, __key: str) -> None:
        return self._node._options.__delitem__(__key)
