from .base import GraphNode, GraphNodeMeta, GraphRootMeta
from .spec import GraphSpecification
from ..settings.user_graph_cfg import USER_GRAPH_CONFIG_DICT


user_spec = GraphSpecification(USER_GRAPH_CONFIG_DICT)


class UserGraphNode(GraphNode, metaclass=GraphNodeMeta, graph_spec=user_spec):
    pass


class UserGraphRoot(UserGraphNode, metaclass=GraphRootMeta):
    pass
