# flake8: noqa
"""Definition of the GraphNode class and related functionality."""
from .config import GraphConfiguration
from ..settings import SETTINGS
GRAPH_CONFIG = GraphConfiguration(SETTINGS.GRAPH_CONFIG)
from .core import (
    GraphNode,
    GraphNodeID,
    GraphNodeNONE,
    GraphRoot
)

__all__ = [
    "GRAPH_CONFIG",
    "GraphNode",
    "GraphNodeID",
    "GraphNodeNONE",
    "GraphRoot"
]