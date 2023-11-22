from ..graph.base import GraphNode, GraphNodeMeta, GraphRootMeta
from ..graph.spec import GraphSpecification
from ..settings.run_graph_cfg import RUN_GRAPH_CONFIG_DICT


class RunGraphNode(GraphNode, metaclass=GraphNodeMeta,
                   graph_spec=GraphSpecification(RUN_GRAPH_CONFIG_DICT)):
    pass


class RunGraphRoot(RunGraphNode, metaclass=GraphRootMeta):
    pass