from .user_spec import USER_GRAPH_CONFIG_DICT
from ...graph.base import GraphNode, GraphNodeMeta, GraphRoot, GraphRootMeta
from ...graph.spec import GraphSpecification


class UserGraphNode(GraphNode, metaclass=GraphNodeMeta,
                    graph_spec=GraphSpecification(USER_GRAPH_CONFIG_DICT)):

    def _post_init(self):
        if not self.isleaf:
            child_rankname = f"{self.rank_name(self.rank + 1).lower()}s"
            try:
                ch_opts = self.options.local[child_rankname]
                ch_gen = (self.make_child(opt) for opt in ch_opts)
                self.set_children(ch_gen, quiet=True)
            except KeyError:
                pass


class UserGraphRoot(GraphRoot, UserGraphNode, metaclass=GraphRootMeta):

    @property
    def stages(self):
        return self.children

    @property
    def start_time(self) -> float:
        return self.options["start_time"]

    @start_time.setter
    def start_time(self, new: float):
        self.options["start_time"] = new
