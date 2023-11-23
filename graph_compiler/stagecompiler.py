import itertools

import numpy as np

from . import errors
from .run_graph import RunGraphNode, RunGraphRoot
from .user_graph import UserGraphNode
from ..graph.base import GraphNodeMeta
from ..graph.errors import NodeConfigurationError
from ..graph.spec import NodeConfigurationProcessor


class StageCompiler:
    """Constructs RunGraph stages from UserGraph stages."""

    def __init__(self, in_type: GraphNodeMeta, out_type: GraphNodeMeta):
        self._in_type = in_type
        self._out_type = out_type
        out_rout_spec = self._out_type._GRAPH_SPEC.ranks["Routine"]
        out_stg_spec = self._out_type._GRAPH_SPEC.ranks["Stage"]
        self._out_rout_keys = {
            k: v.options.keys() for k, v in out_rout_spec.types.items()
        }
        self._out_stg_keys = {k: v for k, v in out_stg_spec.types.items()}
        self._out_config_proc = NodeConfigurationProcessor(
            self._out_type._GRAPH_SPEC)

    def compile(self, stage_node: UserGraphNode,
                parent: RunGraphRoot) -> RunGraphNode:
        if stage_node.rank_name() != "Stage":
            raise errors.StageCompilerError(
                "Input node must be of rank 'Stage'.")

        if not isinstance(stage_node, self._in_type):
            raise errors.StageCompilerError(
                f"Input stage must be instance of {self._in_type},"
                f" got {type(stage_node)}")

        if stage_node.type == "regular":
            return self._compile_regular(stage_node, parent)
        elif stage_node.type == "evolution":
            return self._compile_evolution(stage_node, parent)
        else:
            raise errors.StageCompilerError(
                f"Unknown stage type {stage_node.type}")

    def _compile_regular(self, stage_node: UserGraphNode,
                         parent: RunGraphRoot) -> RunGraphNode:
        routine_opts = (rout.options.local for rout in stage_node.children)
        stage_opts = {
            "routines": [
                {k: rout_opdict[k] for k in self._out_rout_keys["regular"]}
                for rout_opdict in routine_opts
                ],
            # "type": "regular"
            }
        out_stage = RunGraphNode(parent, stage_opts, rank=1)
        parent.add_children((out_stage,))
        try:
            self._out_config_proc.verify(out_stage)
        except NodeConfigurationError:
            raise errors.StageCompilerError("Something went wrong.")

        return out_stage

    def _compile_evolution(self, stage_node: UserGraphNode,
                           parent: RunGraphRoot) -> RunGraphNode:
        in_stg_opts = stage_node.options.local
#        out_stg_opts = {
#            k: in_stg_opts[k] for k in self._out_stg_keys["evolution"]
#            }
        try:
            start_time = stage_node.parent.options["start_time"]
        except KeyError:
            start_time = 0.0

        proptime = in_stg_opts["propagation_time"]
        stop_time = start_time + proptime
        stepsize = in_stg_opts["monitoring_stepsize"]
        numsteps = in_stg_opts["monitoring_numsteps"]
        monroutopts = in_stg_opts["monitoring"]
        usrrouts = stage_node.children
        out_stage = self._out_type(
            parent,
            {
                "propagation_time": proptime,
                "type": "evolution"
                },
            rank=1)
        parent.add_children((out_stage,))

        usr_timetable: dict[float, tuple[UserGraphNode]] = {}
        for rout in usrrouts:
            opts = rout.options.local.copy()
            opts.update({"tag": "USER"})
            try:
                time = rout.options["time"]
            except KeyError:
                time = start_time + rout.options["localtime"]

            opts["time"] = time
            outrout_opts = {
                k: opts[k] for k in self._out_rout_keys["evolution"]}

            out_rout = self._out_type(out_stage, outrout_opts, rank=2)
            if time not in usr_timetable:
                usr_timetable[time] = (out_rout,)
            else:
                usr_timetable[time] += (out_rout,)

        usr_times = np.array(tuple(usr_timetable.keys()))

        if stepsize is None and numsteps is None:
            mon_times = ()
        elif stepsize is not None:
            mon_times = np.arange(start_time, stop_time, step=stepsize)
            mon_times = np.concatenate([mon_times, np.array([stop_time])])
        else:
            mon_times = np.linspace(start_time,
                                    stop_time,
                                    numsteps,
                                    endpoint=True)

        mon_timetable: dict[float, tuple[UserGraphNode]] = {}
        for time in mon_times:
            tdict = {
                "tag": "MONITORING",
                "time": time,
                "type": "evolution"
                }
            mon_routs = ()
            for opt in monroutopts:
                mon_routs += (
                    self._out_type(out_stage, {**tdict, **opt}, rank=2),)
            mon_timetable[time] = mon_routs

        rout_times = np.unique(np.concatenate([usr_times, mon_times]))
        proptimes = np.diff(rout_times)
        prop_timetable = {}
        for time, step in zip(rout_times, proptimes):
            opt = {
                "type": "propagation",
                "time": time,
                "step": step
            }
            prop_timetable[time] = self._out_type(out_stage, opt, rank=2)

        complete_timetable: dict[float, dict] = {}
        for time in rout_times:
            try:
                complete_timetable[time] = mon_timetable[time]
            except KeyError:
                complete_timetable[time] = ()

            try:
                complete_timetable[time] += usr_timetable[time]
            except KeyError:
                pass

            try:
                complete_timetable[time] += (prop_timetable[time],)
            except KeyError:
                pass

#        complete_timetable = {
#            t: (*mon_timetable[t], *usr_timetable[t]) for t in rout_times
#        }

        for t, rout in prop_timetable.items():
            try:
                complete_timetable[t] += (rout,)
            except KeyError:
                complete_timetable[t] = (rout,)

        complete_routines = itertools.chain.from_iterable(
            complete_timetable.values())
        out_stage.children = tuple(complete_routines)
        out_stage.options.local.update(
            {"num_routines": out_stage.num_routines})

        return out_stage
