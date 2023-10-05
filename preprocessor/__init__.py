# flake8: noqa
"""Functionality for preprocessing node options.

During preprocessing, node options are being checked for validity and missing
options are inferred from other sources such as the parent node, if possible.
"""
from ..graph import GRAPH_CONFIG
from .core import main


__all__ = [
    "main"
]
