"""The builder converts the user-specified graph (UserGraph) configuration into
a RunGraph object. During building, any ambiguity is stripped from the
configuration.
"""
from ..graph_classes.builder import (
    InterGraphNode,
    InterGraphRoot,
    RunGraphNode,
    RunGraphRoot,
    UserGraphNode,
    UserGraphRoot
)
