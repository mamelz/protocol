"""Module for the main class 'Protocol'."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import h5py

import textwrap
from typing import Any, Union

from ..graph import GraphNodeMeta, GraphNodeNONE
from ..parser_ import ProtocolConfiguration
from ..routines import RoutineABC, PropagationRoutine
from ..settings import SETTINGS
from ..utils import FrozenDict

from .preprocessor import ProtocolPreprocessor
from .protocolgraph import ProtocolGraph


class Protocol:
    """Main object containing all necessary information for performing
    the calculations on a quantum state.
    """
    _RANK_NAMES = ("Schedule", "Stage", "Task", "Routine")

    def __init__(self, *, options: dict = None, sys_params: dict,
                 output_file: h5py.File):
        """If 'options' is None, initializes empty protocol.
        Schedules and global options can be added later on.
        """
        self._options = options if options is not None else {}
        self.sys_params = sys_params
        self.output_file = output_file
        self._graphs: tuple[ProtocolGraph] = ()
        self._labeled_graphs = {}
# TODO
#        if options is not None:
#            self._graphs =\
#                tuple(self.addGraph(schedule_options) for schedule_options
#                      in self._options["schedules"])
        self.live_tracking = ()
        self.RESULTS: dict[Union[float, str], dict[float, dict[str, Any]]] = {}
        self.initialized = False
        self.finalized = False
        self.protocol_ready = False

    @property
    def global_options(self) -> dict:
        res = {}
        for key in self._options:
            if key != "schedules":
                res[key] = self._options[key]
            if key == "global_schedule_options":
                res["graph"] = self._options[key]
                del res["global_schedule_options"]
        res["sys_params"] = self.sys_params
        return res

    @property
    def schedule_options(self) -> list[dict]:
        # assert len(self._options["schedules"]) == 1
        return self._options["schedules"]

    def graph(self, identifier: Union[float, str]) -> ProtocolGraph:
        """Returns graph, either with specified number or specified label."""
        if isinstance(identifier, float):
            return self._graphs[identifier]
        if isinstance(identifier, str):
            return self._labeled_graphs[identifier]

    def setLiveTracking(self, name_tuple: tuple[str]):
        """Specifies functions, the output of which shall be printed
        during calculation.
        """
        self.live_tracking = name_tuple

    def addGraph(self, graph_options, *pgraph_init_args, **pgraph_init_kwargs):
        """Adds a ProtocolGraph to the protocol."""
        schedule_class = GraphNodeMeta.fromRank(0, self._RANK_NAMES)
        graph = ProtocolGraph(self, schedule_class(GraphNodeNONE(),
                                                   graph_options),
                              *pgraph_init_args, **pgraph_init_kwargs)
        self._graphs += (graph,)
        if graph.label is not None:
            self._labeled_graphs[graph.label] = graph
        return

    def setGlobalOptions(self, config: ProtocolConfiguration):
        if isinstance(config, ProtocolConfiguration):
            self._options.update(config.global_options)
            return
        if not isinstance(config, dict):
            raise ValueError
        self._options.update(config)
        return

    def getOptions(self, key):
        try:
            return self.global_options[key]
        except KeyError:
            raise KeyError(f"Option '{key}' not found.")

    def _preprocessor(self, _start_time=None):
        return ProtocolPreprocessor(self, _start_time)

    def INITIALIZE(self, _start_time=None):
        """Initialize protocol, optionally forcing a start time for all
        graphs.
        """
        if not SETTINGS.check():
            raise ValueError("Library settings not complete.")
        if len(self._graphs) == 0:
            raise ValueError("Protocol does not contain any graphs.")

        self._preprocessor(_start_time=_start_time).run()
        self._options["io_options"]["ofile"] = self.output_file
        self.initialized = True

    def FINALIZE(self):
        if not self.initialized:
            raise ValueError("Protocol must be initialized, first.")

        for graph in self._graphs:
            graph.makeRoutines()
        for routine in graph.ROUTINES:
            if routine.store_token in self.live_tracking:
                routine.enableLiveTracking()
        self.finalized = True

    def PERFORM(self, n):
        """Performs schedule i."""
        if not self.finalized:
            raise ValueError("Protocol must be finalized, first.")

        graph: ProtocolGraph = self._graphs[n]
        num_stages = len(graph.getRank(1))
        assert isinstance(graph, ProtocolGraph)
        for i, routine in enumerate(graph.ROUTINES):
            assert isinstance(routine, RoutineABC)
            stage_idx = routine._node.parent_of_rank(1).ID.local + 1

            if isinstance(routine, PropagationRoutine):
                prop_string = f"PROPAGATE BY {routine.timestep:3.4f}"
                name_string = (f">>>>>>>>>> {prop_string:^29} >>>>>>>>>>")
            else:
                name_string = (f"{routine._TYPE:>10}"
                               f" {routine.store_token:<20}")
            text_prefix = " | ".join([
                f"SCHEDULE {n + 1:>2}:",
                f"STAGE {stage_idx:>3}/{num_stages:<3}",
                f"ROUTINE {i + 1:>{len(str(len(graph.ROUTINES)))}}"  # no comma
                f"/{len(graph.ROUTINES)}",
                f"TIME {f'{graph.tstate.time:.4f}':>10}",
                f"{name_string}"])
            textwrapper = textwrap.TextWrapper(width=250,
                                               initial_indent=text_prefix)
            output = routine(graph.tstate)
            if routine.live_tracking:
                output_text = textwrapper.fill(f": {output[1]}")
            else:
                output_text = text_prefix
            print(output_text)

            if output is None:
                continue

            if graph.tstate.time not in graph.RESULTS:
                graph.RESULTS[graph.tstate.time] = {output[0]: [output[1]]}
            else:
                if output[0] not in graph.RESULTS[graph.tstate.time].keys():
                    graph.RESULTS[graph.tstate.time][output[0]] = [output[1]]
                else:
                    graph.RESULTS[graph.tstate.time][output[0]] += [output[1]]

        if graph.label is not None:
            self.RESULTS[graph.label] = graph.RESULTS
            self.RESULTS[i] = graph.RESULTS
        self.RESULTS = FrozenDict(self.RESULTS)
