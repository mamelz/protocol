from . import GRAPH_CONFIG
from . import stage
from . import errors
from ..graph.config import NodeType
from ..graph.configchecker import ConfigurationChecker
from ..graph.core import GraphNode, GraphRoot


def main(graph: GraphRoot):
    for node in graph:
        preproc = NodePreprocessor(node)
        preproc.process_options()

    for node in graph:
        preproc = NodePreprocessor(node)
        preproc.process_routines()

    for node in graph:
        preproc = NodePreprocessor(node)
        preproc.process_options()


class NodePreprocessor:
    _GRAPH_CONFIG = GRAPH_CONFIG

    def __init__(self, node: GraphNode, node_type: str = None):
        self._node = node
        if node_type is not None:
            self._node.type = node_type
        self._spec = self._determine_specification()
        if self._node.type is None:
            self._node.type = self._spec.type
        self._checker = ConfigurationChecker(self._spec)

    def _determine_specification(self) -> NodeType:
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
        if len(parent_spec.allowed_types[self._node.rank_name()]) == 1:
            node_type = parent_spec.allowed_types[
                self._node.rank_name()][0]
            return self._GRAPH_CONFIG.rank(
                self._node.rank_name()).type(node_type)

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

    def _handle_missing_options(self):
        """Try to fill in missing options and validate them."""
        missing_opts = self._spec.options.missing(self._node._options)
        fetched_opts = self._fetch_missing_options(missing_opts)
        self._node._options.update(fetched_opts)

        return

    def process_options(self):
        self._checker.check_valid(self._node)
        self._handle_missing_options()
        self._checker.check_valid(self._node)
        if not self._checker.check_complete(self._node):
            raise errors.NodeOptionsError

        return

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

        return
