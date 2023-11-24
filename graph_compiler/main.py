from . import errors
from .stagecompiler import StageCompiler
from .taskresolver import TaskResolver
from .graph_bases.user import UserGraphRoot
from .graph_bases.inter import InterGraphRoot
from .graph_bases.run import RunGraphRoot
from ..graph.spec import NodeConfigurationProcessor


class GraphCompiler:

    userspec = UserGraphRoot.graph_spec
    interspec = InterGraphRoot.graph_spec
    runspec = RunGraphRoot.graph_spec

    def __init__(self, user_graph: UserGraphRoot,
                 predefined_tasks: dict[str, dict] = {}):
        if not isinstance(user_graph, UserGraphRoot):
            raise errors.GraphProcessorError(
                "GraphProcessor must be initialized with an instance of"
                f" {UserGraphRoot} but got {type(user_graph)}.")

        if user_graph.graph_spec is not self.userspec:
            raise errors.GraphProcessorError(
                f"Graph {user_graph} has unexpected specification."
            )

        self._user_graph = user_graph.copy()
        self._inter_graph: InterGraphRoot = None
        self._predef_tasks = predefined_tasks

    def build(self) -> RunGraphRoot:
        """Preprocess, compile, verify and return."""
        self.preprocess()
        graph = self.compile()
        specproc = NodeConfigurationProcessor(graph.graph_spec)
        specproc.verify(graph, graph=True)
        return graph

    def compile(self) -> RunGraphRoot:
        """Compile the user graph to a run graph.

        During compilation, all implicit routines like propagation routines
        are constructed. Returns the compiled graph, an instance of
        RunGraphRoot.
        """
        run_graph = RunGraphRoot({})
        stagecompiler = StageCompiler(self._preprocessed_graph._CHILD_TYPE,
                                      run_graph._CHILD_TYPE)

        run_stages = [None] * self._preprocessed_graph.num_children
        for i, stage in enumerate(self._preprocessed_graph.children):
            run_stages[i] = stagecompiler.compile(stage, run_graph)

        run_graph.children = tuple(run_stages)

        return run_graph

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

        confprocessor.verify(node, graph=True)
