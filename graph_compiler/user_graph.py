from ..graph.base import GraphNode, GraphNodeMeta, GraphRoot, GraphRootMeta
from ..graph.spec import GraphSpecification
from ..settings.user_graph_cfg import USER_GRAPH_CONFIG_DICT


class UserGraphNode(GraphNode, metaclass=GraphNodeMeta,
                    graph_spec=GraphSpecification(USER_GRAPH_CONFIG_DICT)):
    pass


class UserGraphRoot(GraphRoot, UserGraphNode, metaclass=GraphRootMeta):

    @property
    def start_time(self) -> float:
        return self.options["start_time"]

    @start_time.setter
    def start_time(self, new: float):
        self.options["start_time"] = new
