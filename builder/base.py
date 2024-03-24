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
