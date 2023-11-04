# flake8: noqa
"""Functionality for preprocessing node options.

During preprocessing, node options are being checked for validity and missing
options are inferred from other sources such as the parent node, if possible.
"""
from ..graph import GRAPH_CONFIG
from ..graph.config import NodeType
from ..graph.configchecker import ConfigurationChecker
from ..graph.core import GraphNode, GraphRoot
from .core import process_graph


__all__ = [
    "main"
]
