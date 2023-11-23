from ..graph.base import GraphNode, GraphNodeMeta, GraphRoot, GraphRootMeta
from ..graph.spec import GraphSpecification
from ..settings.run_graph_cfg import RUN_GRAPH_CONFIG_DICT


class RunGraphNode(GraphNode, metaclass=GraphNodeMeta,
                   graph_spec=GraphSpecification(RUN_GRAPH_CONFIG_DICT)):

    @property
    def num_routines(self):
        return len(self.routines)

    @property
    def routines(self):
        return self.leafs


class RunGraphRoot(GraphRoot, RunGraphNode, metaclass=GraphRootMeta):

    @property
    def num_stages(self):
        return len(self.stages)

    @property
    def stages(self):
        return self.children
