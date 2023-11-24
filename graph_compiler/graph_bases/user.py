from .user_spec import USER_GRAPH_CONFIG_DICT
from ...graph.base import GraphNode, GraphNodeMeta, GraphRoot, GraphRootMeta
from ...graph.spec import GraphSpecification


class UserGraphNode(GraphNode, metaclass=GraphNodeMeta,
                    graph_spec=GraphSpecification(USER_GRAPH_CONFIG_DICT)):

    def _init_children(self):
        return super()._init_children()


class UserGraphRoot(GraphRoot, UserGraphNode, metaclass=GraphRootMeta):

    @property
    def stages(self):
        return self.children

    @property
    def start_time(self) -> float:
        return self.options["start_time"]

    @start_time.setter
    def start_time(self, new: float):
        self.options["start_time"] = new
