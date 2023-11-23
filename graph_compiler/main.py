from . import errors
from .stagecompiler import StageCompiler
from .taskresolver import TaskResolver
from .run_graph import RunGraphRoot
from .user_graph import UserGraphRoot
from ..graph.spec import NodeConfigurationProcessor


class GraphProcessor:

    def __init__(self, root: UserGraphRoot,
                 predefined_tasks: dict[str, dict] = {}):
        if not isinstance(root, UserGraphRoot):
            raise errors.GraphProcessorError(
                "GraphProcessor must be initialized with an instance of"
                f" {UserGraphRoot} but got {type(root)}.")

        self._user_graph = root
        self._preprocessed_graph = root.copy()
        self._user_graph_spec = root.graph_spec
        self._run_graph = RunGraphRoot({"stages": []})
        self._run_graph_spec = self._run_graph.graph_spec
        self._predef_tasks = predefined_tasks

    def preprocess(self):
        """Process the user graph node options.

        Checks the user graph for validity and sets missing node options
        to their default values.
        """
        taskresolver = TaskResolver(self._user_graph_spec, self._predef_tasks)
        confprocessor = NodeConfigurationProcessor(self._user_graph_spec)

        for node in self._preprocessed_graph:
            confprocessor.set_type(node)

        for node in self._preprocessed_graph:
            if node.rank == 2:
                assert node.rank_name() == "Task"
                taskresolver.resolve(node)

        for node in self._preprocessed_graph:
            confprocessor.set_type(node)
            confprocessor.set_options(node)
            confprocessor.verify(node)

        for node in self._preprocessed_graph:
            confprocessor.verify(node)

    def compile(self) -> RunGraphRoot:
        """Compile the user graph to a run graph.

        During compilation, all implicit routines like propagation routines
        are constructed in their respective stages. The resulting graph (root)
        only contains the minimum amount of information needed for execution
        and is an instance of RunGraphRoot.
        """
        stagecompiler = StageCompiler(self._preprocessed_graph._CHILD_TYPE,
                                      self._run_graph._CHILD_TYPE)
        user_stages = self._preprocessed_graph.children
        run_stages = [None] * len(user_stages)

        for i, stage in user_stages:
            run_stages[i] = stagecompiler.compile(stage, self._run_graph)

        self._run_graph.set_children(run_stages)

        return self._run_graph
