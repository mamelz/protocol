from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..essentials import System

from .classes import (
    EvolutionRegularRoutine,
    MonitoringRoutine,
    PropagationRoutine,
    RegularRoutine,
    Routine
)

from ..builder.graph_classes.run import RunGraphRoot


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
