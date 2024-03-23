from . import InterGraphRoot, RunGraphRoot
from .stagecompiler import StageCompiler
from ..base import GraphProcessor


class Inter2RunProcessor(GraphProcessor):

    input_type = InterGraphRoot
    output_type = RunGraphRoot

    def __init__(self):
        self._stagecompiler = StageCompiler()

    def __call__(self, input: InterGraphRoot) -> RunGraphRoot:
        super().__call__(input)

        rungraph = RunGraphRoot({})
        rungraph.virtual_stages = []
        for i, stage in enumerate(input.stages):
            rungraph.virtual_stages += [
                self._stagecompiler.compile(stage, rungraph)]

        rungraph.children = rungraph.virtual_stages
        del rungraph.virtual_stages
        runspec = rungraph._GRAPH_SPEC
        runspec.processor.set_type(rungraph, True)
        runspec.processor.set_options(rungraph, True)
        runspec.processor.verify(rungraph, True)
        return rungraph
