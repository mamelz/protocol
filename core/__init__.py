"""Module for the main class 'Protocol'."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from numpy import ndarray

import sys
import textwrap
from typing import Any, Sequence, Union

from ..parser_ import ProtocolConfiguration
from ..routines import RoutineABC, PropagationRoutine
from ..settings import SETTINGS
from ..utils import FrozenDict

from .preprocessor import ProtocolPreprocessor
from .protocolgraph import ProtocolGraph


class Protocol:
    """
    Main object containing all necessary information for performing
    the calculations on a quantum state.
    """
    _RANK_NAMES = ("Schedule", "Stage", "Task", "Routine")

    def __init__(self, configuration: ProtocolConfiguration = None):
        """
        If 'configuration' is None, initializes empty protocol.
        Schedules and global options can be added later on.
        """
        self._config = configuration
        self._graphs: tuple[ProtocolGraph] = ()
        self._label_map: dict[str, int] = {}
        if self._config is not None:
            for options in self._config.schedules:
                self._graphs += (ProtocolGraph(self, options),)
        self.live_tracking = ()
        self.results: dict[Union[float, str], dict[float, dict[str, Any]]] = {}
        self._initialized = False
        self._finalized = False
        self._graphs_performed: tuple[float] = ()

    @property
    def global_options(self) -> dict:
        res = {}
        for key in self._config:
            if key != "schedules":
                res[key] = self._config[key]
#            if key == "global_schedule_options":
#                res["graph"] = self._options[key]
#                del res["global_schedule_options"]
        return res

    @property
    def num_schedules(self):
        """The number of schedules currently initialized."""
        return len(self._graphs)

    @property
    def schedule_options(self) -> list[dict]:
        # assert len(self._options["schedules"]) == 1
        return self._config["schedules"]

    def _preprocessor(self, _start_time=None):
        return ProtocolPreprocessor(self, _start_time)

    def _perform_n(self, n: int):
        if isinstance(self.results, FrozenDict):
            self.results = dict(self.results)

        graph: ProtocolGraph = self._graphs[n]
        num_stages = len(graph.get_rank(1))
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

        if graph.label is not None:
            self.results[graph.label] = graph.RESULTS
        self.results[n] = graph.RESULTS
        self.results = FrozenDict(self.results)
        self._graphs_performed += (n,)
        return

    def add_schedule(self, graph_options, **tstate_args):
        """
        Adds a schedule to the protocol, optionally setting the tstate aswell.
        """
        graph = ProtocolGraph(self, graph_options)
        if tstate_args is not None:
            graph.init_tstate(**tstate_args)
        self._graphs += (graph,)
        if graph.label is not None:
            if graph.label in self._label_map:
                raise ValueError(f"Graph label {graph.label} already exists.")
            self._label_map[graph.label] = len(self._graphs) - 1
        return

    def duplicate_schedule(self, id, **tstate_args):
        """
        Adds a schedule to the protocol, using the options of some schedule
        already contained in the protocol.
        """
        self.add_schedule(self.schedule(id).root._options, **tstate_args)
        return

    def finalize(self):
        if not self._initialized:
            raise ValueError("Protocol must be initialized, first.")

        for graph in self._graphs:
            graph.make_routines()
            for routine in graph.ROUTINES:
                if routine.store_token in self.live_tracking:
                    routine.enable_live_tracking()
        self._finalized = True

    def get_options(self, key):
        return self.global_options[key]

    def get_output(self, quantities: Sequence = (), graph_id=None)\
            -> dict[str, dict[str, dict[float, Any]]]:
        """
        Returns the time-resolved sequence of measurements of the
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
            key = self.schedule(identifier).label
            if key is None:
                key = identifier
            output_dict[key] = {}

        if graph_id is not None and (
                graph_id not in output_dict):
            assert len(output_dict.values()) == 0
            output_dict[graph_id] = output_dict.values()[0]

        if quantities == ():
            for graph_idt in output_dict.keys():
                output_dict[graph_idt] = self.schedule(graph_idt).RESULTS
        else:
            for graph_idt in output_dict.keys():
                for qname in quantities:
                    output_dict[graph_idt][qname] = self.schedule(
                        graph_idt).RESULTS[qname]
        return FrozenDict(output_dict)

    def initialize(self, _start_time=None):
        """
        Initialize protocol, optionally forcing a start time for all graphs.
        """
        if not SETTINGS.check():
            raise ValueError("Library settings not complete.")
        if len(self._graphs) == 0:
            raise ValueError("Protocol does not contain any graphs.")
        for i in range(len(self._graphs)):
            graph = self._graphs[i]
            id = f"'{graph.label}'" if graph.label is None else i
            if graph.tstate is None:
                raise ValueError(f"TState of schedule {id} not set.")

        self._preprocessor(_start_time=_start_time).run()
        self._initialized = True
        return

    def perform(self, n=None):
        """
        Performs schedule n. If no argument is passed, performs all schedules.
        """
        if not self._finalized:
            raise ValueError("Protocol must be finalized, first.")

        if n is None:
            for i in range(self.num_schedules):
                self._perform_n(i)
        else:
            self._perform_n(n)
        return

    def schedule(self, identifier: Union[int, str]) -> ProtocolGraph:
        """
        Returns schedule, either with specified number or specified label.
        """
        if isinstance(identifier, int):
            return self._graphs[identifier]
        if isinstance(identifier, str):
            return self._graphs[self._label_map[identifier]]
        raise TypeError("Invalid identifier type.")

    def set_global_options(self, config: dict):
        if not isinstance(config, dict):
            raise ValueError
        if "schedules" in config:
            raise ValueError("Global options cannot contain key 'schedules'.")
        self._config.update(config)
        return

    def set_live_tracking(self, names: Union[str, tuple[str]]):
        """
        Specifies functions, the output of which shall be printed during
        calculation.
        """
        if isinstance(names, str):
            names = (names,)
        self.live_tracking = names
        return

    def set_tstate(self, schedule_id: Union[int, str], state: ndarray,
                   propagator_factory, label=None):
        """
        Sets the time-dependent state of the specified schedule.
        The schedule can be specified by label or number.
        """
        schedule = self.schedule(schedule_id)
        schedule.init_tstate(state, propagator_factory, label)
        if schedule.label is not None:
            self._label_map[schedule.label] = self._graphs.index(schedule)
        return
