from numpy import arange

from .. import UserGraphNode, UserGraphRoot, InterGraphNode, InterGraphRoot


class RoutineTranslator:

    def init(self):
        pass

    def __call__(self, usergraph: UserGraphRoot, intergraph: InterGraphRoot):
        def istage_gen():
            time = usergraph.options["start_time"]
            for ustage in usergraph.children:
                istageopts = self._get_inter_opts_stage(ustage)
                if ustage.type == "evolution":
                    istageopts["start_time"] = time
                    time += ustage.options["propagation_time"]

                yield InterGraphNode(intergraph, istageopts)
                # iroutopts = (r.options.local for r in ustage.children)
                # istage.set_children_from_options(iroutopts)

        intergraph.add_children(istage_gen())

        for ustage, istage in zip(usergraph.stages, intergraph.stages):
            assert istage.num_children == 0
            self._translate_routines(ustage, istage)

    def _translate_routines(self, userstage: UserGraphNode,
                            interstage: InterGraphNode):
        assert interstage.num_children == 0
        if userstage.type == "regular":
            def routines_gen():
                for uroutine in userstage.children:
                    assert uroutine.rank_name() == "Routine"
                    ispec = interstage._GRAPH_SPEC.ranks[
                        "Routine"].types[uroutine.type]
                    opts = {
                        k: uroutine.options[k] for k in ispec.options.keys()
                    }

                yield InterGraphNode(interstage, opts)

            interstage.children = iter(routines_gen())
            return

        stage_start = interstage.options["start_time"]
        irout_opts = tuple(ch.options.local for ch in userstage.children)
        for opt in irout_opts:
            try:
                opt["time"] = opt["systemtime"]
                del opt["systemtime"]
            except KeyError:
                opt["time"] = opt["stagetime"] + stage_start
                del opt["stagetime"]

        def routines_gen():
            for opt in irout_opts:
                yield InterGraphNode(interstage, opt)

        interstage.children = routines_gen()

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
            times = arange(0.0, interopts["propagation_time"],
                           step=useropts["monitoring_stepsize"])
            numsteps = len(times)

        interopts.update(
            {"monitoring_numsteps": numsteps})

        interopts.update(
            {"num_routines": stage.num_children}
        )

        return interopts
