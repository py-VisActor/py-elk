"""Bounded single-slot scheduling with genuine spawned-process cancellation.

The queue, deadlines and termination policy are Python host design (ADR0007).
The original context and algorithm remain unchanged in the child process.
"""
from __future__ import annotations

import asyncio
from collections import deque
from concurrent.futures import Future as CleanupFuture
from dataclasses import dataclass, field
import math
import multiprocessing
import threading
import time

from .. import _errors
from .._errors import (ExecutionError, ExecutionTimeoutError, OptionValidationError,
                       QueueFullError, ResourceClosedError, WorkerExecutionError)
from .._json import clone_json
from .worker import run_job


@dataclass(frozen=True)
class ExecutionResult:
    graph: dict
    trace: list
    job_id: int


@dataclass
class _Job:
    job_id: int
    graph: object
    arguments: object
    loop: object
    future: object
    submitted_at: float
    deadline: float | None
    cleanup: CleanupFuture = field(default_factory=CleanupFuture)
    state: str = "queued"
    stop: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    pid: int | None = None
    exitcode: int | None = None
    reaped: bool = False
    progress: dict | None = None
    process: object = None
    connection: object = None
    dispatcher: object = None
    owner: object = None
    cancellation_count: int = 0


_VALIDATION_TYPES = (
    "ValidationError", "ModelValidationError", "OptionValidationError", "UnknownOptionError",
    "UnsupportedOptionError", "UnsupportedFeatureError", "UnknownAlgorithmError",
    "UnsupportedAlgorithmError", "UnsupportedWorkerError", "ResourceClosedError",
)


