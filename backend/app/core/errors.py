class WorkflowError(Exception):
    def __init__(self, message: str, step: str = "workflow") -> None:
        super().__init__(message)
        self.message = message
        self.step = step
