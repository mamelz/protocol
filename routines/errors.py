class RoutineInitializationError(Exception):
    message = "Error during initialization of routine."

    def __init__(self, message=None):
        if message is not None:
            self.message = message
        super().__init__()
