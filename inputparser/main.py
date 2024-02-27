from __future__ import annotations

from abc import ABC, abstractmethod
import os
import yaml

from ..graph.spec import GraphSpecification
from .graph_classes.yaml_spec import INPUT_CONFIG_DICT as _yaml_inputcfg
from .graph_classes.yaml import YAMLGraphRoot


class Parser(ABC):

    @abstractmethod
    def parse(self, config: dict) -> tuple:
        pass


class YAMLParser(Parser):

    parsing_spec = GraphSpecification(_yaml_inputcfg)

    def __init__(self):
        pass

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
