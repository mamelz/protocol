class PreprocessorError(Exception):
    message = "Something went wrong during preprocessing."

    def __init__(self, message=None):
        if message is not None:
            self.message = message
        super().__init__(self.message)


class NodeTypeNotFoundError(PreprocessorError):
    message = "Node type could not be determined."


class NodeOptionsError(PreprocessorError):
    message = "Node options invalid."


class StageProcessingError(PreprocessorError):
    message = "Error during stage preprocessing."
