from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..graph.spec import NodeSpecification

from abc import ABC, abstractmethod
import os
import yaml

from ..builder.graph_classes.user import UserGraphRoot
from ..graph.spec import GraphSpecification
from .graph_classes.yaml_spec import INPUT_CONFIG_DICT as _inputcfg
from .graph_classes.yaml import YAMLGraphRoot


parsingspec = GraphSpecification(_inputcfg)


class Parser(ABC):

    parsing_spec: GraphSpecification = parsingspec
    output_graph_type = UserGraphRoot


class FileParser(Parser):

    inputspec = Parser.parsing_spec.ranks["file"]

    def __init__(self, input_type: str):
        self._file_spec: NodeSpecification = self.inputspec.types[input_type]

    @abstractmethod
    def parse(self, config: dict) -> tuple:
        pass


class YAMLParser(FileParser):

    def __init__(self):
        super().__init__("yaml")

    def parse(self, config: dict) -> tuple[dict,
                                           dict[str, dict]]:
        yaml_graph = YAMLGraphRoot(config)
        self.parsing_spec.processor.process(yaml_graph, graph=True)
        schedules = tuple(sch.options.local for sch in yaml_graph.schedules)
        tasks_dict = {task.options["name"]: task for task in yaml_graph.tasks}

        return schedules, tasks_dict

    def parse_from_file(self, path: str) -> tuple[dict,
                                                  dict[str, dict]]:
        path = os.path.abspath(path)
        with open(path, "r") as stream:
            config = yaml.safe_load(stream)

        return self.parse(config)
