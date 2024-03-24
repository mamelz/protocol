from __future__ import annotations

import os
import yaml

from ..graph_classes.parser.file import FileGraphRoot


class FileParser:

    def __init__(self):
        pass

    def parse_dict(self, config: dict) -> FileGraphRoot:
        filegraph = FileGraphRoot(config)
        filegraph._GRAPH_SPEC.processor.process(filegraph, graph=True)
        for node in filegraph.predeftasks.values():
            node._GRAPH_SPEC.processor.process(node, graph=True)
        return filegraph

    def parse_yaml(self, path: str) -> FileGraphRoot:
        path = os.path.abspath(path)
        with open(path, "r") as stream:
            config = yaml.safe_load(stream)

        return self.parse_dict(config)
