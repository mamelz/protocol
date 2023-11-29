from __future__ import annotations

from .run_spec import RUN_GRAPH_CONFIG_DICT
from ...graph.base import GraphNode, GraphNodeMeta, GraphRoot, GraphRootMeta
from ...graph.spec import GraphSpecification


class RunGraphNode(GraphNode, metaclass=GraphNodeMeta,
                   graph_spec=GraphSpecification(RUN_GRAPH_CONFIG_DICT)):

    @property
    def num_routines(self):
        return len(self.routines)

    @property
    def routines(self) -> tuple[RunGraphNode]:
        return self.leafs

    def _post_init(self):
        pass


class RunGraphRoot(GraphRoot, RunGraphNode, metaclass=GraphRootMeta):

    @property
    def num_stages(self):
        return len(self.stages)

    @property
    def stages(self) -> tuple[RunGraphNode]:
        return self.children
