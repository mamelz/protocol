"""Module for the main class 'Protocol'."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import h5py

import sys
import textwrap
from typing import Any, Sequence, Union

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
        self._label_map: dict[str, int] = {}
# TODO
#        if options is not None:
#            self._graphs =\
#                tuple(self.addGraph(schedule_options) for schedule_options
#                      in self._options["schedules"])
        self.live_tracking = ()
        self.RESULTS: dict[Union[float, str], dict[float, dict[str, Any]]] = {}
        self._initialized = False
        self._finalized = False
        self._graphs_performed: tuple[float] = ()

    @property
    def num_graphs(self):
        return len(self._graphs)

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

    def _preprocessor(self, _start_time=None):
        return ProtocolPreprocessor(self, _start_time)

    def _perform_n(self, n: int):
        if isinstance(self.RESULTS, FrozenDict):
            self.RESULTS = dict(self.RESULTS)

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
            schedule_name = n + 1 if graph.label is None else (
                f"'{graph.label}'")
            text_prefix = " | ".join([
                f"SCHEDULE {schedule_name:>6}:",
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
            sys.stdout.flush()

            if output is None:
                continue

            if output[0] not in graph.RESULTS:
                graph.RESULTS[output[0]] = {graph.tstate.time: output[1]}
            else:
                graph.RESULTS[output[0]].update({graph.tstate.time: output[1]})


#            if graph.tstate.time not in graph.RESULTS:
#                graph.RESULTS[graph.tstate.time] = {output[0]: [output[1]]}
#            else:
#                if output[0] not in graph.RESULTS[graph.tstate.time].keys():
#                    graph.RESULTS[graph.tstate.time][output[0]] = [output[1]]
#                else:
#                    graph.RESULTS[graph.tstate.time][output[0]] += [output[1]]

        if graph.label is not None:
            self.RESULTS[graph.label] = graph.RESULTS
        self.RESULTS[n] = graph.RESULTS
        self.RESULTS = FrozenDict(self.RESULTS)
        self._graphs_performed += (n,)
        return

    def graph(self, identifier: Union[int, str]) -> ProtocolGraph:
        """Returns graph, either with specified number or specified label."""
        if isinstance(identifier, int):
            return self._graphs[identifier]
        if isinstance(identifier, str):
            return self._graphs[self._label_map[identifier]]
        raise TypeError("Invalid identifier type.")

    def setLiveTracking(self, names: Union[str, tuple[str]]):
        """Specifies functions, the output of which shall be printed
        during calculation.
        """
        if isinstance(names, str):
            names = (names,)
        self.live_tracking = names

    def addGraph(self, graph_options, *pgraph_init_args, **pgraph_init_kwargs):
        """Adds a ProtocolGraph to the protocol."""
        schedule_class = GraphNodeMeta.fromRank(0, self._RANK_NAMES)
        graph = ProtocolGraph(self, schedule_class(GraphNodeNONE(),
                                                   graph_options),
                              *pgraph_init_args, **pgraph_init_kwargs)
        self._graphs += (graph,)
        if graph.label is not None:
            if graph.label in self._label_map:
                raise ValueError(f"Graph label {graph.label} already exists.")
            self._label_map[graph.label] = len(self._graphs) - 1
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

    def getOutput(self, quantities: Sequence = (), graph_id=None)\
            -> dict[str, dict[str, dict[float, Any]]]:
        """Returns the time-resolved sequence of measurements of the
        specified quantities. If no graph is specified, returns a dictionary
        with outputs of all graphs, using the graph number or (if available)
        graph labels as keys.
        If no measurement name is specified, the dictionary contains all
        available results.
        """
        if isinstance(quantities, str):
            quantities = (quantities,)

        output_dict = {}
        if graph_id is None:
            graphs = self._graphs_performed
        else:
            graphs = (graph_id,)

        for identifier in graphs:
            key = self.graph(identifier).label
            if key is None:
                key = identifier
            output_dict[key] = {}

        if graph_id is not None and (
                graph_id not in output_dict):
            assert len(output_dict.values()) == 0
            output_dict[graph_id] = output_dict.values()[0]

        if quantities == ():
            for graph_idt in output_dict.keys():
                output_dict[graph_idt] = self.graph(graph_idt).RESULTS
        else:
            for graph_idt in output_dict.keys():
                for qname in quantities:
                    output_dict[graph_idt][qname] = self.graph(
                        graph_idt).RESULTS[qname]
        return FrozenDict(output_dict)

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
        self._initialized = True

    def FINALIZE(self):
        if not self._initialized:
            raise ValueError("Protocol must be initialized, first.")

        for graph in self._graphs:
            graph.makeRoutines()
            for routine in graph.ROUTINES:
                if routine.store_token in self.live_tracking:
                    routine.enableLiveTracking()
        self._finalized = True

    def PERFORM(self, n=None):
        """Performs schedule n. If no argument is passed, performs
        all schedules.
        """
        if not self._finalized:
            raise ValueError("Protocol must be finalized, first.")

        if n is None:
            for i in range(self.num_graphs):
                self._perform_n(i)
        else:
            self._perform_n(n)
        return
