"""Spawn-only Python host worker for the reviewed layout kernel and observers.

This is host execution design, not a port of JavaScript worker cancellation.
Only JSON snapshots and a private Connection cross the process boundary.
"""
from __future__ import annotations

import os
import time

from .._errors import ValidationError


class _ObservedTrace(list):
    """Observe the existing append boundary without changing phase execution."""

    def __init__(self, connection, job_id):
        super().__init__()
        self.connection = connection
        self.job_id = job_id

    def append(self, entry):
        previous = self[-1] if self else None
        super().append(entry)
        self.connection.send({"kind": "progress", "job_id": self.job_id,
                              "index": entry["index"], "processor": entry["processor"],
                              "previous_processor": None if previous is None else previous["processor"],
                              "previous_outcome": None if previous is None else previous.get("outcome"),
                              "process_time": time.process_time()})


def run_job(connection, job_id, graph, constructor, arguments):
    """Run one real context/kernel and send a fixed, plain-data envelope."""
    try:
        from .context import create_context
        from ..algorithms.layered.scope import validate_slice
        from ..algorithms.layered.pipeline import layout_context

        context = create_context(graph, constructor=constructor, layout_arguments=arguments)
        validate_slice(context)
        trace = _ObservedTrace(connection, job_id)
        from .diagnostics import BasicProgressMonitor
        effective_arguments = context.original_arguments
        logging = effective_arguments.get('logging', False)
        timing = effective_arguments.get('measureExecutionTime', False)
        monitor = BasicProgressMonitor(logging, timing) if logging or timing else None
        result = (layout_context(context, trace=trace) if monitor is None else
                  layout_context(context, trace=trace, monitor=monitor))
        # Fixed layout_11 clears only the reserved root key after success.
        result.pop('logging', None)
        if monitor is not None:
            result['logging'] = monitor.collect()
        connection.send({"kind": "result", "job_id": job_id, "graph": result, "trace": list(trace),
                         "pid": os.getpid(), "process_time": time.process_time()})
    except ValidationError as error:
        connection.send({"kind": "error", "job_id": job_id, "category": "validation",
                         "type": type(error).__name__, "code": error.code,
                         "path": error.path, "message": error.message})
    except Exception as error:
        connection.send({"kind": "error", "job_id": job_id, "category": "internal",
                         "type": type(error).__name__, "code": "WORKER_EXECUTION_FAILED", "path": "",
                         "message": str(error)})
    finally:
        connection.close()
