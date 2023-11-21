class GraphError(Exception):
    message = "An error occured while handling the graph."

    def __init__(self, message=None):
        if message is not None:
            self.message = message
        super().__init__(self.message)


class NodeRankInvalidError(GraphError):
    message = "Node rank is invalid."


class NodeTypeInvalidError(GraphError):
    message = "Node type is invalid."


class NodeOptionsError(GraphError):
    message = "Node options are invalid."
