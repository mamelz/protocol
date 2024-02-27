"""Functionality for managing the specification of the graph.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .base import GraphNode

from abc import ABC, abstractmethod
from collections import UserDict
from dataclasses import dataclass, field
from functools import cached_property

from .errors import NodeConfigurationError


class OptionsABC(dict, ABC):

    _KEYS: set
    _KIND: str

    def __init__(self, node_config: dict):
        try:
            dict.__init__(self, node_config[self._KIND])
        except KeyError:
            dict.__init__(self, {})

        for k, v in self.items():
            if any(v.keys() - self._KEYS):
                raise NodeConfigurationError(k)

    @abstractmethod
    def _verify_option(self, opt_key, opt_val):
        pass

    def check(self, node_opts: dict):
        comm_keys = self.keys() & node_opts.keys()
        if len(comm_keys) == 0:
            return
        for key in comm_keys:
            self._verify_option(key, node_opts[key])

    def missing_keys(self, node_opts: dict) -> set[str]:
        return set(self.keys() - node_opts.keys())


class ExclusiveOptionsABC(UserDict, ABC):

    _KEYS: set
    _KIND: str

    def __init__(self, node_config: dict):
        try:
            self.tuple: tuple[dict] = node_config[self._KIND]
        except KeyError:
            self.tuple = ()

        for group in self.tuple:
            if not isinstance(group, dict):
                raise NodeConfigurationError

            for v in group.values():
                unknown_keys = set(v.keys() - self._KEYS)
                if any(unknown_keys):
                    raise NodeConfigurationError(
                        f"Unknown keys {unknown_keys}.")

        self.data = dict(*self.tuple)

    def __iter__(self):
        return iter(self.tuple)

    @abstractmethod
    def _verify_option(self, opt_key, opt_val):
        pass

    def check(self, node_opts: dict):
        relevant_keys = node_opts.keys() & self.data.keys()
        relevant_opts = {k: v for k, v in node_opts.items()
                         if k in relevant_keys}

        for k, v in relevant_opts.items():
            self._verify_option(k, v)

    def missing_keys(self, node_opts: dict) -> set[str]:
        return set(self.data.keys() - node_opts.keys())

    def missing_groups(self, node_opts: dict) -> tuple[dict]:
        miss_groups = ()
        for group in self:
            comm_keys = group.keys() & node_opts.keys()
            if not any(comm_keys):
                miss_groups += (comm_keys,)

        return miss_groups


class MandatoryOptions(OptionsABC):

    _KEYS = {"types"}
    _KIND = "mandatory"

    def _verify_option(self, key, val):
        types = self[key]["types"]
        if not isinstance(val, types):
            raise NodeConfigurationError(
                f"Option entry '{key}' has invalid type.")


class MandatoryExclusiveOptions(ExclusiveOptionsABC):

    _KEYS = {"types"}
    _KIND = "mandatory-exclusive"

    def _verify_option(self, key, val):
        if not isinstance(val, self[key]["types"]):
            raise NodeConfigurationError(
                f"Option entry {key} has invalid type.")


class OptionalOptions(MandatoryOptions):

    _KEYS = {"types", "default"}
    _KIND = "optional"

    def _verify_option(self, key, val):
        if val == self[key]["default"]:
            return

        super()._verify_option(key, val)


class OptionalExclusiveOptions(MandatoryExclusiveOptions):

    _KEYS = {"types", "default"}
    _KIND = "optional-exclusive"

    def _verify_option(self, key, val):
        if val == self[key]["default"]:
            return

        super()._verify_option(key, val)


class NodeOptions(UserDict):

    def __init__(self, mand, mand_ex, opt, opt_ex):
        self._mand: MandatoryOptions = mand
        self._mand_ex: MandatoryExclusiveOptions = mand_ex
        self._opt: OptionalOptions = opt
        self._opt_ex: OptionalExclusiveOptions = opt_ex
        self.data = {
            **self._mand,
            **self._mand_ex.data,
            **self._opt,
            **self._opt_ex.data
            }

    @property
    def exclusive_keygroups(self) -> tuple[set[str]]:
        groups = tuple(g.keys() for g in self.mandatory_exclusive)
        groups += tuple(g.keys() for g in self.optional_exclusive)
        return groups

    @property
    def nonexclusive_keys(self) -> set[str]:
        keys = set()
        keys |= self.mandatory.keys()
        keys |= self.optional.keys()
        keys |= {"type"}
        return keys

    @property
    def mandatory(self):
        return self._mand

    @property
    def mandatory_exclusive(self):
        return self._mand_ex

    @property
    def optional(self):
        return self._opt

    @property
    def optional_exclusive(self):
        return self._opt_ex

    def check(self, node_opts: dict):
        """Checks node options for incompatibility with specification.

        Ignores missing options, only raises exceptions for invalid options.

        Args:
            node_opts (dict): Node options dictionary.

        Raises:
            NodeConfigurationError: Raised, if an option entry is incompatible
                with the specification.
        """
        opts_tup = (self._mand, self._mand_ex, self._opt, self._opt_ex)
        for opt in opts_tup:
            opt.check(node_opts)

        unknown_keys = set(node_opts.keys() - self.keys()) - {"type"}
        if any(unknown_keys):
            raise NodeConfigurationError(
                f"Unknown keys {unknown_keys}.")

    def verify(self, node_opts: dict):
        """Verify node options.

        Checks for incompatibility and completeness.

        Args:
            node_opts (dict): Node options dictionary.

        Raises:
            NodeConfigurationError: Raised, if an option entry is incompatible
                with the specification or if there are missing options.
        """
        self.check(node_opts)
        nonex_miss = self.nonexclusive_keys - node_opts.keys()
        ex_miss = ()
        for keys in self.exclusive_keygroups:
            if not any(keys & node_opts.keys()):
                ex_miss += (keys,)

        if not any((*nonex_miss, *ex_miss)):
            return

        err_msg = ("Missing node options:\n"
                   f"\t Non-exclusive: {nonex_miss}\n"
                   f"\t Exclusive: {ex_miss}")

        raise NodeConfigurationError(err_msg)


class NodeSpecification:

    def __init__(self, rankname: str, typename: str, node_options: dict,
                 allowed_children: dict[str, tuple]):
        self._rank = rankname
        self._type = typename
        self._dict = node_options
        self._mand = MandatoryOptions(node_options)
        self._mand_ex = MandatoryExclusiveOptions(node_options)
        self._opt = OptionalOptions(node_options)
        self._opt_ex = OptionalExclusiveOptions(node_options)
        self._allowed_children = allowed_children

    def __str__(self):
        return f"NodeSpecification: Rank {self.rankname}, Type {self.typename}"

    @property
    def allowed_children(self) -> dict[str, tuple]:
        return self._allowed_children

    @property
    def dictionary(self):
        return self._dict

    @property
    def options(self):
        return NodeOptions(self._mand, self._mand_ex, self._opt, self._opt_ex)

    @property
    def rankname(self):
        return self._rank

    @property
    def typename(self):
        return self._type


class RankSpecification:

    def __init__(self, rankname: str, rank_config: dict,
                 allowed_children: dict):
        self._rankname = rankname
        self._allowed_children = allowed_children
        self._types = {typename: NodeSpecification(
            self.name,
            typename,
            type_config,
            self._allowed_children[typename])
            for typename, type_config in rank_config.items()}

    @property
    def allowed_children(self) -> dict[str, dict[str, tuple]]:
        return self._allowed_children

    @property
    def name(self) -> str:
        return self._rankname

    @property
    def types(self) -> dict[str, NodeSpecification]:
        return self._types


@dataclass(frozen=True)
class GraphSpecification:

    _KEYS = {"ranks", "hierarchy", "allowed_children"}
    _dict: dict[str, dict] = field()

#    def __init__(self, graph_config: dict[str, dict]):
#        if not graph_config.keys() == self._KEYS:
#            raise NodeConfigurationError

#       self._dict = graph_config

    @cached_property
    def hierarchy(self) -> dict[str, int]:
        return self._dict["hierarchy"]

    @cached_property
    def ranks(self) -> dict[str, RankSpecification]:
        ranks = {}
        for rname, rdict in self._dict["ranks"].items():
            rank_children = self._dict["allowed_children"][rname]
            ranks[rname] = RankSpecification(rname, rdict, rank_children)
        return ranks

    @cached_property
    def processor(self):
        return NodeConfigurationProcessor(self)


class NodeConfigurationProcessor:

    @classmethod
    def from_dict(cls, config_dict: dict):
        return cls(GraphSpecification(config_dict))

    def __init__(self, specification: GraphSpecification):
        self._spec = specification

    def get_specification(self, node: GraphNode
                          ) -> NodeSpecification | tuple[NodeSpecification]:
        rankname = node.rank_name()
        if node.type is not None:
            return self._spec.ranks[rankname].types[node.type]

        types_dict = self._spec.ranks[rankname].types.copy()
        impossible_typenames = set()
        for typename, nodetype in types_dict.items():
            try:
                nodetype.options.check(node.options.local)
            except NodeConfigurationError:
                impossible_typenames |= {typename}

        incomplete_typenames = set()
        for typename, nodetype in types_dict.items():
            missing = (set(nodetype.options.mandatory.missing_keys(
                node.options.local))
                | set(nodetype.options.mandatory_exclusive.missing_keys(
                    node.options.local))
                )
            if len(missing) > 0:
                incomplete_typenames |= {typename}

        possible_typenames = set(types_dict.keys() - impossible_typenames)
        if len(possible_typenames) == 0:
            raise NodeConfigurationError(
                f"Node {node} has invalid options.")

        parentspec = self.get_specification(node.parent)
        try:
            parent_typenames = parentspec.allowed_children[rankname]
            parent_typenames = set(parent_typenames)
        except KeyError:
            raise NodeConfigurationError(f"Node {node} has invalid rank"
                                         f" for parent {node.parent}.")

        possible_typenames &= parent_typenames
        if len(possible_typenames) == 0:
            raise NodeConfigurationError(
                f"Node {node} has invalid options.")

        # if type is still ambiguous, filter out types that would
        # miss mandatory options
        if len(possible_typenames) > 1:
            possible_typenames -= incomplete_typenames

        if len(possible_typenames) == 1:
            typename = next(iter(possible_typenames))
            return self._spec.ranks[rankname].types[typename]
        elif len(possible_typenames) > 1:
            return tuple(self._spec.ranks[rankname].types[tname]
                         for tname in possible_typenames)
        else:
            raise NodeConfigurationError(f"Node {node} has invalid options.")

    def process(self, node: GraphNode, graph=False):
        self.set_type(node, graph)
        self.set_options(node, graph)
        self.verify(node, graph)

    def set_type(self, node: GraphNode, graph=False):
        if graph:
            for ch in node:
                self.set_type(ch)
            return

        spec = self.get_specification(node)
        if isinstance(spec, tuple):
            raise NodeConfigurationError(
                f"Ambiguous node type for node {node}.")
        if node.type is None:
            node.type = spec.typename

    def set_options(self, node: GraphNode, graph=False):
        if graph:
            for ch in node:
                self.set_options(ch)
            return

        spec = self.get_specification(node)

        mand_miss = spec.options.mandatory.missing_keys(node.options.local)
        opt_miss = spec.options.optional.missing_keys(node.options.local)
        mandex_miss = spec.options.mandatory_exclusive.missing_groups(
            node.options.local)
        optex_miss = spec.options.optional_exclusive.missing_keys(
            node.options.local)

        mand_fetched = {}
        opt_fetched = {}
        mandex_fetched = {}
        optex_fetched = {}

        for key in mand_miss:
            mand_fetched[key] = node.options[key]

        for key in opt_miss:
            try:
                opt_fetched[key] = node.options[key]
            except KeyError:
                opt_fetched[key] = spec.options[key]["default"]

        for key in optex_miss:
            try:
                optex_fetched[key] = node.options[key]
            except KeyError:
                optex_fetched[key] = spec.options[key]["default"]

        for group in mandex_miss:
            matches = ()
            for key in group:
                try:
                    mandex_fetched[key] = node.options[key]
                    matches += (key,)
                except KeyError:
                    continue

            if len(matches) > 1:
                raise NodeConfigurationError(
                    f"More than one exclusive option {matches}"
                    f" for node {node}")
            elif not any(matches):
                raise NodeConfigurationError(
                    f"Mandatory exclusive options {group} not found."
                )

        all_fetched = (mand_fetched
                       | opt_fetched
                       | mandex_fetched
                       | optex_fetched)

        node.options.update(all_fetched)
        spec.options.verify(node.options.local)

    def verify(self, node: GraphNode, graph=False):
        if graph:
            for ch in node:
                self.verify(ch)
            return

        self._verify_local(node)

    def _verify_local(self, node: GraphNode):
        spec = self.get_specification(node)
        try:
            spec.options.verify(node.options.local)
        except NodeConfigurationError as err:
            err_str = f"Node {node}:\n{err.message}"
            raise NodeConfigurationError(err_str)
