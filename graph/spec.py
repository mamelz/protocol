"""Functionality for managing the specification of the graph.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .base import GraphNode

from abc import ABC, abstractmethod

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

    def missing(self, node_opts: dict) -> set[str]:
        return set(self.keys() - node_opts.keys())


class ExclusiveOptionsABC(tuple[dict], ABC):

    _KEYS: set
    _KIND: str

    def __new__(cls, node_config: dict):
        try:
            obj: tuple[str, dict] = tuple.__new__(
                cls, node_config[cls._KIND])
        except KeyError:
            obj: tuple[str, dict] = tuple.__new__(cls, ())

        for d in obj:
            if not isinstance(d, dict):
                raise NodeConfigurationError

            for k, v in d.items():
                if any(v.keys() - cls._KEYS):
                    raise NodeConfigurationError

        return obj

    @abstractmethod
    def _verify_option(self, opt_key, opt_val):
        pass

    def check(self, node_opts: dict):
        for group in self:
            comm_keys = group.keys() & node_opts.keys()
            if len(comm_keys) > 1:
                raise NodeConfigurationError("More than one exclusive option.")
            if len(comm_keys) == 0:
                return

            key = next(iter(comm_keys))
            self._verify_option(key, node_opts[key])

    def keys(self) -> set[str]:
        keys = set()
        for d in self:
            keys |= d.keys()
        return keys

    def missing(self, node_opts: dict) -> tuple[set[str]]:
        missing_groups = ()
        for group in self:
            comm_keys = group.keys() & node_opts.keys()
            if len(comm_keys) == 0:
                missing_groups += set(group.keys())

        return missing_groups


class MandatoryOptions(OptionsABC):

    _KEYS = {"types"}
    _KIND = "mandatory"

    def _verify_option(self, opt_key, opt_val):
        types = self[opt_key]["types"]
        if not isinstance(opt_val, types):
            raise NodeConfigurationError(
                f"Option entry {opt_key} has invalid type.")


class MandatoryExclusiveOptions(ExclusiveOptionsABC):

    _KEYS = {"types"}
    _KIND = "mandatory-exclusive"

    def _verify_option(self, opt_key, opt_val):
        for g in self:
            try:
                types = g[opt_key]["types"]
                break
            except KeyError:
                continue

        if not isinstance(opt_val, types):
            raise NodeConfigurationError(
                f"Option entry {opt_key} has invalid type.")


class OptionalOptions(OptionsABC):

    _KEYS = {"types", "default"}
    _KIND = "optional"

    def _verify_option(self, opt_key, opt_val):
        types = self[opt_key]["types"]
        default = self[opt_key]["default"]
        if not (isinstance(opt_val, types) or opt_val == default):
            raise NodeConfigurationError(
                f"Option entry {opt_key} has invalid type.")


class OptionalExclusiveOptions(ExclusiveOptionsABC):

    _KEYS = {"types", "default"}
    _KIND = "optional-exclusive"

    def _verify_option(self, opt_key, opt_val):
        for g in self:
            try:
                types = g[opt_key]["types"]
                default = g[opt_key]["default"]
                break
            except KeyError:
                continue

        if not (isinstance(opt_val, types) or opt_val == default):
            raise NodeConfigurationError(
                f"Option entry {opt_key} has invalid type.")


class NodeOptions:

    def __init__(self, mand, mand_ex, opt, opt_ex):
        self._mand: MandatoryOptions = mand
        self._mand_ex: MandatoryExclusiveOptions = mand_ex
        self._opt: OptionalOptions = opt
        self._opt_ex: OptionalExclusiveOptions = opt_ex

    @property
    def all_keys(self):
        keys = set()
        keys |= self.mandatory.keys()
        keys |= self.mandatory_exclusive.keys()
        keys |= self.optional.keys()
        keys |= self.optional_exclusive.keys()
        keys |= {"type"}
        return keys

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

        unknown_keys = set(node_opts.keys() - self.all_keys)
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

        if not any(nonex_miss) and not any(ex_miss):
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
        self._mand = MandatoryOptions(node_options)
        self._mand_ex = MandatoryExclusiveOptions(node_options)
        self._opt = OptionalOptions(node_options)
        self._opt_ex = OptionalExclusiveOptions(node_options)
        self._allowed_children = allowed_children

    def __str__(self):
        return f"NodeSpecification: Rank {self.rankname}, Type {self.typename}"

    @property
    def options(self):
        return NodeOptions(self._mand, self._mand_ex, self._opt, self._opt_ex)

    @property
    def allowed_children(self) -> dict[str, tuple]:
        return self._allowed_children

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


class GraphSpecification:

    _KEYS = {"ranks", "hierarchy", "allowed_children"}

    def __init__(self, graph_config: dict):
        if not graph_config.keys() == self._KEYS:
            raise NodeConfigurationError

        self._hierarchy = graph_config["hierarchy"]
        self._ranks = {}
        for rname, rdict in graph_config["ranks"].items():
            rank_children = graph_config["allowed_children"][rname]
            self._ranks[rname] = RankSpecification(rname, rdict, rank_children)

    @property
    def hierarchy(self) -> dict[str, int]:
        return self._hierarchy

    @property
    def ranks(self) -> dict[str, RankSpecification]:
        return self._ranks


class NodeConfigurationProcessor:

    @classmethod
    def from_dict(cls, config_dict: dict):
        return cls(GraphSpecification(config_dict))

    def __init__(self, specification: GraphSpecification):
        self._spec = specification

    def get_specification(self, node: GraphNode
                          ) -> NodeSpecification | tuple(NodeSpecification):
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

        if len(possible_typenames) == 1:
            typename = next(iter(possible_typenames))
            return self._spec.ranks[rankname].types[typename]
        elif len(possible_typenames) > 1:
            return tuple(self._spec.ranks[rankname].types[tname]
                         for tname in possible_typenames)
        else:
            raise NodeConfigurationError(f"Node {node} has invalid options.")

    def set_type(self, node: GraphNode):
        spec = self.get_specification(node)
        if isinstance(spec, tuple):
            raise NodeConfigurationError(
                f"Ambiguous node type for node {node}.")
        if node.type is None:
            node.type = spec.typename

    def set_options(self, node: GraphNode):
        spec = self.get_specification(node)

        mand_miss = spec.options.mandatory.missing(node.options.local)
        opt_miss = spec.options.optional.missing(node.options.local)
        mandex_miss = spec.options.mandatory_exclusive.missing(
            node.options.local)
        optex_miss = spec.options.optional_exclusive.missing(
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
                opt_fetched[key] = spec.options.optional[key]["default"]

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
                    f"Ambiguous global options {matches} for node {node}")
            elif not any(matches):
                raise NodeConfigurationError(
                    f"Mandatory exclusive options {group} not found."
                )

        for group in optex_miss:
            matches = ()
            for key in group:
                try:
                    optex_fetched[key] = node.options[key]
                    matches += (key,)
                except KeyError:
                    continue

            if len(matches) > 1:
                raise NodeConfigurationError(
                    f"Ambiguous global options {matches} for node {node}")
            elif not any(matches):
                for key in group:
                    optex_fetched[key] = spec.options.optional_exclusive[
                        key]["default"]

        all_fetched = (mand_fetched
                       | opt_fetched
                       | mandex_fetched
                       | optex_fetched)

        node.options.update(all_fetched)
        spec.options.verify(node.options.local)

    def verify(self, node: GraphNode):
        spec = self.get_specification(node)
        spec.options.verify(node.options.local)
