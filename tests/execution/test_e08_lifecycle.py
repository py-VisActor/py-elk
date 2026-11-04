"""Actual spawn/lifecycle guards; synthetic workers only isolate host races."""
import asyncio
import copy
import multiprocessing
import os
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if not sys.flags.isolated:
    sys.path.insert(0, str(ROOT / "src"))
else:
    # Installed acceptance invokes this file directly with -I. Never make the
    # repository package importable in that mode, including in spawned children.
    import importlib.metadata
    import pyelk
    installed = importlib.metadata.distribution("py-elk")
    actual = Path(pyelk.__file__).resolve()
    expected = Path(installed.locate_file("pyelk/__init__.py")).resolve()
    if actual != expected or actual.is_relative_to(ROOT / "src"):
        raise RuntimeError("Isolated lifecycle tests must import the installed py-elk distribution")
    if pyelk.__version__ != installed.version:
        raise RuntimeError("Installed lifecycle package/distribution versions differ")

from pyelk._errors import (ExecutionError, ExecutionTimeoutError, ModelValidationError,
                          OptionValidationError, QueueFullError, ResourceClosedError,
                          UnsupportedFeatureError, WorkerExecutionError)
from pyelk.execution import ExecutionController


def graph(dense=False, payload=0):
    count = 8 if dense else 2
    result = {"id": "root", "children": [{"id": str(index), "width": 20, "height": 10} for index in range(count)],
              "edges": [{"id": f"e{source}-{target}", "sources": [str(source)], "targets": [str(target)]}
                        for source in range(count) for target in range(source + 1, count)
                        if dense or (source, target) == (0, 1)],
              "business": {"error": {"stack": "preserved"}, "$H": False}}
    if payload:
        result["business"]["items"] = list(range(payload))
    return result


def synthetic_busy_worker(connection, job_id, graph, constructor, arguments):
    """CPU fixture for queue/deadline races, explicitly not layout evidence."""
    connection.send({"kind": "progress", "job_id": job_id, "index": 0,
                     "processor": "synthetic-host-control", "previous_processor": None,
                     "previous_outcome": None, "process_time": time.process_time()})
    value = 1
    while True:
        value = (value * 17 + 3) % 2147483647


def crash_worker(connection, job_id, graph, constructor, arguments):
    os._exit(23)


def malformed_worker(connection, job_id, graph, constructor, arguments):
    connection.send({"kind": "result", "job_id": job_id + 1, "graph": {}, "trace": []})
    connection.close()


def internal_error_worker(connection, job_id, graph, constructor, arguments):
    connection.send({"kind": "error", "job_id": job_id, "category": "internal", "type": "ImportError",
                     "code": "WORKER_EXECUTION_FAILED", "path": "", "message": "deliberate import control"})
    connection.close()


