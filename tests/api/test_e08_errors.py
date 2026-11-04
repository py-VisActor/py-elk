"""Public error distinctions and real native facade delegation."""
import asyncio
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk import ELK
from pyelk._errors import (ExecutionError, ExecutionTimeoutError, ModelValidationError,
                           OptionValidationError, QueueFullError, UnknownAlgorithmError,
                           UnsupportedAlgorithmError, UnsupportedFeatureError, ValidationError,
                           WorkerExecutionError)


def graph():
    return {"id": "g", "children": [{"id": "a", "width": 20, "height": 15},
                                      {"id": "b", "width": 30, "height": 25}],
            "edges": [{"id": "e", "sources": ["a"], "targets": ["b"]}]}


class NativeErrorTests(unittest.TestCase):
    def instance(self, options=None, **kwargs):
        instance = ELK(options, **kwargs)
        self.addCleanup(instance.terminateWorker)
        return instance

    def test_unregistered_effective_algorithms_preserve_node_path_and_input(self):
        cases = [({"defaultLayoutOptions": {"elk.algorithm": "unknown"}}, {}, {}, UnknownAlgorithmError,
                  ""),
                 ({"algorithms": []}, {"layoutOptions": {"org.eclipse.elk.algorithm": "stress"}}, {}, UnknownAlgorithmError,
                  ""),
                 ({}, {}, {"elk.algorithm": "unknown"}, UnknownAlgorithmError, "")]
        for constructor, args, local, category, path in cases:
            with self.subTest(path=path):
                instance = self.instance(constructor)
                value = graph()
                if local:
                    value["layoutOptions"] = local
                before = copy.deepcopy((value, args))
                with self.assertRaises(category) as caught:
                    asyncio.run(instance.layout(value, args))
                self.assertEqual(caught.exception.path, path)
                self.assertEqual((value, args), before)
                self.assertEqual(instance.last_trace, [])

    def test_canonical_registration_and_empty_call_override_execute_real_layout(self):
        constructor = {"algorithms": ["org.eclipse.elk.layered", "layered"],
                       "defaultLayoutOptions": {"elk.algorithm": "unknown"}}
        instance = self.instance(constructor)
        value = graph()
        before = copy.deepcopy(value)
        result = asyncio.run(instance.layout(value, {"layoutOptions": {}}))
        self.assertLess(result["children"][0]["x"], result["children"][1]["x"])
        self.assertEqual(value, before)
        self.assertEqual(len(instance.last_trace), 1)
        self.assertEqual(instance.last_trace[0]['processor'],'RecursiveLayoutEngine')
        self.assertEqual(constructor["algorithms"], ["org.eclipse.elk.layered", "layered"])

    def test_local_selector_overrides_global_selector_without_mutating_input(self):
        for value in('unknown','stress'):
            instance = self.instance({"defaultLayoutOptions": {"elk.algorithm": value}})
            request = graph()
            request["layoutOptions"] = {"elk.algorithm": "layered"}
            before = copy.deepcopy(request)
            with self.subTest(value=value):
                result=asyncio.run(instance.layout(request))
                self.assertLess(result['children'][0]['x'],result['children'][1]['x'])
            self.assertEqual(request, before)
            # This call really replaces constructor defaults rather than
            # merely overwriting one subsequently parsed global value.
            self.assertIn("width", asyncio.run(instance.layout(request, {"layoutOptions": {}})))

    def test_real_worker_validation_error_preserves_class_fields_and_recovers(self):
        instance = self.instance()
        value = graph()
        value["edges"][0]["targets"] = ["missing"]
        before = copy.deepcopy(value)
        with self.assertRaises(ModelValidationError) as caught:
            asyncio.run(instance.layout(value))
        self.assertTrue(caught.exception.code)
        self.assertIn("edges", caught.exception.path)
        self.assertEqual(value, before)
        self.assertEqual(instance.last_trace, [])
        self.assertIn("width", asyncio.run(instance.layout(graph())))

    def test_logging_and_execution_timing_reject_non_bool_flags(self):
        instance = self.instance()
        for key in ("logging", "measureExecutionTime"):
            with self.subTest(key=key), self.assertRaises(OptionValidationError) as caught:
                asyncio.run(instance.layout(graph(), {key: 0}))
            self.assertEqual(caught.exception.path, "/layoutArguments/" + key)
        self.assertEqual(instance.last_trace, [])

    def test_duplicate_local_spellings_follow_actual_source_property_assignment(self):
        value = graph()
        value["layoutOptions"] = {"elk.algorithm": "layered", "org.eclipse.elk.algorithm": "layered"}
        before=copy.deepcopy(value)
        result=asyncio.run(self.instance().layout(value))
        self.assertLess(result['children'][0]['x'],result['children'][1]['x'])
        self.assertEqual(value,before)

    def test_execution_errors_remain_distinct_from_validation_and_timeout_is_catchable(self):
        for category in (ExecutionError, QueueFullError, ExecutionTimeoutError, WorkerExecutionError):
            error = category("CODE", "/task", "reason")
            self.assertIsInstance(error, RuntimeError)
            self.assertNotIsInstance(error, ValidationError)
            self.assertEqual((error.code, error.path, error.message), ("CODE", "/task", "reason"))
        self.assertIsInstance(ExecutionTimeoutError("TIMEOUT", "", "expired"), TimeoutError)

    def test_older_success_cannot_publish_trace_after_a_newer_submission(self):
        async def execute():
            instance = self.instance()
            pending = []
            async def controlled(graph, args=None):
                future = asyncio.get_running_loop().create_future()
                pending.append(future)
                return await future
            instance._controller.execute = controlled
            first = asyncio.create_task(instance.layout(graph()))
            await asyncio.sleep(0)
            second = asyncio.create_task(instance.layout(graph()))
            await asyncio.sleep(0)
            pending[0].set_result(SimpleNamespace(graph={"id": "first"}, trace=[{"job": 1}], job_id=1))
            self.assertEqual(await first, {"id": "first"})
            self.assertEqual(instance.last_trace, [])
            pending[1].set_result(SimpleNamespace(graph={"id": "second"}, trace=[{"job": 2}], job_id=2))
            self.assertEqual(await second, {"id": "second"})
            self.assertEqual(instance.last_trace, [{"job": 2}])
        asyncio.run(execute())

    def test_failure_of_latest_submission_keeps_trace_empty_when_older_job_returns(self):
        async def execute():
            instance = self.instance()
            pending = []
            async def controlled(graph, args=None):
                future = asyncio.get_running_loop().create_future()
                pending.append(future)
                return await future
            instance._controller.execute = controlled
            first = asyncio.create_task(instance.layout(graph()))
            await asyncio.sleep(0)
            second = asyncio.create_task(instance.layout(graph()))
            await asyncio.sleep(0)
            pending[1].set_exception(WorkerExecutionError("INTERNAL", "", "controlled protocol failure"))
            with self.assertRaises(WorkerExecutionError):
                await second
            pending[0].set_result(SimpleNamespace(graph={"id": "older"}, trace=[{"job": 1}], job_id=1))
            await first
            self.assertEqual(instance.last_trace, [])
        asyncio.run(execute())


if __name__ == "__main__":
    unittest.main()
