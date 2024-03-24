from .routinetranslator import RoutineTranslator
from .taskresolver import TaskResolver
from ..base import GraphProcessor
from .. import UserGraphRoot, InterGraphNode, InterGraphRoot


class User2InterProcessor(GraphProcessor):

    input_type = UserGraphRoot
    output_type = InterGraphRoot

    def __init__(self, predefined_tasks: dict[str, dict]):
        self._routinetranslator = RoutineTranslator()
        self._taskresolver = TaskResolver(predefined_tasks)

    def __call__(self, input: UserGraphRoot) -> InterGraphRoot:
        super().__call__(input)

        userprocessor = input._GRAPH_SPEC.processor
        userprocessor.set_type(input, graph=True)
        self._taskresolver.inline(input, graph=True)
        userprocessor.set_type(input, graph=True)
        self._taskresolver.resolve(input, graph=True)
        userprocessor.set_options(input, graph=True)
        userprocessor.verify(input, graph=True)

        intergraph: InterGraphNode = self.output_type(
            {
                "start_time": input.options["start_time"]
                }
            )

        self._routinetranslator(input, intergraph)
        intergraph._GRAPH_SPEC.processor.process(intergraph, True)
        return intergraph
