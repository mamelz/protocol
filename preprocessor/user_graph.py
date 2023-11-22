from ..graph.base import GraphNode, GraphNodeMeta, GraphRootMeta
from ..graph.spec import GraphSpecification
from ..settings.user_graph_cfg import USER_GRAPH_CONFIG_DICT


class UserGraphNode(GraphNode, metaclass=GraphNodeMeta,
                    graph_spec=GraphSpecification(USER_GRAPH_CONFIG_DICT)):
    pass


class UserGraphRoot(UserGraphNode, metaclass=GraphRootMeta):
    pass
