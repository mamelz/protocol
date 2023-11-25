from __future__ import annotations

import functools
import typing
from abc import ABC

import numpy as np

from . import errors
from .stagecompiler import StageCompiler
from .taskresolver import TaskResolver
from .graph_classes.user import UserGraphRoot, UserGraphNode
from .graph_classes.inter import InterGraphRoot, InterGraphNode
from .graph_classes.run import RunGraphRoot
from ..graph.base import GraphRoot
from ..graph.spec import NodeConfigurationProcessor, GraphSpecification


def check_input(method):
    input_type = tuple(typing.get_type_hints(method).values())[0]

    @functools.wraps(method)
    def wrapped(obj: GraphProcessor, input_graph, **kwargs):
        if not isinstance(input_graph, input_type):
            raise TypeError
        return method(obj, input_graph, **kwargs)
    return wrapped


class GraphProcessor(ABC):

    userspec = UserGraphRoot.graph_spec
    intercls = InterGraphRoot
    interspec = InterGraphRoot.graph_spec
    runcls = RunGraphRoot
    runspec = RunGraphRoot.graph_spec

    @classmethod
    @property
    def specs(cls) -> tuple[GraphSpecification]:
        return (cls.userspec, cls.interspec, cls.runspec)

    def _check(self, graph: GraphRoot):
        if graph.graph_spec not in self.specs:
            raise errors.GraphProcessorError(
                "Unknown specification."
            )

        if not isinstance(graph, GraphRoot):
            raise errors.GraphProcessorError(
                f"Graph {graph} must be GraphRoot instance."
            )


class GraphBuilder(GraphProcessor):

    def __init__(self, predefined_tasks: dict[str, dict] = {}):
        self._predef_tasks = predefined_tasks
        self.preprocessor = Preprocessor(self._predef_tasks)
        self.compiler = StageCompiler(self.intercls._CHILD_TYPE,
                                      self.runcls._CHILD_TYPE)

    @check_input
    def preprocess(self, user_graph: UserGraphRoot):
        return self.preprocessor.process(user_graph)

    @check_input
    def compile(self, inter_graph: InterGraphRoot) -> RunGraphRoot:
        """Compile an inter graph to a run graph.

        During compilation, all implicit routines like propagation routines
        are constructed. Returns the compiled graph, an instance of
        RunGraphRoot.
        """
        rungraph = RunGraphRoot({})
        stagecompiler = self.compiler

        # run_stages = [None] * inter_graph.num_stages
        rungraph.virtual_stages = []
        for i, stage in enumerate(inter_graph.children):
            rungraph.virtual_stages += [stagecompiler.compile(stage, rungraph)]

        rungraph.children = rungraph.virtual_stages
        del rungraph.virtual_stages
        self.runspec.processor.set_type(rungraph, True)
        self.runspec.processor.set_options(rungraph, True)
        self.runspec.processor.verify(rungraph, True)

        return rungraph

    @check_input
    def build(self, user_graph: UserGraphRoot) -> RunGraphRoot:
        """Preprocess, compile, verify and return."""
        if not isinstance(user_graph, UserGraphRoot):
            raise TypeError

        intergraph = self.preprocess(user_graph)
        rungraph = self.compile(intergraph)
        self.runspec.processor.verify(rungraph, True)

        return rungraph


class Preprocessor(GraphProcessor):

    def __init__(self, predefined_tasks: dict[str, dict]):
        self._predef_tasks = predefined_tasks
        self._taskresolver = TaskResolver(self._predef_tasks)
        self._userprocessor = NodeConfigurationProcessor(self.userspec)

    @check_input
    def process(self, user_graph: UserGraphRoot) -> InterGraphRoot:
        """Preprocess the user graph.
        """
        self._userprocessor.set_type(user_graph, graph=True)
        self._taskresolver.resolve(user_graph, graph=True)
        self._userprocessor.set_options(user_graph, graph=True)
        self._userprocessor.verify(user_graph, graph=True)

        intergraph = self.intercls(
            {
                "start_time": user_graph.options["start_time"]
                }
            )

        self._translate(user_graph, intergraph)
        self.interspec.processor.process(intergraph, True)

        return intergraph

    def _translate_routines(self, userstage: UserGraphNode,
                            interstage: InterGraphNode):
        assert interstage.num_children == 0

        def routines_gen():
            for uroutine in userstage.children:
                assert uroutine.rank_name() == "Routine"
                ispec = self.interspec.ranks["Routine"].types[uroutine.type]
                opts = {
                    k: uroutine.options[k] for k in ispec.options.keys()
                }

                yield InterGraphNode(interstage, opts)

        interstage.children = iter(routines_gen())

    def _translate(self, usergraph: UserGraphRoot,
                   intergraph: InterGraphRoot):
        for stage in usergraph.children:
            interopts = self._get_inter_opts_stage(stage)
            intergraph.add_children_from_options(interopts)

        for ustage, istage in zip(usergraph.stages, intergraph.stages):
            assert istage.num_children == 0
            self._translate_routines(ustage, istage)

    def _get_inter_opts_stage(self, stage: UserGraphNode) -> dict:
        if stage.type == "regular":
            return {"num_routines": stage.num_children}

        useropts = stage.options.local
        interopts = {
            "propagation_time": useropts["propagation_time"],
            "monitoring": useropts["monitoring"]
            }

        if useropts["monitoring_numsteps"] is not None:
            numsteps = useropts["monitoring_numsteps"]
        elif useropts["monitoring_stepsize"] is not None:
            times = np.arange(0.0, interopts["propagation_time"],
                              step=useropts["monitoring_stepsize"])
            numsteps = len(times)

        interopts.update(
            {"monitoring_numsteps": numsteps})

        interopts.update(
            {"num_routines": stage.num_children}
        )

        return interopts
