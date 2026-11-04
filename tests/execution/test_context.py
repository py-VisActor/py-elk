"""Single-call data isolation tests; no scheduler or layout is implemented."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk._errors import ModelValidationError, OptionValidationError, UnsupportedFeatureError
from pyelk.execution import ExecutionContext, create_context


def graph():
    return {"id": "root", "business": {"$H": False, "error": {"stack": "keep"}},
            "children": [{"id": "a", "width": 40, "height": 30}, {"id": "b", "width": 40, "height": 30}],
            "edges": [{"id": "e", "sources": ["a"], "targets": ["b"]}]}


class ContextOwnershipTests(unittest.TestCase):
    def test_context_does_not_mutate_or_add_coordinates_to_original_graph(self):
        original = graph()
        before = copy.deepcopy(original)
        context = ExecutionContext.create(original)
        self.assertEqual(original, before)
        self.assertEqual(context.working_graph.to_json(), before)
        self.assertEqual(context.original_graph, before)
        self.assertNotIn("x", context.working_graph.root.to_json())
        self.assertEqual(context.resolved_options.values["org.eclipse.elk.direction"], "UNDEFINED")

    def test_two_contexts_do_not_share_working_graph_or_scratch_state(self):
        original = graph()
        first, second = create_context(original), create_context(original)
        first.working_graph.root.set_property("business", {"changed": True})
        first.working_graph.node("a").set_property("width", 40 + 1e-10)
        first.state["pipeline"] = ["only-first"]
        self.assertNotEqual(first.working_graph.to_json(), second.working_graph.to_json())
        self.assertEqual(second.working_graph.to_json(), original)
        self.assertEqual(second.state, {})
        self.assertEqual(first.original_graph, original)

    def test_all_snapshots_are_returned_as_independent_deep_copies(self):
        original = graph()
        constructor = {"defaultLayoutOptions": {"elk.randomSeed": 7}, "data": {"enabled": False}}
        arguments = {"layoutOptions": {}, "data": {"x": 0}}
        context = create_context(original, constructor=constructor, layout_arguments=arguments)
        context.original_graph["business"]["error"]["stack"] = "changed"
        context.original_constructor["data"]["enabled"] = True
        context.original_arguments["data"]["x"] = 1
        original["business"]["$H"] = 123
        constructor["data"]["enabled"] = True
        arguments["data"]["x"] = 2
        self.assertIs(context.original_graph["business"]["$H"], False)
        self.assertEqual(context.original_graph["business"]["error"]["stack"], "keep")
        self.assertIs(context.original_constructor["data"]["enabled"], False)
        self.assertEqual(context.original_arguments["data"]["x"], 0)

    def test_root_local_overrides_only_selected_global(self):
        original = graph()
        original["layoutOptions"] = {"elk.direction": "UP"}
        context = create_context(original, constructor={"defaultLayoutOptions": {"elk.direction": "DOWN", "elk.randomSeed": 7}},
                                 layout_arguments={"layoutOptions": {"elk.spacing.nodeNode": 31}})
        self.assertEqual(context.resolved_options.selected_global, "call")
        self.assertEqual(context.resolved_options.values["org.eclipse.elk.direction"], "UP")
        self.assertEqual(context.seed, 1)

    def test_seed_zero_and_negative_seed_are_values_without_random_stream(self):
        for seed in (0, -7):
            context = create_context(graph(), layout_arguments={"layoutOptions": {"elk.randomSeed": seed}})
            self.assertEqual(context.seed, seed)
            self.assertFalse(hasattr(context, "random"))
            self.assertFalse(hasattr(context, "rng"))
            self.assertEqual(context.state, {})

    def test_worker_parameters_are_rejected_by_presence(self):
        for key in ("workerUrl", "workerFactory"):
            for value in (None, False, 0, ""):
                with self.subTest(key=key, value=value), self.assertRaises(UnsupportedFeatureError) as caught:
                    create_context(graph(), constructor={key: value})
                self.assertEqual(caught.exception.path, "/constructor/" + key)

    def test_constructor_algorithm_filter_must_include_effective_layered(self):
        for algorithms in ([], ["stress"], ["org.eclipse.elk.layered"]):
            with self.subTest(algorithms=algorithms), self.assertRaises(UnsupportedFeatureError):
                create_context(graph(), constructor={"algorithms": algorithms})
        for algorithms in (None, False, "layered", [False]):
            with self.subTest(algorithms=algorithms), self.assertRaises(OptionValidationError):
                create_context(graph(), constructor={"algorithms": algorithms})
        self.assertEqual(create_context(graph(), constructor={"algorithms": ["layered", "stress"]}).seed, 1)

    def test_root_option_null_is_not_outer_none_convenience(self):
        for value in (None, False, 0, ""):
            original = graph()
            original["layoutOptions"] = value
            with self.subTest(value=value), self.assertRaises(ModelValidationError) as caught:
                create_context(original)
            self.assertEqual(caught.exception.code, "INVALID_CONTAINER")
            self.assertEqual(caught.exception.path, "/layoutOptions")
        self.assertEqual(create_context(graph(), constructor=None, layout_arguments=None).original_constructor, {})


if __name__ == "__main__":
    unittest.main()
