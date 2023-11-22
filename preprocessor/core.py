from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..graph.base import GraphNode, GraphRoot

from functools import wraps

from . import errors
from . import stage
from .user_graph import UserGraphNode
from .run_graph import RunGraphNode
from ..graph.spec import NodeConfigurationProcessor


class NodeProcessor:

    def __init__(self, node: UserGraphNode):
        self._graph_spec = node._GRAPH_SPEC






class NodeOptionsProcessor:
    """Class that bundles all functionality for processing of node options."""

    @staticmethod
    def _setup_if_needed(method):
        @wraps(method)
        def wrapped(self, node: GraphNode = None,
                    node_type=None):
            if node is not None:
                self._setup_processing(node, node_type)
            return method(self)

        return wrapped

    def __init__(self, graph_config):
        self._GRAPH_CONFIG = graph_config

    def _clear(self):
        del self._node
        del self._spec
        del self._checker

    def _determine_specification(self):
        """Determine the specification that applies for the node."""
        node_rank = self._node.rank_name()
        if self._node.type is not None:
            return self._GRAPH_CONFIG.rank(node_rank).type(self._node.type)

        if len(self._GRAPH_CONFIG.rank(node_rank)) == 1:
            return self._GRAPH_CONFIG.rank(node_rank).type()

        # check if node options are only compatible with one type
        type_candidates = ()
        for type_ in self._GRAPH_CONFIG.rank(
                self._node.rank_name()).values():
            if type_.options.validate_options(self._node._options):
                type_candidates += (type_,)
        if len(type_candidates) == 1:
            return type_candidates[0]

        # check if parent determines unique type
        par = self._node.parent
        parent_spec = self._GRAPH_CONFIG.get_specification(par)
        num_allowed_types = len(parent_spec.allowed_types[
            self._node.rank_name()])
        if num_allowed_types == 1:
            node_type = parent_spec.allowed_types[
                self._node.rank_name()][0]
            return self._GRAPH_CONFIG.rank(
                self._node.rank_name()).type(node_type)
        else:
            raise errors.NodeTypeNotFoundError(
                f"Node type of node {self._node} could not be determined.")

    def _fetch_mandatory_exclusive(self, miss_dict: dict) -> dict:
        """Infer missing exclusive options from parent nodes."""
        fetched = {}
        for exgroup in miss_dict["mandatory_exclusive"]:
            for key in exgroup:
                try:
                    fetched[key] = self._node.options[key]
                    break
                except KeyError:
                    continue

        return fetched

    def _fetch_optional_exclusive(self, miss_dict: dict) -> dict:
        """Return dictionary with missing optional key: default value pairs."""
        fetched = {}
        for key in miss_dict["optional_exclusive"]:
            fetched[key] = self._spec.options.optional[key]["default"]

        return fetched

    def _fetch_mandatory_nonexclusive(self, miss_dict: dict) -> dict:
        """Infer missing non-exclusive options from parent nodes."""
        fetched = {}
        for key in miss_dict["mandatory"]:
            fetched[key] = self._node.options[key]

        return fetched

    def _fetch_optional_nonexclusive(self, miss_dict: dict) -> dict:
        """Return dictionary with missing optional key: default value pairs."""
        fetched = {}
        for key in miss_dict["optional"]:
            fetched[key] = self._spec.options.optional[key]["default"]

        return fetched

    def _fetch_missing_options(self, miss_dict: dict) -> dict:
        return (
            self._fetch_mandatory_exclusive(miss_dict) |
            self._fetch_mandatory_nonexclusive(miss_dict) |
            self._fetch_optional_exclusive(miss_dict) |
            self._fetch_optional_nonexclusive(miss_dict)
        )

    def _setup_processing(self, node: GraphNode, node_type):
        self._node = node
        if node_type is not None:
            self._node.type = node_type
        self._spec = self._determine_specification()
        if self._node.type is None:
            self._node.type = self._spec.type
        self._checker = ConfigurationChecker(self._spec)

        return

    @_setup_if_needed
    def check_complete(self):
        """Check, if all node options are set and valid."""
        self._checker.check_complete(self._node)

    @_setup_if_needed
    def fill_missing(self):
        """Try to fill in missing options."""
        missing_opts = self._spec.options.missing(self._node._options)
        fetched_opts = self._fetch_missing_options(missing_opts)
        self._node._options.update(fetched_opts)

    @_setup_if_needed
    def check_valid(self):
        """Check if any given node options are invalid."""
        self._checker.check_valid(self._node)

    def process(self, node: GraphNode, node_type: str = None):
        """Process the options of the given node.

        Checks the node for validity and sets missing options to their
        default values.
        """
        self._setup_processing(node, node_type)
        self.check_valid()
        self.fill_missing()
        self.check_complete()
        self._clear()

    @_setup_if_needed
    def process_routines(self):
        match self._node.rank:
            case 0:     # schedule
                for routine in self._node.leafs:
                    routine._options["tag"] = "USER"
            case 1:     # stage
                if self._node.type == "evolution":
                    for routine in self._node.leafs:
                        routine._options["type"] = "evolution"
                    stage.process_evolution(self._node)
            case 2:     # task
                pass
            case 3:     # routine
                pass
