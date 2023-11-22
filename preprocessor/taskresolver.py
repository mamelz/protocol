from . import errors
from .user_graph import UserGraphNode
from ..graph.spec import GraphSpecification


class TaskResolver:
    """Resolves tasks into routines and replaces the task node with the
    routines in the parent's children.
    """

    def __init__(self, user_graph_spec: GraphSpecification,
                 predefined_tasks: dict[str, dict]):
        self._spec = user_graph_spec
        self._predef_tasks = predefined_tasks
        for task_opts in self._predef_tasks.values():
            if not isinstance(task_opts, dict):
                raise errors.TaskResolverError(
                    "Predefined tasks must be dict[str, dict] with "
                    "task_name: task_options pairs."
                )

    def resolve(self, task_node: UserGraphNode):
        if task_node.rank_name() != "Task":
            raise errors.TaskResolverError(
                ".resolve() has been called"
                f" with a non-task node: {task_node}")

        if task_node.type == "default":
            self._resolve_default(task_node)
        elif task_node.type == "predefined":
            self._resolve_predefined(task_node)
        else:
            raise errors.TaskResolverError(
                f"Unknown task type {task_node.type}")

    def _resolve_default(self, task_node: UserGraphNode):
        if task_node.type != "default":
            raise errors.TaskResolverError(
                f"Wrong type for task {task_node}")

        parent = task_node.parent
        routine_options = task_node.options["routines"]
        routine_nodes = tuple(
            UserGraphNode(parent, opts, rank=3) for opts in routine_options)
        parent.replace_child(
            task_node.ID.local,
            routine_nodes)

    def _resolve_predefined(self, task_node: UserGraphNode):
        if task_node.type != "predefined":
            raise errors.TaskResolverError(
                f"Wrong type for task {task_node}")

        inlined_task = UserGraphNode(
            task_node.parent,
            self._predef_tasks[task_node.options["task_name"]],
            rank=2)
        task_node.parent.replace_child(
            task_node.ID.local, (inlined_task,))
