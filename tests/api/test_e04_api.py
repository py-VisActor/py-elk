"""Public facade regressions, updated for the full native execution path."""
import asyncio
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk import ELK
from pyelk._errors import ValidationError


def chain():
    return {"id": "g", "children": [{"id": "a", "width": 20, "height": 15}, {"id": "b", "width": 30, "height": 25}],
            "edges": [{"id": "e", "sources": ["a"], "targets": ["b"]}],
            "business": {"$H": False, "error": {"stack": "caller data"}}}


class ExperimentalFacadeTests(unittest.TestCase):
    def instance(self,options=None):
        instance=ELK(options);self.addCleanup(instance.close);return instance

    def test_same_instance_calls_restart_work_and_outputs_are_not_shared(self):
        graph = chain()
        original = copy.deepcopy(graph)
        instance = self.instance()
        first = asyncio.run(instance.layout(graph))
        trace = instance.last_trace
        first["children"][0]["x"] = 999
        trace[0]["processor"] = "edited copy"
        second = asyncio.run(instance.layout(graph))
        self.assertNotEqual(second["children"][0]["x"], 999)
        self.assertEqual(instance.last_trace[0]["processor"], "RecursiveLayoutEngine")
        self.assertEqual(instance.last_trace[-1]["after"]["edges"], 1)
        self.assertEqual(instance.last_trace[-1]["outcome"], "returned")
        self.assertEqual(graph, original)
        self.assertEqual(second["business"], original["business"])

    def test_constructor_copies_options_and_call_empty_mapping_replaces_defaults(self):
        constructor = {"defaultLayoutOptions": {"elk.direction": "LEFT"}}
        instance = self.instance(constructor)
        arguments = {"layoutOptions": {}}
        before = copy.deepcopy(arguments)
        result = asyncio.run(instance.layout(chain(), arguments))
        self.assertLess(result["children"][0]["x"], result["children"][1]["x"])
        self.assertEqual(arguments, before)
        self.assertEqual(constructor["defaultLayoutOptions"]["elk.direction"], "LEFT")

    def test_former_slice_exclusions_execute_and_preserve_caller_data(self):
        for mutate in (lambda g: g["children"][0].update(labels=[{"text": "x"}]),
                       lambda g: g["children"][0].update({"$H": 0})):
            graph = chain()
            mutate(graph)
            before = copy.deepcopy(graph)
            result=asyncio.run(self.instance().layout(graph))
            self.assertGreater(result['width'],0)
            self.assertTrue(result['edges'][0]['sections'])
            if 'labels'in graph['children'][0]:
                self.assertEqual(result['children'][0]['labels'][0]['text'],'x')
            else:self.assertEqual(result['children'][0]['$H'],0)
            self.assertEqual(graph, before)

    def test_reserved_root_logging_is_cleaned_on_the_returned_copy(self):
        # E09 migrates the former unsupported-root-logging case to the actual
        # source cleanup branch. Business fields with the same names survive.
        graph = chain()
        graph.update(logging={"old": True}, executionTime=321)
        graph["business"].update(logging={"executionTime": "caller"})
        original = copy.deepcopy(graph)
        instance = self.instance()
        try:
            result = asyncio.run(instance.layout(graph))
            self.assertNotIn("logging", result)
            self.assertEqual(result["executionTime"], 321)
            self.assertEqual(result["business"], original["business"])
            self.assertEqual(graph, original)
            self.assertIn("width", result)
        finally:
            instance.terminateWorker()

    def test_down_direction_uses_real_transforms_and_preserves_input(self):
        graph = chain()
        graph["layoutOptions"] = {"elk.direction": "DOWN"}
        before = copy.deepcopy(graph)
        instance = self.instance()
        result = asyncio.run(instance.layout(graph))
        self.assertLess(result["children"][0]["y"], result["children"][1]["y"])
        trace = instance.last_trace
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]["processor"], "RecursiveLayoutEngine")
        self.assertEqual(trace[-1]["outcome"], "returned")
        self.assertEqual(graph, before)

    def test_worker_callable_is_rejected_without_executing_it(self):
        called = []
        with self.assertRaises(ValidationError):
            ELK({"workerFactory": lambda: called.append(True)})
        self.assertEqual(called, [])

    def test_local_close_is_idempotent_and_rejects_new_work(self):
        instance = self.instance()
        asyncio.run(instance.layout(chain()))
        self.assertIsNone(instance.terminateWorker())
        self.assertIsNone(instance.terminateWorker())
        with self.assertRaises(ValidationError) as caught:
            asyncio.run(instance.layout(chain()))
        self.assertEqual(caught.exception.code, "RESOURCE_CLOSED")
        self.assertEqual(instance.last_trace, [])


if __name__ == "__main__":
    unittest.main()
