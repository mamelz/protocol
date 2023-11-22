from . import errors
from .run_graph import RunGraphNode
from .user_graph import UserGraphNode
from ..graph.base import GraphNodeMeta


class StageCompiler:
    """Constructs RunGraph stages from UserGraph stages."""

    def __init__(self, in_type: GraphNodeMeta, out_type: GraphNodeMeta):
        self._in_type = in_type
        self._out_type = out_type

    def compile(self, stage_node: UserGraphNode,
                parent: RunGraphNode) -> RunGraphNode:
        if stage_node.rank_name() != "Stage":
            raise errors.StageCompilerError(
                "Input node must be of rank 'Stage'.")

        if not isinstance(stage_node, self._in_type):
            raise errors.StageCompilerError(
                f"Input stage must be instance of {self._in_type},"
                f" got {type(stage_node)}")

        if stage_node.type == "regular":
            self._compile_regular(stage_node)
        elif stage_node.type == "evolution":
            self._compile_evolution(stage_node)
        else:
            raise errors.StageCompilerError(
                f"Unknown stage type {stage_node.type}")
