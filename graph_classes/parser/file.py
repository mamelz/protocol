from __future__ import annotations

from .file_spec import FILE_CONFIG_DICT
from .. import GraphNode, GraphNodeMeta, GraphRoot, GraphRootMeta
from ..builder import UserGraphRoot


class FileGraphNode(GraphNode, metaclass=GraphNodeMeta,
                    graph_spec=FILE_CONFIG_DICT):

    def _post_init(self):
        pass


class FileGraphRoot(GraphRoot, FileGraphNode, metaclass=GraphRootMeta):

    _rankname = "file"

    @property
    def schedules(self) -> tuple[UserGraphRoot]:
        if "schedules" not in self.options.local:
            return ()

        sched_opts = self.options.local["schedules"]
        return tuple(UserGraphRoot(opt) for opt in sched_opts)

    @property
    def predeftasks(self) -> dict[str, PreDefinedTask]:
        if "tasks" not in self.options.local:
            return ()

        task_opts = self.options.local["tasks"]
        pretasks = {opts["name"]: PreDefinedTask(self, opts)
                    for opts in task_opts}
        return pretasks


class PreDefinedTask(FileGraphNode, metaclass=GraphNodeMeta,
                     graph_spec=FILE_CONFIG_DICT):

    def _post_init(self):
        routine_opts = self.options.local["routines"]
        self.set_children((self.make_child(opt) for opt in routine_opts),
                          quiet=True)

    @property
    def name(self):
        return self._options["name"]

    @property
    def routines(self):
        return self.children
