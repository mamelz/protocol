from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .base import GraphNode

from collections import UserDict
from dataclasses import dataclass, field

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
