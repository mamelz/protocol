import numpy as np

from ..graph_classes.run import RunGraphNode, RunGraphRoot
from ..graph_classes.inter import InterGraphNode


class StageCompiler:
    """Constructs RunGraph stages from InterGraph stages."""

    class StageCompilerError(Exception):
        pass

    input_type = InterGraphNode
    output_type = RunGraphNode

    def __init__(self):
        self._out_rout_spec = self.output_type._GRAPH_SPEC.ranks["Routine"]
        out_stg_spec = self.output_type._GRAPH_SPEC.ranks["Stage"]
        self._out_rout_keys = {
            k: v.options.keys() for k, v in self._out_rout_spec.types.items()
        }
        self._out_stg_keys = {k: v for k, v in out_stg_spec.types.items()}
        self._out_config_proc = self.output_type._GRAPH_SPEC.processor

    def compile(self, stage_node: InterGraphNode,
                parent: RunGraphRoot) -> RunGraphNode:
        if stage_node.rank_name() != "Stage":
            raise self.StageCompilerError(
                "Input node must be of rank 'Stage'.")

        if not isinstance(stage_node, self.input_type):
            raise self.StageCompilerError(
                f"Input stage must be instance of {self.input_type},"
                f" got {type(stage_node)}")

        if stage_node.type == "regular":
            return self._compile_regular(stage_node, parent)
        elif stage_node.type == "evolution":
            return self._compile_evolution(stage_node, parent)
        else:
            raise self.StageCompilerError(
                f"Unknown stage type {stage_node.type}")

    def _compile_regular(self, interstage: InterGraphNode,
                         parent: RunGraphRoot) -> RunGraphNode:
        routine_opts = (rout.options.local for rout in interstage.children)
        stage_opts = {
            "type": "regular"
            }
        out_stage = RunGraphNode(parent, stage_opts, rank=1)
        out_stage.set_children_from_options(routine_opts, quiet=True)
        parent.add_children((out_stage,))

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
        out_stage: RunGraphNode = self.output_type(
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

            out_rout_kwargs = {
                "parent": out_stage,
                "options": outrout_opts,
                "rank": 2
            }

            if time not in usr_timetable:
                usr_timetable[time] = [out_rout_kwargs]
            else:
                usr_timetable[time] += [out_rout_kwargs]

        usr_times = np.array(tuple(usr_timetable.keys()))
        mon_times = np.linspace(start_time,
                                stop_time,
                                numsteps,
                                endpoint=True)

        mon_timetable: dict[float, tuple[InterGraphNode]] = {}
        tdict = {
            "tag": "MONITORING",
            "type": "monitoring"
        }
        for time in mon_times:
            tdict.update({"time": time})
            mon_rout_kwargs = []
            for opt in monroutopts:
                mon_rout_kwargs += [{
                    "parent": out_stage,
                    "options": {**tdict, **opt},
                    "rank": 2
                }]

            mon_timetable[time] = mon_rout_kwargs

        rout_times = np.unique(np.concatenate([usr_times, mon_times]))
        proptimes = np.diff(rout_times)
        prop_timetable = {}
        for time, step in zip(rout_times, proptimes):
            opt = {
                "type": "propagation",
                "time": time,
                "step": step
            }
            prop_timetable[time] = {
                "parent": out_stage,
                "options": opt,
                "rank": 2,
            }

        complete_timetable = []
        for time in rout_times:
            try:
                complete_timetable.extend(mon_timetable[time])
            except KeyError:
                pass

            try:
                complete_timetable.extend(usr_timetable[time])
            except KeyError:
                pass

            try:
                complete_timetable.append(prop_timetable[time])
            except KeyError:
                pass

        stage_id_tup = out_stage.ID.tuple

        def stage_routines_gen():
            for i, kwargs in enumerate(complete_timetable):
                rout_id = tuple((*stage_id_tup, i))
                yield self.output_type(**kwargs, ID=rout_id)

        out_stage.children = tuple((stage_routines_gen()))
        out_stage.options.update(
            {"num_routines": out_stage.num_routines})

        return out_stage
