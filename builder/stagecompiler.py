import itertools

import numpy as np

from . import errors
from .graph_classes.run import RunGraphNode, RunGraphRoot
from .graph_classes.inter import InterGraphNode
from ..graph.base import GraphNodeMeta
from ..graph.errors import NodeConfigurationError
from ..graph.spec import NodeConfigurationProcessor


class StageCompiler:
    """Constructs RunGraph stages from UserGraph stages."""

    def __init__(self, in_type: GraphNodeMeta, out_type: GraphNodeMeta):
        self._in_type = in_type
        self._out_type = out_type
        self._out_rout_spec = self._out_type._GRAPH_SPEC.ranks["Routine"]
        out_stg_spec = self._out_type._GRAPH_SPEC.ranks["Stage"]
        self._out_rout_keys = {
            k: v.options.keys() for k, v in self._out_rout_spec.types.items()
        }
        self._out_stg_keys = {k: v for k, v in out_stg_spec.types.items()}
        self._out_config_proc = NodeConfigurationProcessor(
            self._out_type._GRAPH_SPEC)

    def compile(self, stage_node: InterGraphNode,
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

    def _compile_regular(self, interstage: InterGraphNode,
                         parent: RunGraphRoot) -> RunGraphNode:
        routine_opts = (rout.options.local for rout in interstage.children)
        stage_opts = {
            "routines": [
                {k: rout_opdict[k] for k in self._out_rout_keys["regular"]}
                for rout_opdict in routine_opts
                ],
            "type": "regular"
            }
        out_stage = RunGraphNode(parent, stage_opts, rank=1)
        parent.add_children((out_stage,))
        try:
            self._out_config_proc.verify(out_stage)
        except NodeConfigurationError:
            raise errors.StageCompilerError("Something went wrong.")

        return out_stage

    def _compile_evolution(self, interstage: InterGraphNode,
                           parent: RunGraphRoot) -> RunGraphNode:
        in_stg_opts = interstage.options.local
        start_time = interstage.parent.options["start_time"]

        if len(parent.virtual_stages) > 0:
            start_time += parent.virtual_stages[
                -1].options.local["propagation_time"]

        proptime = in_stg_opts["propagation_time"]
        stop_time = start_time + proptime
        numsteps = in_stg_opts["monitoring_numsteps"]

        monroutopts = in_stg_opts["monitoring"]
        for opt in monroutopts:
            if "store_token" not in opt:
                opt["store_token"] = opt["routine_name"]
        out_stage: RunGraphNode = self._out_type(
            parent,
            {
                "propagation_time": proptime,
                "type": "evolution"
                },
            rank=1)
        parent.add_children((out_stage,))

        usrrouts = interstage.children
        usr_timetable: dict[float, tuple[InterGraphNode]] = {}
        for rout in usrrouts:
            opts = rout.options.local.copy()
            opts.update({"tag": "USER"})
            if opts["store_token"] == "":
                opts["store_token"] = opts["routine_name"]
            try:
                time = rout.options["time"]
            except KeyError:
                time = start_time + rout.options["localtime"]

            opts["time"] = time
            outrout_opts = {
                k: opts[k] for k in self._out_rout_keys["evolution"]}
            outrout_opts.update({"type": "evolution"})

            out_rout = self._out_type(out_stage, outrout_opts, rank=2)
            if time not in usr_timetable:
                usr_timetable[time] = (out_rout,)
            else:
                usr_timetable[time] += (out_rout,)

        usr_times = np.array(tuple(usr_timetable.keys()))

        mon_times = np.linspace(start_time,
                                stop_time,
                                numsteps,
                                endpoint=True)

        mon_timetable: dict[float, tuple[InterGraphNode]] = {}
        for time in mon_times:
            tdict = {
                "tag": "MONITORING",
                "time": time,
                "type": "monitoring"
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

#        save_last_opts = {
#            "routine_name": "_return_state",
#            "time": stop_time,
#            "store_token": "State",
#            "tag": "AUTOMATIC",
#            "type": "evolution"
#        }


#        complete_timetable[rout_times[-1]] +=

        complete_routines = itertools.chain.from_iterable(
            complete_timetable.values())
        out_stage.children = tuple(complete_routines)
        out_stage.options.local.update(
            {"num_routines": out_stage.num_routines})

        return out_stage