async def until(engine, predicate, *, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = engine.snapshot()
        if predicate(value):
            return value
        await asyncio.sleep(0.001)
    raise AssertionError("Lifecycle predicate not observed: " + repr(engine.snapshot()))


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engines = []

    def engine(self, **kwargs):
        engine = ExecutionController({}, **kwargs)
        self.engines.append(engine)
        return engine

    async def asyncTearDown(self):
        for engine in self.engines:
            engine.close()
        await asyncio.sleep(0)

    async def test_real_layout_returns_original_geometry_and_isolated_trace(self):
        engine = self.engine()
        original = graph()
        before = copy.deepcopy(original)
        result = await engine.execute(original)
        self.assertEqual(original, before)
        self.assertEqual(result.graph["children"][0]["x"], 12)
        self.assertEqual(result.graph["children"][1]["x"], 52)
        self.assertEqual(len(result.trace), 19)
        self.assertTrue(all(entry["outcome"] == "returned" for entry in result.trace))
        await until(engine, lambda s: not s["dispatcher_alive"])
        snapshot = engine.snapshot()
        self.assertEqual(snapshot["pending"], 0)
        self.assertFalse(snapshot["worker_alive"])
        self.assertEqual(snapshot["jobs"][-1]["exitcode"], 0)
        self.assertTrue(snapshot["jobs"][-1]["reaped"])
        result.graph["business"]["error"]["stack"] = "changed"
        result.trace.clear()
        self.assertEqual((await engine.execute(original)).graph["business"], before["business"])

    async def test_real_empty_graph_keeps_valid_zero_phase_path(self):
        engine = self.engine()
        original = {"id": "empty", "business": {"kept": True}}
        result = await engine.execute(original)
        self.assertEqual(result.trace, [])
        self.assertEqual(result.graph["id"], "empty")
        self.assertEqual(result.graph["business"], {"kept": True})
        self.assertEqual(original, {"id": "empty", "business": {"kept": True}})
        # Foundation identity support does not expand the reviewed E07 scope.
        with self.assertRaises(UnsupportedFeatureError) as caught:
            await engine.execute({"id": 17, "business": {"kept": True}})
        self.assertEqual((caught.exception.code, caught.exception.path), ("UNSUPPORTED_SLICE", "/id"))

    async def test_same_instance_fifo_single_slot_and_independent_inputs(self):
        engine = self.engine()
        tasks = [asyncio.create_task(engine.execute(graph())) for _ in range(3)]
        results = await asyncio.gather(*tasks)
        self.assertEqual([result.job_id for result in results], [1, 2, 3])
        records = engine.snapshot()["jobs"]
        self.assertEqual([record["state"] for record in records], ["returned"] * 3)
        self.assertEqual(len({record["pid"] for record in records}), 3)
        self.assertTrue(all(a["finished_at"] <= b["started_at"] for a, b in zip(records, records[1:])))

    async def test_two_instances_have_distinct_overlapping_real_kernel_processes(self):
        first, second = self.engine(), self.engine()
        tasks = [asyncio.create_task(engine.execute(graph(dense=True, payload=150000))) for engine in (first, second)]
        deadline = time.monotonic() + 15
        observed = None
        while time.monotonic() < deadline:
            snapshots = [engine.snapshot() for engine in (first, second)]
            if all(s["running"] is not None and s["jobs"][-1]["progress"] is not None
                   and s["jobs"][-1]["progress"]["index"] >= 1 for s in snapshots):
                observed = snapshots
                break
            await asyncio.sleep(0.001)
        self.assertIsNotNone(observed)
        self.assertNotEqual(observed[0]["worker_pid"], observed[1]["worker_pid"])
        results = await asyncio.gather(*tasks)
        self.assertEqual(results[0].graph, results[1].graph)
        self.assertTrue(all(engine.snapshot()["jobs"][-1]["reaped"] for engine in (first, second)))

    async def test_queued_cancel_never_spawns_and_does_not_wait_for_running(self):
        engine = self.engine(max_pending=2)
        engine._worker_target = synthetic_busy_worker
        running = asyncio.create_task(engine.execute(graph()))
        await until(engine, lambda s: s["jobs"] and s["jobs"][-1]["progress"] is not None)
        queued = asyncio.create_task(engine.execute(graph()))
        await until(engine, lambda s: s["queued"] == [2])
        queued.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(queued, 3)
        record = engine.snapshot()["jobs"][-1]
        self.assertEqual((record["state"], record["pid"], record["reaped"]), ("cancelled", None, True))
        self.assertFalse(running.done())
        running.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await running

    async def test_pending_limit_counts_running_and_queue_and_accepts_after_cancel(self):
        engine = self.engine(max_pending=1)
        engine._worker_target = synthetic_busy_worker
        first = asyncio.create_task(engine.execute(graph()))
        await until(engine, lambda s: s["running"] == 1)
        with self.assertRaises(QueueFullError) as caught:
            await engine.execute(graph())
        self.assertEqual(caught.exception.code, "QUEUE_FULL")
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        from pyelk.execution.worker import run_job
        engine._worker_target = run_job
        self.assertEqual((await engine.execute(graph())).job_id, 2)

    async def test_running_cancel_reaps_process_and_thread_before_propagation(self):
        engine = self.engine()
        engine._worker_target = synthetic_busy_worker
        task = asyncio.create_task(engine.execute(graph()))
        snapshot = await until(engine, lambda s: s["jobs"] and s["jobs"][-1]["progress"] is not None)
        pid = snapshot["worker_pid"]
        self.assertIn(pid, [child.pid for child in multiprocessing.active_children()])
        task.cancel()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        snapshot = engine.snapshot()
        self.assertEqual(snapshot["pending"], 0)
        self.assertFalse(snapshot["worker_alive"])
        self.assertFalse(snapshot["dispatcher_alive"])
        self.assertNotIn(pid, [child.pid for child in multiprocessing.active_children()])
        self.assertIsNotNone(snapshot["jobs"][-1]["exitcode"])
        self.assertTrue(snapshot["jobs"][-1]["reaped"])

    async def test_real_pipeline_cpu_progress_heartbeat_and_running_cancel(self):
        engine = self.engine()
        ticks = []
        active = True
        async def heartbeat():
            while active:
                snapshot = engine.snapshot()
                if snapshot["jobs"] and snapshot["jobs"][-1]["progress"] is not None:
                    ticks.append((time.monotonic(), snapshot["jobs"][-1]["progress"]["index"]))
                await asyncio.sleep(0.001)
        pulse = asyncio.create_task(heartbeat())
        task = asyncio.create_task(engine.execute(graph(dense=True, payload=150000)))
        snapshot = await until(engine, lambda s: s["running"] is not None and s["jobs"][-1]["progress"] is not None
                               and s["jobs"][-1]["progress"]["index"] >= 1)
        self.assertEqual(snapshot["jobs"][-1]["progress"]["previous_outcome"], "returned")
        self.assertGreater(snapshot["jobs"][-1]["progress"]["process_time"], 0)
        self.assertFalse(task.done())
        await asyncio.sleep(0.003)
        self.assertTrue(ticks)
        self.assertFalse(task.done())
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        active = False
        await pulse
        self.assertEqual(engine.snapshot()["jobs"][-1]["state"], "cancelled")
        self.assertTrue(engine.snapshot()["jobs"][-1]["reaped"])
        self.assertEqual(engine.snapshot()["pending"], 0)
        self.assertEqual(len((await engine.execute(graph())).trace), 19)

    async def test_timeout_includes_spawn_and_recovers(self):
        engine = self.engine(timeout=0.000001)
        with self.assertRaises(ExecutionTimeoutError) as caught:
            await engine.execute(graph())
        self.assertIsInstance(caught.exception, TimeoutError)
        record = engine.snapshot()["jobs"][-1]
        self.assertEqual((record["state"], record["pid"], record["reaped"]), ("failed", None, True))
        engine._timeout = None
        self.assertIsInstance((await engine.execute(graph())).graph, dict)

    async def test_timeout_stops_running_cpu_and_releases_slot(self):
        engine = self.engine(timeout=0.3)
        engine._worker_target = synthetic_busy_worker
        task = asyncio.create_task(engine.execute(graph()))
        await until(engine, lambda s: s["jobs"] and s["jobs"][-1]["progress"] is not None)
        with self.assertRaises(ExecutionTimeoutError):
            await task
        snapshot = await until(engine, lambda s: not s["dispatcher_alive"])
        self.assertTrue(snapshot["jobs"][-1]["reaped"])
        self.assertFalse(snapshot["worker_alive"])
        self.assertEqual(snapshot["pending"], 0)

    async def test_queued_deadline_expires_without_spawn_before_running_ends(self):
        engine = self.engine()
        engine._worker_target = synthetic_busy_worker
        first = asyncio.create_task(engine.execute(graph()))
        await until(engine, lambda s: s["jobs"] and s["jobs"][-1]["progress"] is not None)
        engine._timeout = 0.03
        waiting = asyncio.create_task(engine.execute(graph()))
        with self.assertRaises(ExecutionTimeoutError):
            await asyncio.wait_for(waiting, 2)
        self.assertFalse(first.done())
        record = engine.snapshot()["jobs"][-1]
        self.assertEqual((record["pid"], record["state"]), (None, "failed"))
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first

    async def test_synchronous_close_stops_running_and_rejects_queued(self):
        engine = self.engine()
        engine._worker_target = synthetic_busy_worker
        tasks = [asyncio.create_task(engine.execute(graph())) for _ in range(2)]
        await until(engine, lambda s: s["running"] == 1 and s["queued"] == [2])
        engine.close()
        self.assertEqual(engine.snapshot()["state"], "closed")
        self.assertFalse(engine.snapshot()["worker_alive"])
        self.assertFalse(engine.snapshot()["dispatcher_alive"])
        for task in tasks:
            with self.assertRaises(ResourceClosedError):
                await task
        engine.close()
        with self.assertRaises(ResourceClosedError):
            await engine.execute(graph())

    async def test_close_from_another_thread_is_safely_joined(self):
        engine = self.engine()
        engine._worker_target = synthetic_busy_worker
        task = asyncio.create_task(engine.execute(graph()))
        await until(engine, lambda s: s["running"] is not None)
        await asyncio.to_thread(engine.close)
        with self.assertRaises(ResourceClosedError):
            await task
        self.assertEqual(engine.snapshot()["pending"], 0)
        self.assertFalse(engine.snapshot()["dispatcher_alive"])

    async def test_worker_crash_is_internal_and_next_real_layout_succeeds(self):
        engine = self.engine()
        engine._worker_target = crash_worker
        with self.assertRaises(WorkerExecutionError) as caught:
            await engine.execute(graph())
        self.assertNotIsInstance(caught.exception, UnsupportedFeatureError)
        self.assertEqual(engine.snapshot()["jobs"][-1]["exitcode"], 23)
        self.assertTrue(engine.snapshot()["jobs"][-1]["reaped"])
        from pyelk.execution.worker import run_job
        engine._worker_target = run_job
        self.assertEqual(len((await engine.execute(graph())).trace), 19)

    async def test_unknown_or_wrong_job_worker_message_is_protocol_error(self):
        engine = self.engine()
        engine._worker_target = malformed_worker
        with self.assertRaises(WorkerExecutionError) as caught:
            await engine.execute(graph())
        self.assertEqual(caught.exception.code, "WORKER_PROTOCOL_ERROR")
        self.assertTrue(engine.snapshot()["jobs"][-1]["reaped"])

    async def test_internal_import_error_does_not_become_unsupported(self):
        engine = self.engine()
        engine._worker_target = internal_error_worker
        with self.assertRaises(WorkerExecutionError) as caught:
            await engine.execute(graph())
        self.assertEqual(caught.exception.code, "WORKER_EXECUTION_FAILED")
        self.assertEqual(caught.exception.message, "deliberate import control")

    async def test_validation_errors_preserve_exact_subclass_fields_and_recover(self):
        engine = self.engine()
        with self.assertRaises(ModelValidationError) as caught:
            await engine.execute({"id": "root", "children": [{"id": "same"}, {"id": "same"}]})
        self.assertEqual(caught.exception.code, "DUPLICATE_ID")
        self.assertEqual(caught.exception.path, "/children/1/id")
        self.assertEqual(len((await engine.execute(graph())).trace), 19)

    async def test_arbitrary_user_object_is_rejected_before_spawn_or_pickle(self):
        class Unsafe:
            def __reduce__(self):
                raise AssertionError("Must never pickle a user object")
        engine = self.engine()
        original = graph()
        original["unsafe"] = Unsafe()
        with self.assertRaises(ModelValidationError) as caught:
            await engine.execute(original)
        self.assertEqual((caught.exception.code, caught.exception.path), ("INVALID_JSON", "/graph/unsafe"))
        self.assertEqual(engine.snapshot()["jobs"], [])
        self.assertFalse(engine.snapshot()["dispatcher_alive"])

    async def test_snapshot_cannot_mutate_internal_records(self):
        engine = self.engine()
        await engine.execute(graph())
        snapshot = engine.snapshot()
        snapshot["jobs"][0]["progress"]["processor"] = "wrong"
        snapshot["jobs"].clear()
        self.assertEqual(len(engine.snapshot()["jobs"]), 1)
        self.assertEqual(engine.snapshot()["jobs"][0]["progress"]["processor"], "ReversedEdgeRestorer")

    async def test_published_result_wins_cancel_before_coroutine_resumes(self):
        engine = self.engine()
        task = asyncio.create_task(engine.execute(graph()))
        await until(engine, lambda s: s["running"] is not None)
        with engine._lock:
            future = engine._jobs[1].future
        future.add_done_callback(lambda _: task.cancel())
        result = await task
        self.assertEqual(result.job_id, 1)
        self.assertFalse(task.cancelled())
        self.assertEqual(engine.snapshot()["jobs"][-1]["state"], "returned")

    async def test_cancel_before_result_publication_wins_reaped_result(self):
        engine = self.engine()
        loop = asyncio.get_running_loop()
        original_finish = engine._finish
        task = None
        def finish(job, state, result, error):
            if state == "returned":
                loop.call_soon_threadsafe(task.cancel)
            original_finish(job, state, result, error)
        engine._finish = finish
        task = asyncio.create_task(engine.execute(graph()))
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(engine.snapshot()["jobs"][-1]["state"], "cancelled")
        self.assertTrue(engine.snapshot()["jobs"][-1]["reaped"])

    async def test_close_before_result_publication_rejects_old_result(self):
        engine = self.engine()
        loop = asyncio.get_running_loop()
        original_finish = engine._finish
        def finish(job, state, result, error):
            if state == "returned":
                loop.call_soon_threadsafe(engine.close)
            original_finish(job, state, result, error)
        engine._finish = finish
        with self.assertRaises(ResourceClosedError):
            await engine.execute(graph())
        self.assertEqual(engine.snapshot()["state"], "closed")

    async def test_slow_spawn_does_not_hold_snapshot_or_submit_state_lock(self):
        engine = self.engine()
        entered = threading.Event()
        release = threading.Event()
        context = multiprocessing.get_context("spawn")
        actual_process = context.Process
        class ProcessWrapper:
            def __init__(self, *args, **kwargs):
                self.inner = actual_process(*args, **kwargs)
            def start(self):
                entered.set()
                release.wait(5)
                return self.inner.start()
            def __getattr__(self, key):
                return getattr(self.inner, key)
        class ContextWrapper:
            Pipe = staticmethod(context.Pipe)
            Process = ProcessWrapper
        with patch("pyelk.execution.lifecycle.multiprocessing.get_context", return_value=ContextWrapper()):
            first = asyncio.create_task(engine.execute(graph()))
            while not entered.is_set():
                await asyncio.sleep(0.001)
            start = time.monotonic()
            self.assertEqual(engine.snapshot()["pending"], 1)
            second = asyncio.create_task(engine.execute(graph()))
            await asyncio.sleep(0)
            self.assertEqual(engine.snapshot()["pending"], 2)
            self.assertLess(time.monotonic() - start, 0.1)
            release.set()
            self.assertEqual([result.job_id for result in await asyncio.gather(first, second)], [1, 2])

    async def test_active_cross_loop_rejected_without_poisoning_original(self):
        engine = self.engine()
        engine._worker_target = synthetic_busy_worker
        task = asyncio.create_task(engine.execute(graph()))
        await until(engine, lambda s: s["running"] is not None)
        def other_loop():
            with self.assertRaises(ExecutionError) as caught:
                asyncio.run(engine.execute(graph()))
            return caught.exception.code
        self.assertEqual(await asyncio.to_thread(other_loop), "EVENT_LOOP_CONFLICT")
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task


class LifecycleBoundaryTests(unittest.TestCase):
    def test_constructor_bounds_and_timeout_values(self):
        for value in (False, True, 0, -1, 65, 1.0, "16", None):
            with self.subTest(max_pending=value), self.assertRaises(OptionValidationError):
                ExecutionController({}, max_pending=value)
        for value in (False, True, 0, -1, float("nan"), float("inf"), "1", 10**1000):
            with self.subTest(timeout=str(value)[:30]), self.assertRaises(OptionValidationError):
                ExecutionController({}, timeout=value)
        for value in (1, 64):
            engine = ExecutionController({}, max_pending=value, timeout=1)
            engine.close()

    def test_idle_instance_rebinds_across_asyncio_run_and_closes_without_loop(self):
        engine = ExecutionController({})
        try:
            first = asyncio.run(engine.execute(graph()))
            second = asyncio.run(engine.execute(graph()))
            self.assertEqual((first.job_id, second.job_id), (1, 2))
            self.assertEqual(first.graph, second.graph)
        finally:
            engine.close()
        self.assertEqual(engine.snapshot()["state"], "closed")
        self.assertFalse(engine.snapshot()["dispatcher_alive"])

    def test_protocol_rejects_wrong_kind_fields_job_types_error_class_and_progress(self):
        job = SimpleNamespace(job_id=1, pid=123, progress=None, graph={"id": "root"})
        progress = {"kind": "progress", "job_id": 1, "index": 0, "processor": "GreedyCycleBreaker",
                    "previous_processor": None, "previous_outcome": None, "process_time": 0.1}
        result = {"kind": "result", "job_id": 1, "graph": {"id": "root"}, "trace": [], "pid": 123,
                  "process_time": 0.1}
        error = {"kind": "error", "job_id": 1, "category": "validation", "type": "ModelValidationError",
                 "code": "INVALID_GRAPH", "path": "/graph", "message": "expected"}
        mutants = [None, [], {}, {"kind": "mystery", "job_id": 1}, {**progress, "job_id": True},
                   {**progress, "index": True}, {**progress, "index": 1}, {**progress, "previous_outcome": "returned"},
                   {**progress, "process_time": float("nan")}, {**progress, "process_time": True},
                   {**progress, "process_time": 10**1000},
                   {**progress, "extra": 1}, {**result, "pid": True}, {**result, "pid": 124},
                   {**result, "process_time": float("inf")}, {**result, "trace": {}},
                   {**result, "process_time": 10**1000},
                   {**result, "graph": {}}, {**result, "graph": {"id": "wrong"}},
                   {**result, "trace": [{"index": 0}]}, {**result, "graph": {"business": object()}},
                   {**error, "type": "builtins.AssertionError"}, {**error, "code": None},
                   {**error, "category": "internal"}, {**error, "type": "WorkerExecutionError"}]
        for mutant in mutants:
            with self.subTest(mutant=repr(mutant)), self.assertRaises(WorkerExecutionError) as caught:
                ExecutionController._decode(job, mutant)
            self.assertEqual(caught.exception.code, "WORKER_PROTOCOL_ERROR")
        self.assertEqual(ExecutionController._decode(job, progress)[0], "progress")
        self.assertEqual(ExecutionController._decode(job, result)[0], "result")
        self.assertIsInstance(ExecutionController._decode(job, error)[1], ModelValidationError)
        job.progress = {key: value for key, value in progress.items() if key not in ("kind", "job_id")}
        with self.assertRaises(WorkerExecutionError):
            ExecutionController._decode(job, progress)
        job.progress = None
        job.graph = graph()
        with self.assertRaises(WorkerExecutionError):
            ExecutionController._decode(job, result)

    def test_spawn_failure_is_internal_and_recoverable_without_a_live_handle(self):
        engine = ExecutionController({})
        try:
            with patch("pyelk.execution.lifecycle.multiprocessing.get_context", side_effect=OSError("spawn control")):
                with self.assertRaises(WorkerExecutionError) as caught:
                    asyncio.run(engine.execute(graph()))
            self.assertEqual(caught.exception.code, "WORKER_EXITED")
            self.assertTrue(engine.snapshot()["jobs"][-1]["reaped"])
            self.assertFalse(engine.snapshot()["worker_alive"])
            self.assertIsInstance(asyncio.run(engine.execute(graph())).graph, dict)
        finally:
            engine.close()


if __name__ == "__main__":
    unittest.main()
