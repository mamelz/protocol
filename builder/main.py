import functools
import typing

from . import InterGraphRoot, RunGraphRoot, UserGraphRoot
from .base import GraphProcessor
from .intertorun.main import Inter2RunProcessor
from .routine_classes import (
    EvolutionRegularRoutine,
    MonitoringRoutine,
    PropagationRoutine,
    RegularRoutine,
    Routine
)
from .usertointer.main import User2InterProcessor
from ..essentials import System


def check_input(method):
    input_type = tuple(typing.get_type_hints(method).values())[0]

    @functools.wraps(method)
    def wrapped(obj: GraphProcessor, input_graph, **kwargs):
        if not isinstance(input_graph, input_type):
            raise TypeError
        return method(obj, input_graph, **kwargs)
    return wrapped


class GraphBuilder(GraphProcessor):

    input_type = UserGraphRoot
    output_type = RunGraphRoot

    def __init__(self, predefined_tasks: dict[str, dict] = {}):
        self._predef_tasks = predefined_tasks
        self.u2i = User2InterProcessor(self._predef_tasks)
        self.i2r = Inter2RunProcessor()

    @check_input
    def __call__(self, user_graph: UserGraphRoot) -> RunGraphRoot:
        """Preprocess, compile, verify and return."""
        if not isinstance(user_graph, UserGraphRoot):
            raise TypeError

        rungraph = self.i2r(self.u2i(user_graph))
        self.output_type._GRAPH_SPEC.processor.verify(rungraph, True)
        return rungraph

    @check_input
    def user2inter(self, user_graph: UserGraphRoot) -> InterGraphRoot:
        return self.u2i(user_graph)

    @check_input
    def inter2run(self, inter_graph: InterGraphRoot) -> RunGraphRoot:
        return self.i2r(inter_graph)

    def generate_routines(self, system: System, run_graph: RunGraphRoot):
        gen = RoutineGenerator()
        return gen.make(system, run_graph)


class RoutineGenerator:

    def __init__(self):
        pass

    def make(self, system: System, rungraph: RunGraphRoot) -> tuple[Routine]:
        routines = [None]*rungraph.num_routines
        for i, routnode in enumerate(rungraph.routines):
            stage_idx = routnode.parent.ID.local + 1
            if routnode.type == "propagation":
                routine = PropagationRoutine(routnode.options.local)
                routine.stage_idx = stage_idx
                routines[i] = routine
            elif routnode.type == "evolution":
                routine = EvolutionRegularRoutine(routnode.options.local,
                                                  system)
                routine.stage_idx = stage_idx
                routines[i] = routine
            elif routnode.type == "monitoring":
                routine = MonitoringRoutine(routnode.options.local,
                                            system)
                routine.stage_idx = stage_idx
                routines[i] = routine
            elif routnode.type == "regular":
                routine = RegularRoutine(routnode.options.local,
                                         system)
                routine.stage_idx = stage_idx
                routines[i] = routine

        return tuple(routines)
