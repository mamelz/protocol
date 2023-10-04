"""Functionality for managing the specification of the graph.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import GraphNode

import itertools
from abc import ABC
from collections import UserDict
from collections.abc import Mapping
from dataclasses import dataclass

from . import errors
from ..utils import FrozenDict


class EmptyEntries(FrozenDict):
    """Class for empty entries."""
    dict = {}

    def __init__(self):
        super().__init__({})

    def missing(self, _: dict) -> set:
        """Return missing option keys."""
        return set()

    def check_options(self, _: dict) -> set:
        """Return invalid and valid option keys."""
        return (set(), set())


class MandatoryEntries(FrozenDict):
    """Dictionary containing mandatory entries."""
    def __init__(self, options_dict: dict[str, dict]):
        for d in options_dict.values():
            for key, value in d.items():
                if key != "types":
                    raise ValueError
                if not all(isinstance(t, type) for t in value):
                    raise ValueError
        super().__init__(options_dict)

    def __str__(self):
        out = ""
        for key in self:
            out += (f"Mandatory key {key}: types {self[key]['types']}\n")
        return out

    @property
    def names(self):
        return tuple(self._d.keys())

    def missing(self, opts: dict) -> set:
        """Return missing option keys."""
        return self.keys() - opts.keys()

    def check_options(self, opts: dict) -> tuple[set]:
        """Return invalid and valid option keys."""
        invalid_opts = set()
        valid_opts = set()
        for key, opt in self.items():
            try:
                opts_key = opts[key]
            except KeyError:
                invalid_opts.add(key)
                continue
            if not isinstance(opts_key, opt["types"]):
                invalid_opts.add(key)
            else:
                valid_opts.add(key)
        return (invalid_opts, valid_opts)


class OptionalEntries(FrozenDict):
    """Dictionary containing optional entries."""
    def __init__(self, options_dict: dict):
        for d in options_dict.values():
            for key, value in d.items():
                if key not in ("types", "default"):
                    raise ValueError
                if key == "default" and not isinstance(value, object):
                    raise ValueError
                if key == "types" and not all(
                        isinstance(t, type) for t in value):
                    raise ValueError
        super().__init__(options_dict)

    def __str__(self):
        out = ""
        for key in self:
            out += (f"Optional key {key}: types {self[key]['types']}\n"
                    f"                    default {self[key]['default']}\n")
        return out

    @property
    def names(self):
        return tuple(self._d.keys())

    def missing(self, opts: dict) -> set:
        """Return missing option keys."""
        return self.keys() - opts.keys()

    def check_options(self, opts: dict) -> tuple[set]:
        """Return invalid and valid option keys."""
        invalid_opts = set()
        valid_opts = set()
        for key in opts.keys() & self.keys():
            if opts[key] == self[key]["default"]:
                valid_opts.add(key)
            elif isinstance(opts[key], self[key]["types"]):
                valid_opts.add(key)
            else:
                invalid_opts.add(key)
        return (invalid_opts, valid_opts)


class ExclusiveEntries(ABC, tuple):

    @property
    def dict(self):
        return {k: v for ent in self for k, v in ent.items()}


class ExclusiveMandatoryEntries(ExclusiveEntries):

    def __new__(cls, exmanent: list) -> tuple[MandatoryEntries]:
        return super().__new__(
            ExclusiveMandatoryEntries,
            list(MandatoryEntries(elem) for elem in exmanent))

    def check_options(self, opts: dict) -> tuple[set]:
        """Return invalid and valid option keys."""
        invalid_opts = set()
        valid_opts = set()
        for gr in self:
            if len(gr.keys()) == 0:
                continue
            common_keys = gr.keys() & opts.keys()
            if len(common_keys) > 1:
                raise errors.NodeOptionsError(f"Got multiple exclusive keys:"
                                              f" {common_keys}")
            elif len(common_keys) == 0:
                raise errors.NodeOptionsError(
                    f"Missing one of options: {gr.keys()}.")
            key = (gr.keys() & opts.keys())[0]
            if not isinstance(opts[key], gr[key]["types"]):
                invalid_opts.add(key)
            else:
                valid_opts.add(key)
        return (invalid_opts, valid_opts)

    def missing(self, opts: dict) -> tuple[set]:
        """Return missing option keys."""
        missing = ()
        for gr in self:
            gr_missing = gr.missing(opts)
            if len(gr_missing) < 2:
                continue
            missing += (gr_missing,)
        return missing


class ExclusiveOptionalEntries(ExclusiveEntries):

    def __new__(cls, exoptent: list) -> tuple[OptionalEntries]:
        return super().__new__(
            ExclusiveOptionalEntries,
            list(OptionalEntries(elem) for elem in exoptent))

    def missing(self, opts: dict) -> tuple[set]:
        """Return missing option keys."""
        missing = ()
        for gr in self:
            gr_missing = gr.missing(opts)
            if len(gr_missing) < 2:
                continue
            missing += (gr_missing,)
        return missing

    def check_options(self, opts: dict) -> tuple[set]:
        """Return invalid and valid option keys."""
        invalid_opts = set()
        valid_opts = set()
        for gr in self:
            common_keys = gr.keys() & opts.keys()
            if len(common_keys) > 1:
                raise errors.NodeOptionsError(f"Got multiple exclusive keys:"
                                              f" {common_keys}")
            if any(common_keys):
                key = list(common_keys)[0]
                if not isinstance(opts[key], gr[key]["types"]):
                    invalid_opts.add(key)
                else:
                    valid_opts.add(key)
        return (invalid_opts, valid_opts)


@dataclass(frozen=True, slots=True)
class NodeOptions(Mapping):
    """The options of a particular node type."""
    mandatory: MandatoryEntries
    mandatory_exclusive: ExclusiveMandatoryEntries
    optional: OptionalEntries
    optional_exclusive: ExclusiveOptionalEntries

    @classmethod
    def make(cls, options: dict):
        try:
            mandatory = MandatoryEntries(options["mandatory"])
        except KeyError:
            mandatory = EmptyEntries()
        try:
            mandatory_exclusive = ExclusiveMandatoryEntries(
                options["mandatory-exclusive"])
        except KeyError:
            mandatory_exclusive = ExclusiveMandatoryEntries([{}])
        try:
            optional = OptionalEntries(options["optional"])
        except KeyError:
            optional = EmptyEntries()
        try:
            optional_exclusive = ExclusiveOptionalEntries(
                options["optional-exclusive"])
        except KeyError:
            optional_exclusive = ExclusiveMandatoryEntries([{}])

        return cls(
            mandatory,
            mandatory_exclusive,
            optional,
            optional_exclusive)

    def __getitem__(self, key):
        return self._all_dict[key]

    def __iter__(self):
        return iter(self._all_dict)

    def __len__(self):
        return len(self._all_dict)

    @property
    def _all_dict(self):
        return (
            dict(self.mandatory) |
            dict(self.optional) |
            self.mandatory_exclusive.dict |
            self.optional_exclusive.dict
            )

    def check_options(self, options: dict) -> tuple[set]:
        """Return invalid and valid option keys."""
        _options = options.copy()
#        if "type" in _options.keys():
#            del _options["type"]
        trimmed_options = _options
        checked_options = {
            "mandatory": self.mandatory.check_options(trimmed_options),
            "mandatory_exclusive": self.mandatory_exclusive.check_options(
                trimmed_options),
            "optional": self.optional.check_options(trimmed_options),
            "optional_exclusive": self.optional_exclusive.check_options(
                trimmed_options)
        }

        out = [set(), set()]
        for tup in checked_options.values():
            out[0] |= tup[0]
            out[1] |= tup[1]

        return tuple(out)

    def validate_options(self, options: dict) -> bool:
        """Check if all option keys are known and valid."""
        checked_opts = self.check_options(options)
        # invalid options found
        if any(checked_opts[0]):
            return False

        # unknown options found
        if any(options.keys() - checked_opts[1]):
            return False

        missing = self.missing(options)
        missing = (
            missing["mandatory"] |
            set(itertools.chain.from_iterable(missing["mandatory_exclusive"]))
            )
        if any(missing):
            return False

        return True

    def missing(self, options: dict) -> dict:
        """Determine the missing mandatory options."""
        return {
            "mandatory": self.mandatory.missing(options),
            "mandatory_exclusive": self.mandatory_exclusive.missing(options),
            "optional": self.optional.missing(options),
            "optional_exclusive": self.optional_exclusive.missing(options)
        }

    def invalid_options(self, options: dict) -> set:
        """Return invalid option keys."""
        _options = options.copy()
        if "type" in _options.keys():
            del _options["type"]
        trimmed_options = _options
        checked_options = {
            "mandatory": self.mandatory.check_options(trimmed_options),
            "mandatory_exclusive": self.mandatory_exclusive.check_options(
                trimmed_options),
            "optional": self.optional.check_options(trimmed_options),
            "optional_exclusive": self.optional_exclusive.check_options(
                trimmed_options)
        }
        invalid_keys = set()
        for ch_op in checked_options.values():
            invalid_keys |= ch_op[0]

        return invalid_keys


class NodeType:
    """A particular node type of a rank."""
    def __init__(self, rank, type, options: dict,
                 graph_config: GraphConfiguration):
        self.rank = rank
        self.type = type
        self.options = NodeOptions.make(
            options)
        self._graph_config = graph_config

    def __repr__(self):
        return f"NodeType {self.rank}::{self.type}"

    @property
    def allowed_types(self):
        return self._graph_config._dict["allowed_types"][self.rank][self.type]


class Rank(UserDict):
    """A rank in the configuration."""
    def __init__(self, name: str, rank_dict: dict,
                 graph_config: GraphConfiguration):
        self._graph_config = graph_config
        self.name = name
        super().__init__(rank_dict)
        for key, value in rank_dict.items():
            self[key] = NodeType(self.name, key, value, self._graph_config)

    def __str__(self):
        return self.name

    @property
    def types(self):
        return tuple(self.values())

    @property
    def type_names(self):
        return tuple(self.keys())

    def type(self, type_name: str = None) -> NodeType:
        """Return configuration of specified node type.

        If node_type is None and only one node type is defined,
        return that type configuration.

        Args:
            type_name (str, optional): Name of node type. Defaults to None.

        Returns:
            Node: The configuration of the node type.
        """
        if type_name is None and len(self.keys()) == 1:
            return tuple(self.values())[0]
        return self[type_name]


@dataclass
class GraphConfiguration:
    """Class storing all configuration parameters of the graph."""
    _dict: FrozenDict

    def __init__(self, config: dict):
        self._dict = config
        try:
            none_rank = self._dict["ranks"]["NONE"]
            raise errors.GraphError("The 'NONE' rank is reserved for"
                                    " internal use.")
        except KeyError:
            none_rank = {"NONE": {"NONE": {}}}

        for rank_dict in self._dict["ranks"].values():
            for rtype_dict in rank_dict.values():
                rtype_dict["optional"]["type"] = {
                    "types": (str,),
                    "default": None
                }

        self._dict["ranks"].update(none_rank)
        self._dict = FrozenDict(self._dict)
        ranks_dict = self._dict["ranks"]
        for rank_name, opts in ranks_dict.items():
            self._dict["ranks"][rank_name] = Rank(rank_name, opts, self)
        self._ranks = {
            rname: self._dict["ranks"][rname] for rname
            in self._full_rank_names}

    @property
    def _full_rank_names(self) -> set:
        return self._dict["ranks"].keys()

    @property
    def depth(self):
        """The number of user-defined rank names."""
        return len(self.rank_names)

    @property
    def ranks(self):
        return {self._dict["ranks"][key] for key in self.rank_names}

    @property
    def rank_names(self) -> set:
        """Set containing all user-defined rank names."""
        return self._dict["ranks"].keys() - {"NONE"}

    @property
    def rank_map(self) -> map:
        """Mapping between rank index and rank names."""
        return self._dict["hierarchy"]

    def allowed_types(self, rank_type_tuple: tuple[str, str]) -> dict:
        """Return the allowed types for child nodes of a given node type."""
        rtt = rank_type_tuple
        return self.rank(rtt[0]).type(rtt[1]).allowed_types

    def get_specification(self, node: GraphNode) -> NodeType:
        """Return the specification of a node."""
        return self.rank(node.rank_name()).type(node.type)

    def rank(self, rank_name) -> Rank:
        """Return the specified rank of the configuration."""
        return self._ranks[rank_name]
