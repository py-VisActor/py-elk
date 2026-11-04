"""Independent per-call data isolation checks; no async/lifecycle/PRNG claims."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pyelk._errors import UnsupportedFeatureError, ValidationError
from pyelk.execution import ExecutionContext, create_context


P = "org.eclipse.elk."


def graph_input():
    return {"id": "root", "$H": False,
            "business": {"error": {"stack": "caller-stack"}, "$H": 0, "optional": None},
            "children": [{"id": "a", "width": 10, "height": 5}, {"id": "b", "width": 3, "height": 0}],
            "edges": [{"id": "edge", "sources": ["a"], "targets": ["b"]}]}


class IndependentContextCases(unittest.TestCase):
    def test_two_contexts_never_share_working_graph_state_or_caller_snapshots(self):
        graph = graph_input()
        constructor = {"defaultLayoutOptions": {"elk.direction": "DOWN"}}
        args = {"layoutOptions": {"elk.randomSeed": 7}, "logging": False}
        originals = copy.deepcopy((graph, constructor, args))
        first = ExecutionContext.create(graph, constructor=constructor, layout_arguments=args)
        second = create_context(graph, constructor=constructor, layout_arguments=args)
        self.assertIsNot(first.working_graph, second.working_graph)
        self.assertIsNot(first.state, second.state)
        self.assertIsNot(first.resolved_options, second.resolved_options)
        first.working_graph.node("a").set_property("x", 42)
        first.working_graph.root.set_property("business", {"error": {"stack": "work"}})
        first.state["temporary_mapping"] = {"a": ["dummy-node"]}
        self.assertNotIn("x", second.working_graph.node("a").to_json())
        self.assertEqual(second.working_graph.to_json()["business"]["error"]["stack"], "caller-stack")
        self.assertEqual(second.state, {})
        self.assertEqual((graph, constructor, args), originals)

    def test_snapshots_are_copied_on_every_access_and_preserve_exact_input(self):
        graph = graph_input()
        constructor = {"defaultLayoutOptions": {"elk.direction": "LEFT"}}
        args = {"layoutOptions": {}, "logging": False}
        context = create_context(graph, constructor=constructor, layout_arguments=args)
        self.assertEqual(context.original_graph, graph)
        self.assertEqual(context.original_constructor, constructor)
        self.assertEqual(context.original_arguments, args)
        context.original_graph["business"]["error"]["stack"] = "snapshot-mutation"
        context.original_constructor["defaultLayoutOptions"]["elk.direction"] = "UP"
        context.original_arguments["layoutOptions"]["elk.direction"] = "DOWN"
        self.assertEqual(context.original_graph["business"]["error"]["stack"], "caller-stack")
        self.assertEqual(context.original_constructor, constructor)
        self.assertEqual(context.original_arguments, args)
        graph["business"]["optional"] = False
        constructor["defaultLayoutOptions"].clear()
        args["layoutOptions"]["elk.direction"] = "RIGHT"
        self.assertIsNone(context.original_graph["business"]["optional"])
        self.assertEqual(context.original_constructor["defaultLayoutOptions"], {"elk.direction": "LEFT"})
        self.assertEqual(context.original_arguments["layoutOptions"], {})

    def test_context_selected_global_and_root_local_follow_one_precedence_chain(self):
        graph = graph_input()
        graph["layoutOptions"] = {"elk.direction": "RIGHT"}
        context = create_context(graph, constructor={"defaultLayoutOptions": {"elk.direction": "DOWN", "elk.spacing.nodeNode": 99}},
                                 layout_arguments={"layoutOptions": {"elk.direction": "LEFT"}})
        resolved = context.resolved_options
        self.assertEqual(resolved.selected_global, "call")
        self.assertEqual(resolved.values[P + "direction"], "RIGHT")
        self.assertEqual(resolved.origins[P + "direction"], "local")
        self.assertEqual(resolved.values[P + "spacing.nodeNode"], 20)
        self.assertEqual(graph["layoutOptions"], {"elk.direction": "RIGHT"})

    def test_context_preserves_zero_seed_without_claiming_random_stream(self):
        first = create_context(graph_input(), layout_arguments={"layoutOptions": {"elk.randomSeed": 0}})
        second = create_context(graph_input(), layout_arguments={"layoutOptions": {"elk.randomSeed": 7}})
        self.assertEqual(first.seed, 0)
        self.assertIs(type(first.seed), int)
        self.assertEqual(second.seed, 7)
        first.state["seed_work"] = [1, 2]
        self.assertEqual(second.state, {})

    def test_any_explicit_worker_key_is_unsupported_even_when_falsy(self):
        for name in ("workerUrl", "workerFactory"):
            for value in (None, "", False, 0):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(UnsupportedFeatureError) as caught:
                        create_context(graph_input(), constructor={name: value})
                    self.assertEqual(caught.exception.path, "/constructor/" + name)

    def test_algorithm_registration_filter_is_not_silently_ignored(self):
        for algorithms in ([], ["stress"], "layered", [1], [False]):
            with self.subTest(algorithms=algorithms):
                with self.assertRaises(ValidationError):
                    create_context(graph_input(), constructor={"algorithms": algorithms})
        context = create_context(graph_input(), constructor={"algorithms": ["layered"]})
        self.assertEqual(context.resolved_options.values[P + "algorithm"], P + "layered")
        self.assertEqual(context.original_constructor, {"algorithms": ["layered"]})

    def test_invalid_call_does_not_pollute_later_valid_context(self):
        graph = graph_input()
        before = copy.deepcopy(graph)
        with self.assertRaises(ValidationError):
            create_context(graph, layout_arguments={"layoutOptions": {"vendor.notAnElkOption": 9}})
        context = create_context(graph)
        self.assertEqual(context.state, {})
        self.assertEqual(context.working_graph.to_json(), before)
        self.assertEqual(graph, before)
        self.assertEqual(context.resolved_options.values[P + "direction"], "UNDEFINED")

    def test_working_export_and_business_keys_are_isolated_from_context_input(self):
        graph = graph_input()
        context = create_context(graph)
        exported = context.working_graph.to_json()
        exported["$H"] = 0
        exported["business"]["$H"] = False
        exported["business"]["error"]["stack"] = "changed"
        exported["children"].reverse()
        original = context.original_graph
        self.assertIs(original["$H"], False)
        self.assertIs(type(original["business"]["$H"]), int)
        self.assertEqual(original["business"]["error"]["stack"], "caller-stack")
        self.assertEqual([n.id for n in context.working_graph.nodes], ["root", "a", "b"])
        self.assertNotIn("x", context.working_graph.node("a").to_json())


if __name__ == "__main__":
    unittest.main()
