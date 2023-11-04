from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .config import NodeType
    from .core import GraphNode

from . import errors
from . import GRAPH_CONFIG


class ConfigurationChecker:
    """Class for validating node options."""
    _graph_config = GRAPH_CONFIG

    def __init__(self, spec: NodeType):
        self._spec = spec

    def _check_specification(self, node: GraphNode):
        self._check_type(node)
        node_opts = node._options
        unknown = (
            node_opts.keys() - self._spec.options.keys() - {"type"})
        if any(unknown):
            raise errors.NodeOptionsError(
                f"Node {node} has unknown options: {unknown}"
            )

        invalid = self._spec.options.invalid_options(node._options)
        if any(invalid):
            err_str = f"Invalid node options: {invalid}\n"
            for key in invalid:
                err_str += f"'{key}':\n"
                err_str += (
                    "\tExpected types:"
                    f" {self._spec.options[key]['types']}\n")
                err_str += f"\tReceived: {node_opts[key]}\n"
            raise errors.NodeOptionsError(err_str)

        return

    def _check_type(self, node: GraphNode) -> None:
        parent_allowed_types = self._graph_config.get_specification(
            node.parent).allowed_types
        if node.parent.rank == -1:
            allowed_root_ranks = parent_allowed_types
            if node.rank_name() not in allowed_root_ranks:
                raise errors.NodeRankInvalidError(
                    f"Root node {node} has invalid rank:\n"
                    f"\t Allowed root ranks: {allowed_root_ranks}\n"
                    f"\t Received: {node.rank_name()}"
                    )
            else:
                return
        try:
            rank = parent_allowed_types[node.rank_name()]
        except KeyError:
            raise errors.NodeRankInvalidError(
                f"Node {node} has invalid rank:\n"
                f"\t Allowed ranks: {parent_allowed_types.keys()}\n"
                f"\t Received: {node.rank_name()}"
                )

        if self._spec.type not in rank:
            raise errors.NodeTypeInvalidError(
                f"Node {node} has invalid type:\n"
                f"\t Allowed types: {rank}\n"
                f"\t Received: {self._spec.type}"
                )

        return

    def check_valid(self, node: GraphNode) -> None:
        """Checks node options for validity.

        Returns:
            None

        Raises:
            NodeTypeError: Raised, whenever the node options are incompatible
                with the graph configuration.
        """
        self._check_specification(node)

        return

    def check_complete(self, node: GraphNode) -> bool:
        """Check node options for completeness and validity.

        Raises:
            NodeTypeError: Raised, when there are missing or invalid options.
        """
        miss_dict = self._spec.options.missing(node._options)
        for keysets in (miss_dict["mandatory_exclusive"] +
                        miss_dict["optional_exclusive"]):
            for miss_set in keysets:
                if any(miss_set):
                    return False

        for miss_set in (miss_dict["mandatory"] | miss_dict["optional"]):
            if any(miss_set):
                raise errors.NodeOptionsError(f"Missing options: {miss_set}")

        self.check_valid(node)

        return
