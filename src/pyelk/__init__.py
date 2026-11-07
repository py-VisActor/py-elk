"""Native Python implementation targeting elkjs 0.12.1.

All reference providers are wired to native implementations. Unified algorithm,
API and distribution acceptance is still pending. No Node/JVM/renderer is used
by the runtime; the previous bounded layout path is retained as historical code.
"""

__version__ = "0.1.1"

from .api import ELK
from ._errors import (
    ValidationError, ModelValidationError, OptionValidationError,
    UnknownOptionError, UnsupportedOptionError, UnsupportedFeatureError,
    UnknownAlgorithmError, UnsupportedAlgorithmError, UnsupportedWorkerError,
    ResourceClosedError, ExecutionError, QueueFullError, ExecutionTimeoutError,
    WorkerExecutionError,
)

__all__ = ["__version__", "ELK", "ValidationError", "ModelValidationError",
           "OptionValidationError", "UnknownOptionError", "UnsupportedOptionError",
           "UnsupportedFeatureError", "UnknownAlgorithmError", "UnsupportedAlgorithmError",
           "UnsupportedWorkerError", "ResourceClosedError", "ExecutionError",
           "QueueFullError", "ExecutionTimeoutError", "WorkerExecutionError"]