class ExecutionController:
    """One running child per instance; FIFO pending count includes that child."""

    def __init__(self, constructor=None, *, max_pending=16, timeout=None):
        if type(max_pending) is not int or not 1 <= max_pending <= 64:
            raise OptionValidationError("INVALID_OPTION_VALUE", "/max_pending", "Expected an integer from 1 to 64")
        try:
            valid_timeout = timeout is None or (type(timeout) in (int, float)
                                                and math.isfinite(timeout) and timeout > 0)
        except OverflowError:
            valid_timeout = False
        if not valid_timeout:
            raise OptionValidationError("INVALID_OPTION_VALUE", "/timeout", "Expected finite positive seconds or None")
        self._constructor = clone_json({} if constructor is None else constructor,
                                       path="/constructor", error_type=OptionValidationError)
        self._max_pending = max_pending
        self._timeout = timeout
        self._lock = threading.RLock()
        self._reap_lock = threading.Lock()
        self._wake = threading.Event()
        self._state = "open"
        self._queue = deque()
        self._jobs = {}
        self._history = deque(maxlen=64)
        self._active = None
        self._thread = None
        self._last_thread = None
        self._loop = None
        self._next_id = 0
        self._worker_target = run_job  # Private injection point for protocol/crash tests.

    async def execute(self, graph, args=None):
        submitted_at = time.monotonic()
        loop = asyncio.get_running_loop()
        with self._lock:
            self._check_submission(loop)
        # Strict copies prevent arbitrary user objects crossing pickle/spawn.
        graph_copy = clone_json(graph, path="/graph", error_type=_errors.ModelValidationError)
        arguments = clone_json({} if args is None else args, path="/layoutArguments",
                               error_type=OptionValidationError)
        with self._lock:
            self._check_submission(loop)
            self._loop = loop
            self._next_id += 1
            future = loop.create_future()
            deadline = None if self._timeout is None else submitted_at + self._timeout
            job = _Job(self._next_id, graph_copy, arguments, loop, future, submitted_at, deadline)
            job.owner = asyncio.current_task()
            job.cancellation_count = job.owner.cancelling()
            self._jobs[job.job_id] = job
            self._queue.append(job)
            if self._thread is None:
                self._thread = threading.Thread(target=self._dispatch, name="pyelk-dispatch-" + str(id(self)), daemon=True)
                self._last_thread = self._thread
                self._thread.start()
            job.dispatcher = self._thread
            self._wake.set()
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            with self._lock:
                if job.state == "returned" and future.done() and not future.cancelled():
                    # The loop already published the completed result before cancel.
                    return future.result()
                if job.state in ("queued", "running"):
                    job.stop = "cancel"
                    self._wake.set()
                elif job.state == "returned" and not future.done():
                    # Reaping finished but delivery has not yet been published.
                    job.stop = "cancel"
                    job.state = "cancelled"
                    for record in self._history:
                        if record["job_id"] == job.job_id:
                            record["state"] = "cancelled"
            # Repeated Task.cancel calls must not escape before actual cleanup.
            cleanup = asyncio.wrap_future(job.cleanup, loop=loop)
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    continue
            cleanup.result()
            # An otherwise idle instance also releases its management thread.
            while job.dispatcher.is_alive():
                with self._lock:
                    if self._jobs:
                        break
                try:
                    await asyncio.sleep(0.001)
                except asyncio.CancelledError:
                    continue
            # Consume an already committed error when cancellation raced delivery.
            if future.done() and not future.cancelled():
                future.exception()
            raise

    def _check_submission(self, loop):
        if self._state != "open":
            raise ResourceClosedError("RESOURCE_CLOSED", "", "The native instance is closed")
        if self._jobs and self._loop is not loop:
            raise ExecutionError("EVENT_LOOP_CONFLICT", "", "Active tasks belong to another event loop")
        if len(self._jobs) >= self._max_pending:
            raise QueueFullError("QUEUE_FULL", "", "The instance pending-task limit has been reached")

    @staticmethod
    def _job_snapshot(job):
        return {"job_id": job.job_id, "state": job.state, "pid": job.pid, "exitcode": job.exitcode,
                "reaped": job.reaped, "submitted_at": job.submitted_at, "started_at": job.started_at,
                "finished_at": job.finished_at, "progress": job.progress}

    def snapshot(self):
        """Return independent diagnostics; these never enter the layout JSON."""
        with self._lock:
            active = self._active
            thread = self._last_thread
            worker_alive = False
            if active is not None and active.process is not None and active.pid is not None and not active.reaped:
                try:
                    worker_alive = active.process.is_alive()
                except (ValueError, AssertionError):
                    # Concurrent reaping may already have closed the handle.
                    pass
            value = {"state": self._state, "pending": len(self._jobs),
                     "queued": [job.job_id for job in self._queue if job.state == "queued"],
                     "running": None if active is None or active.state != "running" else active.job_id,
                     "worker_pid": None if active is None else active.pid,
                     "worker_alive": worker_alive,
                     "dispatcher_alive": thread is not None and thread.is_alive(),
                     "last_submitted_id": self._next_id,
                     "jobs": sorted([*self._history, *(self._job_snapshot(job) for job in self._jobs.values())],
                                    key=lambda job: job["job_id"])}
            return clone_json(value)

    def _dispatch(self):
        try:
            while True:
                with self._lock:
                    if not self._queue:
                        self._thread = None
                        return
                    job = self._queue.popleft()
                    self._active = job
                self._run(job)
        finally:
            with self._lock:
                if self._thread is threading.current_thread():
                    self._thread = None

    def _stop_reason(self, job):
        with self._lock:
            if job.stop is not None:
                return job.stop
            if self._state != "open":
                return "close"
            if job.deadline is not None and time.monotonic() >= job.deadline:
                return "timeout"
        return None

    def _sweep_queue(self):
        # Waiting cancellation/deadlines do not depend on the active layout ending.
        with self._lock:
            for waiting in list(self._queue):
                reason = self._stop_reason(waiting)
                if reason is not None:
                    self._queue.remove(waiting)
                    waiting.reaped = True  # No process was ever created.
                    self._finish(waiting, "cancelled" if reason == "cancel" else "failed",
                                 None, self._reason_error(reason))

    @staticmethod
    def _reason_error(reason):
        if reason == "close":
            return ResourceClosedError("RESOURCE_CLOSED", "", "The native instance is closed")
        if reason == "timeout":
            return ExecutionTimeoutError("EXECUTION_TIMEOUT", "", "The layout submission deadline expired")
        return None

    def _run(self, job):
        result = error = None
        reason = self._stop_reason(job)
        receiver = sender = None
        try:
            if reason is None:
                context = multiprocessing.get_context("spawn")
                receiver, sender = context.Pipe(duplex=False)
                process = context.Process(target=self._worker_target,
                                          args=(sender, job.job_id, job.graph, self._constructor, job.arguments),
                                          name="pyelk-worker-" + str(job.job_id), daemon=True)
                # Spawn/pickle may block: never hold the event-loop-facing state lock.
                # The reap lock makes assignment/start indivisible with synchronous close.
                with self._reap_lock:
                    with self._lock:
                        reason = self._stop_reason(job)
                        if reason is None:
                            job.process = process
                            job.connection = receiver
                    if reason is None:
                        process.start()
                        with self._lock:
                            job.pid = process.pid
                            job.started_at = time.monotonic()
                            job.state = "running"
                sender.close()
                sender = None
                if reason is None:
                    while True:
                        self._sweep_queue()
                        reason = self._stop_reason(job)
                        if reason is not None:
                            break
                        if receiver.poll(0.005):
                            envelope = receiver.recv()
                            kind, value = self._decode(job, envelope)
                            if kind == "progress":
                                with self._lock:
                                    job.progress = value
                                continue
                            result, error = value if kind == "result" else None, value if kind == "error" else None
                            break
                        if process.exitcode is not None:
                            raise WorkerExecutionError("WORKER_EXITED", "", "The worker exited without a result")
        except (EOFError, BrokenPipeError, OSError) as caught:
            error = WorkerExecutionError("WORKER_EXITED", "", "The worker connection closed: " + str(caught))
        except Exception as caught:
            error = caught if isinstance(caught, WorkerExecutionError) else WorkerExecutionError(
                "WORKER_START_FAILED" if job.started_at is None else "WORKER_EXECUTION_FAILED", "", str(caught))
        finally:
            if sender is not None:
                sender.close()
            try:
                self._reap(job, stop=reason is not None or error is not None)
                if result is not None and job.exitcode != 0:
                    result = None
                    error = WorkerExecutionError("WORKER_EXITED", "", "The worker did not exit normally after its result")
            except Exception as caught:
                error = caught
            if receiver is not None:
                receiver.close()
        # Cancellation/close/deadline wins until committing the terminal state.
        with self._lock:
            reason = self._stop_reason(job) or reason
            if job.process is None:
                job.reaped = True
            if reason is not None and job.reaped:
                result, error = None, self._reason_error(reason)
            if not job.reaped:
                self._state = "closing"
                error = WorkerExecutionError("WORKER_SHUTDOWN_FAILED", "", "The worker remains unreaped")
                reason = None
            state = "cancelled" if reason == "cancel" else "failed" if error is not None else "returned"
            self._finish(job, state, result, error)

    def _reap(self, job, *, stop):
        with self._reap_lock:
            process = job.process
            if process is None or job.reaped:
                return
            if process.pid is None:
                process.close()
                job.reaped = True
                return
            if stop and process.is_alive():
                process.terminate()
            process.join(0.5)
            if process.is_alive():
                process.kill()
                process.join(2)
            if process.is_alive():
                raise WorkerExecutionError("WORKER_SHUTDOWN_FAILED", "", "The worker could not be stopped and reaped")
            job.exitcode = process.exitcode
            process.close()
            job.reaped = True

    def _finish(self, job, state, result, error):
        job.state = state
        job.finished_at = time.monotonic()
        if job.reaped:
            self._history.append(self._job_snapshot(job))
            self._jobs.pop(job.job_id, None)
            if self._active is job:
                self._active = None
        job.graph = job.arguments = job.connection = None
        def deliver():
            with self._lock:
                if job.future.done():
                    return
                cancellation_pending = job.owner.cancelling() > job.cancellation_count
                if state == "cancelled" or job.stop == "cancel" or cancellation_pending:
                    job.state = "cancelled"
                    for record in self._history:
                        if record["job_id"] == job.job_id:
                            record["state"] = "cancelled"
                    job.future.cancel()
                elif error is not None:
                    job.future.set_exception(error)
                elif self._state != "open":
                    job.state = "failed"
                    for record in self._history:
                        if record["job_id"] == job.job_id:
                            record["state"] = "failed"
                    job.future.set_exception(self._reason_error("close"))
                else:
                    job.future.set_result(result)
        try:
            job.loop.call_soon_threadsafe(deliver)
        except RuntimeError:
            # A destroyed caller loop cannot receive data; resources are still reaped.
            pass
        if job.reaped:
            job.cleanup.set_result(None)
        else:
            job.cleanup.set_exception(error)

    @staticmethod
    def _decode(job, envelope):
        def malformed():
            raise WorkerExecutionError("WORKER_PROTOCOL_ERROR", "", "Invalid worker message")
        def duration(value):
            try:
                return type(value) in (int, float) and math.isfinite(value) and value >= 0
            except OverflowError:
                return False
        if type(envelope) is not dict or type(envelope.get("job_id")) is not int or envelope["job_id"] != job.job_id:
            malformed()
        kind = envelope.get("kind")
        if kind == "progress":
            keys = {"kind", "job_id", "index", "processor", "previous_processor", "previous_outcome", "process_time"}
            if set(envelope) != keys or type(envelope["index"]) is not int or envelope["index"] < 0:
                malformed()
            if type(envelope["processor"]) is not str or envelope["previous_outcome"] not in (None, "returned"):
                malformed()
            if envelope["previous_processor"] is not None and type(envelope["previous_processor"]) is not str:
                malformed()
            if not duration(envelope["process_time"]):
                malformed()
            previous = job.progress
            if (envelope["index"] != (0 if previous is None else previous["index"] + 1)
                    or envelope["previous_processor"] != (None if previous is None else previous["processor"])
                    or envelope["previous_outcome"] != (None if previous is None else "returned")
                    or (previous is not None and envelope["process_time"] < previous["process_time"])):
                malformed()
            return kind, {key: value for key, value in envelope.items() if key not in ("kind", "job_id")}
        if kind == "result":
            if set(envelope) != {"kind", "job_id", "graph", "trace", "pid", "process_time"}:
                malformed()
            if type(envelope["graph"]) is not dict or type(envelope["trace"]) is not list or envelope["pid"] != job.pid:
                malformed()
            if type(envelope["pid"]) is not int or not duration(envelope["process_time"]):
                malformed()
            try:
                graph = clone_json(envelope["graph"])
                trace = clone_json(envelope["trace"])
            except _errors.ValidationError:
                malformed()
            if (type(graph.get("id")) not in (str, int)
                    or type(graph["id"]) is not type(job.graph.get("id")) or graph["id"] != job.graph.get("id")
                    or (job.graph.get("children") and not trace)):
                malformed()
            if len(trace) != (0 if job.progress is None else job.progress["index"] + 1):
                malformed()
            for index, entry in enumerate(trace):
                if (type(entry) is not dict or type(entry.get("index")) is not int or entry["index"] != index
                        or type(entry.get("processor")) is not str or entry.get("outcome") != "returned"
                        or type(entry.get("before")) is not dict or type(entry.get("after")) is not dict):
                    malformed()
            if trace and (trace[-1]["processor"] != job.progress["processor"]
                          or envelope["process_time"] < job.progress["process_time"]):
                malformed()
            return kind, ExecutionResult(graph, trace, job.job_id)
        if kind == "error":
            if set(envelope) != {"kind", "job_id", "category", "type", "code", "path", "message"}:
                malformed()
            if any(type(envelope[key]) is not str for key in ("category", "type", "code", "path", "message")):
                malformed()
            if envelope["category"] == "validation" and envelope["type"] in _VALIDATION_TYPES:
                error_type = getattr(_errors, envelope["type"])
            elif envelope["category"] == "internal" and envelope["code"] == "WORKER_EXECUTION_FAILED" and envelope["path"] == "":
                error_type = WorkerExecutionError
            else:
                malformed()
            return kind, error_type(envelope["code"], envelope["path"], envelope["message"])
        malformed()

    def close(self):
        """Synchronously stop/reap all work and release the dispatcher thread."""
        with self._lock:
            if self._state == "closed":
                return
            self._state = "closing"
            for job in self._jobs.values():
                job.stop = "close"
            active = self._active
            thread = self._thread
            self._wake.set()
        if active is not None:
            self._reap(active, stop=True)
        if thread is not None and thread is not threading.current_thread():
            thread.join(5)
            if thread.is_alive():
                raise WorkerExecutionError("WORKER_SHUTDOWN_FAILED", "", "The dispatcher could not be joined")
        with self._lock:
            if active is not None and active.reaped and active.job_id in self._jobs:
                self._history.append(self._job_snapshot(active))
                self._jobs.pop(active.job_id)
                self._active = None
            if self._jobs:
                raise WorkerExecutionError("WORKER_SHUTDOWN_FAILED", "", "Pending tasks remain after shutdown")
            self._state = "closed"
