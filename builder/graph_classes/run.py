from __future__ import annotations

from .run_spec import RUN_GRAPH_CONFIG_DICT
from ...graph.base import (
    GraphNode,
    GraphNodeID,
    GraphNodeMeta,
    GraphRoot,
    GraphRootMeta
    )
from ...graph.spec import GraphSpecification


class RunGraphNode(GraphNode, metaclass=GraphNodeMeta,
                   graph_spec=GraphSpecification(RUN_GRAPH_CONFIG_DICT)):

    def __init__(self, parent: GraphNode, options: dict, rank: int = None,
                 ID: tuple = None):
        super().__init__(parent, options, rank)
        self._fixed_ID = GraphNodeID(ID) if ID is not None else None

    def _post_init(self):
        pass

    @property
    def ID(self) -> GraphNodeID:
        if self._fixed_ID is not None:
            return self._fixed_ID

        return GraphNodeID(
            (*self.parent.ID.tuple, self._get_children_index(
                self.parent.children)))

    @ID.setter
    def ID(self, new: tuple):
        self._fixed_ID = GraphNodeID(new)

    @ID.deleter
    def ID(self):
        del self._fixed_ID

    @property
    def num_routines(self):
        return len(self.routines)

    @property
    def routines(self) -> tuple[RunGraphNode]:
        return self.leafs


class RunGraphRoot(GraphRoot, RunGraphNode, metaclass=GraphRootMeta):

    @property
    def num_stages(self):
        return len(self.stages)

    @property
    def stages(self) -> tuple[RunGraphNode]:
        return self.children
