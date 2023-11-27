from .parser_spec import INPUT_CONFIG_DICT
from ...graph.base import GraphNode, GraphNodeMeta, GraphRoot, GraphRootMeta
from ...graph.spec import GraphSpecification


class YAMLGraphNode(GraphNode, metaclass=GraphNodeMeta,
                    graph_spec=GraphSpecification(INPUT_CONFIG_DICT)):

    def _init_children(self):
        pass


class YAMLGraphRoot(GraphRoot, YAMLGraphNode, metaclass=GraphRootMeta):

    @property
    def schedules_conf(self) -> list[dict]:
        return self.options.local["schedules"]

    @property
    def tasks_conf(self) -> dict[str, dict]:
        tasks_list: list = self.options.local["tasks"]
        tasks = {}
        for conf in tasks_list:
            name = conf["name"]
            del conf["name"]
            tasks[name] = conf

        return tasks
