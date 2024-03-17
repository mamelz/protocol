from .graph_classes.user import UserGraphNode
from .. inputparser.graph_classes.yaml import YAMLTaskNode


_usrcfg = UserGraphNode.graph_spec


class TaskResolver:
    """Resolves tasks into routines and replaces the task node with the
    routines in the parent's children.
    """

    class TaskResolverError(Exception):
        pass

    def __init__(self, predefined_tasks: dict[str, dict]):
        self._predef_tasks = predefined_tasks
        for task_opts in self._predef_tasks.values():
            if not isinstance(task_opts, YAMLTaskNode):
                raise TypeError

    def inline(self, task_node: UserGraphNode, graph=False):
        if graph:
            for ch in task_node:
                self.inline(ch)
            return

        if task_node.rank_name() != "Task":
            return

        if task_node.type == "predefined-evolution":
            self._inline_evolution(task_node)
        elif task_node.type == "predefined-regular":
            self._inline_regular(task_node)
        else:
            return

    def _inline_evolution(self, task_node: UserGraphNode):
        taskname = task_node.options["name"]
        predef_task: YAMLTaskNode = self._predef_tasks[taskname]

        rout_opts = [r.options.local.copy() for r in predef_task.routines]
        for opt in rout_opts:
            try:
                time = task_node.options["stagetime"]
                time_key = "stagetime"
            except KeyError:
                time = task_node.options["systemtime"]
                time_key = "systemtime"

            opt[time_key] = time
            del opt["tasktime"]
            del opt["type"]

        inlined_opts = predef_task.options.local.copy()
        del inlined_opts["name"]
        inlined_opts["routines"] = rout_opts
        inlined_task = UserGraphNode(
            task_node.parent,
            inlined_opts,
            rank=2)
        _usrcfg.processor.process(inlined_task)
        task_node.parent.replace_child(
            task_node.ID.local, (inlined_task,))

    def _inline_regular(self, task_node: UserGraphNode):
        taskname = task_node.options["name"]
        predef_task: YAMLTaskNode = self._predef_tasks[taskname]
        inlined_task = UserGraphNode(
            task_node.parent,
            predef_task.options.local,
            rank=2)
        _usrcfg.processor.process(inlined_task)
        task_node.parent.replace_child(
            task_node.ID.local, (inlined_task,))

    def resolve(self, task_node: UserGraphNode, graph=False):
        if graph:
            for ch in task_node:
                self.resolve(ch)
            return

        if task_node.rank_name() != "Task":
            return

        if task_node.type == "default":
            self._resolve_default(task_node)
        else:
            raise self.TaskResolverError(
                f"Cannot resolve task type {task_node.type}")

    def _resolve_default(self, task_node: UserGraphNode):
        if task_node.type != "default":
            raise self.TaskResolverError(
                f"Wrong type for task {task_node}")

        parent = task_node.parent
        routine_options = task_node.options["routines"]
        routine_nodes = tuple(
            UserGraphNode(parent, opts, rank=3) for opts in routine_options)
        parent.replace_child(
            task_node.ID.local,
            routine_nodes)
