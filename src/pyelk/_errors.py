"""Public native validation and execution errors with JSON Pointer locations.

These categories describe the explicit Python host contract. They do not
rename every JavaScript/GWT error into a single compatibility error.
"""


class ValidationError(ValueError):
    """A stable category and JSON Pointer identifying invalid host input."""

    def __init__(self, code: str, path: str, message: str):
        self.code = code
        self.path = path
        self.message = message
        super().__init__(f"{code} at {path or '/'}: {message}")


class ModelValidationError(ValidationError):
    """Invalid graph data or a structural mutation that would break its index."""


class OptionValidationError(ValidationError):
    """Invalid option containers, aliases or supported values."""


class UnknownOptionError(OptionValidationError):
    """An option identifier absent from the fixed reference catalogue."""


class UnsupportedOptionError(OptionValidationError):
    """A reference option known by name but not parsed by this slice."""


class UnsupportedFeatureError(ValidationError):
    """An explicitly supplied capability outside this native host slice."""


class UnknownAlgorithmError(OptionValidationError):
    """An algorithm identifier absent from the fixed reference catalogue."""


class UnsupportedAlgorithmError(UnsupportedFeatureError):
    """A known algorithm unavailable in this instance's native registry."""


class UnsupportedWorkerError(UnsupportedFeatureError, NotImplementedError):
    """JavaScript worker construction is not a native host capability."""


class ResourceClosedError(UnsupportedFeatureError):
    """Work or metadata was requested after the instance closed."""


class ExecutionError(RuntimeError):
    """A scheduling or internal execution failure, distinct from bad input."""

    def __init__(self, code: str, path: str, message: str):
        self.code = code
        self.path = path
        self.message = message
        super().__init__(f"{code} at {path or '/'}: {message}")


class QueueFullError(ExecutionError):
    """The instance's pending-job limit has been reached."""


class ExecutionTimeoutError(ExecutionError, TimeoutError):
    """The submission-through-result deadline expired."""


class WorkerExecutionError(ExecutionError):
    """An internal worker, import, serialization or protocol failed."""
