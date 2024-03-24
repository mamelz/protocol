from .inter_spec import INTER_GRAPH_CONFIG_DICT
from .. import GraphNode, GraphNodeMeta, GraphRoot, GraphRootMeta


class InterGraphNode(GraphNode, metaclass=GraphNodeMeta,
                     graph_spec=INTER_GRAPH_CONFIG_DICT):

    def _post_init(self):
        pass


class InterGraphRoot(GraphRoot, InterGraphNode, metaclass=GraphRootMeta):

    @property
    def num_stages(self):
        return len(self.stages)

    @property
    def stages(self):
        return self.children

    @property
    def start_time(self) -> float:
        return self.options["start_time"]

    @start_time.setter
    def start_time(self, new: float):
        self.options["start_time"] = new
