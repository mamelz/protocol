from abc import ABC, abstractmethod

from ..graph.base import GraphNodeMeta


class GraphProcessor(ABC):

    class GraphProcessorError(Exception):
        pass

    input_type: GraphNodeMeta
    output_type: GraphNodeMeta

    @abstractmethod
    def __call__(self, input: GraphNodeMeta) -> GraphNodeMeta:
        if not isinstance(input, self.input_type):
            raise self.GraphProcessorError()

#    @classmethod
#    @property
#    def specs(cls) -> tuple[GraphSpecification]:
#        return (cls.userspec, cls.interspec, cls.runspec)

#    def _check(self, graph: GraphRoot):
#        if graph.graph_spec not in self.specs:
#            raise self.GraphProcessorError(
#                "Unknown specification."
#            )
#
#        if not isinstance(graph, GraphRoot):
#            raise self.GraphProcessorError(
#                f"Graph {graph} must be GraphRoot instance."
#            )
