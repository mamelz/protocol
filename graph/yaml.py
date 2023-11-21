from .base import GraphNode, GraphNodeMeta, GraphRootMeta
from .config import GraphSpecification
from ..settings.yaml_graph_cfg import YAML_GRAPH_CONFIG_DICT


yaml_spec = GraphSpecification(YAML_GRAPH_CONFIG_DICT)


class YAMLGraphNode(GraphNode, metaclass=GraphNodeMeta, graph_spec=yaml_spec):
    pass


class YAMLGraphRoot(YAMLGraphNode, metaclass=GraphRootMeta):
    pass
