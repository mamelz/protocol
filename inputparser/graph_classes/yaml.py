from .yaml_spec import INPUT_CONFIG_DICT
from ...graph.base import GraphNode, GraphNodeMeta, GraphRoot, GraphRootMeta
from ...graph.spec import GraphSpecification


class YAMLGraphNode(GraphNode, metaclass=GraphNodeMeta,
                    graph_spec=GraphSpecification(INPUT_CONFIG_DICT)):

    def _post_init(self):
        pass


class YAMLScheduleNode(YAMLGraphNode):

    _rankname = "schedule"


class YAMLRoutineNode(YAMLGraphNode):

    _rankname = "routine"


class YAMLTaskNode(YAMLGraphNode):

    _CHILD_TYPE = YAMLRoutineNode
    _rankname = "task"

    def _post_init(self):
        routine_opts: list = self.options.local["routines"]
        self.set_children((self.make_child(opt) for opt in routine_opts),
                          quiet=True)

    def make_child(self, opts: dict) -> GraphNodeMeta:
        return self._CHILD_TYPE(self, opts)

    @property
    def routines(self):
        return self.children


class YAMLGraphRoot(GraphRoot, YAMLGraphNode, metaclass=GraphRootMeta):

    _rankname = "file"

    def _post_init(self):
        self.set_children((*self.schedules, *self.tasks), quiet=True)

    @property
    def schedules(self) -> tuple[YAMLScheduleNode]:
        if "schedules" not in self.options.local:
            return ()

        sched_opts = self.options.local["schedules"]
        return tuple(YAMLScheduleNode(self, opt) for opt in sched_opts)

    @property
    def tasks(self) -> tuple[YAMLTaskNode]:
        if "tasks" not in self.options.local:
            return ()

        task_opts = self.options.local["tasks"]
        return tuple(YAMLTaskNode(self, opt) for opt in task_opts)
