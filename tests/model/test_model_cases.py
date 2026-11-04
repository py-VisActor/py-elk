"""Independent E03 host-model invariants; no layout algorithm is exercised.

Expected cases were prepared before implementation, then scoped by ADR-0002.
Integer identities here do not expand E02's string-only comparison profile.
"""
import copy
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pyelk._errors import ModelValidationError
from pyelk.model import Anchor, Graph, Margin, TypedId


def simple_graph():
    return {"id": "root", "children": [{"id": 2, "width": 10, "height": 0},
                                         {"id": "2", "width": 0, "height": 5}],
            "edges": [{"id": "edge", "sources": [2], "targets": ["2"]}]}


class IndependentModelCases(unittest.TestCase):
    def assert_json_exact(self, actual, expected):
        self.assertIs(type(actual), type(expected))
        if isinstance(expected, dict):
            self.assertEqual(list(actual), list(expected))
            for key in expected:
                self.assert_json_exact(actual[key], expected[key])
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for a, b in zip(actual, expected):
                self.assert_json_exact(a, b)
        else:
            self.assertEqual(actual, expected)
            if type(expected) is float and expected == 0:
                self.assertEqual(math.copysign(1, actual), math.copysign(1, expected))

    def rejects(self, value, path):
        before = copy.deepcopy(value)
        with self.assertRaises(ModelValidationError) as caught:
            Graph.from_json(value)
        self.assertEqual(caught.exception.path, path)
        self.assertIsInstance(caught.exception.code, str)
        self.assertTrue(caught.exception.code)
        # Invalid NaN is not equal to itself, so compare that input separately.
        if not any(type(v) is float and math.isnan(v) for v in self._leaves(before)):
            self.assert_json_exact(value, before)

    @classmethod
    def _leaves(cls, value):
        if isinstance(value, dict):
            for item in value.values():
                yield from cls._leaves(item)
        elif isinstance(value, list):
            for item in value:
                yield from cls._leaves(item)
        else:
            yield value

    def test_exact_roundtrip_retains_business_keys_order_and_no_geometry(self):
        graph = simple_graph()
        graph["$H"] = 0
        graph["business"] = {"$H": False, "error": {"stack": "caller-stack"},
                             "none": None, "empty": [], "flags": [False, 0, None, ""]}
        graph["children"][0]["business"] = {"$H": None}
        graph["edges"][0]["business"] = {"$H": "edge-hash"}
        before = copy.deepcopy(graph)
        model = Graph.from_json(graph)
        self.assert_json_exact(model.to_json(), before)
        self.assert_json_exact(graph, before)
        self.assertNotIn("x", model.root.to_json())
        self.assertNotIn("sections", model.edge("edge").to_json())

    def test_typed_integer_and_string_indexes_do_not_merge_or_sort(self):
        graph = simple_graph()
        graph["children"].extend([{"id": 0}, {"id": ""}])
        model = Graph.from_json(graph)
        self.assertEqual([node.id for node in model.nodes], ["root", 2, "2", 0, ""])
        self.assertIsNot(model.node(2), model.node("2"))
        self.assertIs(model.node_index[TypedId("integer", 2)], model.node(2))
        self.assertIs(model.node_index[TypedId("string", "2")], model.node("2"))
        self.assertIs(model.edge("edge").source_endpoints[0], model.node(2))
        self.assertIs(model.edge("edge").target_endpoints[0], model.node("2"))
        with self.assertRaises(TypeError):
            model.node_index[TypedId("integer", 4)] = model.node(2)

    def test_invalid_identity_types_never_alias_integer(self):
        for bad in (True, False, 1.0, None, [], {}):
            with self.subTest(bad=bad):
                graph = simple_graph()
                graph["children"][1]["id"] = bad
                self.rejects(graph, "/children/1/id")
                with self.assertRaises(ModelValidationError):
                    TypedId.from_value(bad)
        with self.assertRaises(ModelValidationError):
            TypedId("integer", True)
        with self.assertRaises(ModelValidationError):
            TypedId("string", 2)

    def test_missing_identity_and_duplicate_global_typed_identity_have_paths(self):
        self.rejects({}, "/id")
        graph = simple_graph()
        del graph["children"][1]["id"]
        self.rejects(graph, "/children/1/id")
        for placement, expected_path in (("node", "/children/1/id"),
                                         ("port", "/children/0/ports/0/id"),
                                         ("edge", "/edges/0/id")):
            with self.subTest(placement=placement):
                graph = simple_graph()
                if placement == "node":
                    graph["children"][1]["id"] = 2
                elif placement == "port":
                    graph["children"][0]["ports"] = [{"id": 2}]
                else:
                    graph["edges"][0]["id"] = 2
                self.rejects(graph, expected_path)

    def test_unknown_lookup_is_distinct_from_invalid_identity(self):
        model = Graph.from_json(simple_graph())
        with self.assertRaises(KeyError):
            model.node("missing")
        with self.assertRaises(ModelValidationError):
            model.node(False)

    def test_endpoint_identity_and_bad_reference_paths(self):
        for endpoint, expected_path in (("missing", "/edges/0/targets/0"),
                                        (False, "/edges/0/targets/0")):
            graph = simple_graph()
            graph["edges"][0]["targets"] = [endpoint]
            self.rejects(graph, expected_path)
        graph = simple_graph()
        graph["edges"][0]["targets"] = []
        self.rejects(graph, "/edges/0/targets")
        graph = simple_graph()
        graph["edges"][0]["sources"] = None
        self.rejects(graph, "/edges/0/sources")

    def test_dimensions_reject_invalid_values_without_changing_input(self):
        for bad in (-1, -1e-300, float("inf"), float("-inf"), float("nan"), True, "10", None):
            with self.subTest(bad=bad):
                graph = simple_graph()
                graph["children"][0]["width"] = bad
                self.rejects(graph, "/children/0/width")

    def test_missing_dimensions_zero_signed_zero_and_tiny_values_are_lossless(self):
        graph = {"id": "root", "children": [{"id": "a"}, {"id": "b", "width": -0.0, "height": 5e-324}]}
        result = Graph.from_json(graph).to_json()
        self.assert_json_exact(result, graph)
        self.assertNotIn("width", result["children"][0])
        self.assertNotIn("height", result["children"][0])

    def test_absent_and_empty_collections_stay_distinct_from_null(self):
        self.assert_json_exact(Graph.from_json({"id": "root"}).to_json(), {"id": "root"})
        graph = {"id": "root", "children": [], "ports": [], "labels": [], "edges": [], "layoutOptions": {}}
        self.assert_json_exact(Graph.from_json(graph).to_json(), graph)
        for field in ("children", "ports", "labels", "edges", "layoutOptions"):
            self.rejects({"id": "root", field: None}, "/" + field)

    def test_option_containers_validate_on_every_element_without_parsing_contents(self):
        # Root clarified this schema boundary after V's original null control.
        for place in ("root", "child", "port", "edge", "label"):
            for invalid in (None, False, 0, ""):
                graph = simple_graph()
                graph["children"][0]["ports"] = [{"id": "port"}]
                graph["labels"] = [{"text": "label"}]
                element, path = {
                    "root": (graph, ""),
                    "child": (graph["children"][0], "/children/0"),
                    "port": (graph["children"][0]["ports"][0], "/children/0/ports/0"),
                    "edge": (graph["edges"][0], "/edges/0"),
                    "label": (graph["labels"][0], "/labels/0"),
                }[place]
                element["layoutOptions"] = invalid
                with self.subTest(place=place, invalid=invalid):
                    self.rejects(graph, path + "/layoutOptions")
        graph = {"id": "root", "layoutOptions": {"vendor.notAnElkOption": None}}
        self.assert_json_exact(Graph.from_json(graph).to_json(), graph)
        model = Graph.from_json({"id": "root", "children": [{"id": "a", "ports": [{"id": "p"}]}],
                                 "edges": [{"id": "e", "sources": ["a"], "targets": ["p"]}]})
        before = model.to_json()
        for element in (model.root, model.node("a"), model.port("p"), model.edge("e")):
            for invalid in (None, False, 0, ""):
                with self.subTest(element=element.id, invalid=invalid):
                    with self.assertRaises(ModelValidationError):
                        element.set_property("layoutOptions", invalid)
                    self.assert_json_exact(model.to_json(), before)

    def test_nested_ports_labels_and_hyperedges_are_data_carriers(self):
        graph = {"id": "root", "children": [{"id": "b", "ports": [{"id": "pb", "width": 0}],
                                               "children": [{"id": "nested"}],
                                               "edges": [{"id": "inner", "sources": ["pb"], "targets": ["nested"]}]},
                                              {"id": "a", "labels": [{"id": "b", "text": "business", "width": 1, "height": 2}]}],
                 "edges": [{"id": "z", "sources": ["b", "pb"], "targets": ["a", "nested"]},
                           {"id": "y", "sources": ["a"], "targets": ["b"]}]}
        model = Graph.from_json(graph)
        self.assert_json_exact(model.to_json(), graph)
        self.assertEqual([n.id for n in model.nodes], ["root", "b", "nested", "a"])
        self.assertEqual([e.id for e in model.edges], ["z", "y", "inner"])
        self.assertEqual([p.id for p in model.ports], ["pb"])
        self.assertIs(model.node("nested").parent, model.node("b"))
        self.assertIs(model.port("pb").owner, model.node("b"))
        self.assertEqual(model.edge("z").sources, ("b", "pb"))
        self.assertIs(model.edge("z").source_endpoints[1], model.port("pb"))
        self.assertNotIn("x", model.to_json())

    def test_primitive_edge_is_explicitly_rejected(self):
        graph = {"id": "root", "children": [{"id": "a"}, {"id": "b"}],
                 "edges": [{"id": "e", "source": "a", "target": "b"}]}
        with self.assertRaises(ModelValidationError) as caught:
            Graph.from_json(graph)
        self.assertTrue(caught.exception.path.startswith("/edges/0"))

    def test_import_export_and_set_property_have_independent_ownership(self):
        graph = simple_graph()
        graph["business"] = {"list": [{"value": 1}]}
        expected = copy.deepcopy(graph)
        model = Graph.from_json(graph)
        graph["business"]["list"][0]["value"] = 9
        self.assert_json_exact(model.to_json(), expected)
        first = model.to_json()
        first["children"][0]["width"] = 300
        first["business"]["list"].append({"value": 2})
        self.assert_json_exact(model.to_json(), expected)
        supplied = {"nested": [False, 0]}
        model.node(2).set_property("business", supplied)
        supplied["nested"].append("external")
        self.assertEqual(model.node(2).to_json()["business"], {"nested": [False, 0]})
        self.assertNotIn("business", expected["children"][0])
        exported_node = model.node(2).to_json()
        exported_node["business"]["nested"].append("export")
        self.assertEqual(model.node(2).to_json()["business"], {"nested": [False, 0]})

    def test_set_property_rejects_structural_mutation_and_invalid_geometry_atomically(self):
        model = Graph.from_json(simple_graph())
        original = model.to_json()
        for element, key, value in ((model.node(2), "id", "changed"),
                                     (model.node(2), "children", []),
                                     (model.edge("edge"), "sources", ["2"]),
                                     (model.node(2), "width", -1)):
            with self.subTest(key=key):
                with self.assertRaises(ModelValidationError):
                    element.set_property(key, value)
                self.assert_json_exact(model.to_json(), original)

    def test_json_business_errors_have_escaped_pointer_and_no_lossy_conversion(self):
        for invalid in (float("inf"), (1, 2), object()):
            graph = {"id": "root", "a/b~c": {"value": invalid}}
            with self.assertRaises(ModelValidationError) as caught:
                Graph.from_json(graph)
            self.assertEqual(caught.exception.path, "/a~1b~0c/value")
        with self.assertRaises(ModelValidationError):
            Graph.from_json({"id": "root", "business": {1: "not-a-json-key"}})

    def test_shared_business_references_are_copied_not_treated_as_cycles(self):
        shared = {"list": [1]}
        model = Graph.from_json({"id": "root", "first": shared, "second": shared})
        shared["list"].append(2)
        result = model.to_json()
        self.assertEqual(result["first"], {"list": [1]})
        result["first"]["list"].append(3)
        self.assertEqual(result["second"], {"list": [1]})
        cyclic = {"id": "root"}
        cyclic["business"] = cyclic
        with self.assertRaises(ModelValidationError) as caught:
            Graph.from_json(cyclic)
        self.assertEqual(caught.exception.path, "/business")

    def test_anchor_and_margin_are_validated_without_export_injection(self):
        anchor = Anchor(x=-1.5, y=0)
        margin = Margin(top=1, right=2, bottom=3, left=4)
        self.assertEqual((anchor.x, anchor.y), (-1.5, 0))
        self.assertEqual((margin.top, margin.right, margin.bottom, margin.left), (1, 2, 3, 4))
        for kwargs in ({"x": True, "y": 0}, {"x": 0, "y": float("inf")}):
            with self.assertRaises(ModelValidationError):
                Anchor(**kwargs)
        with self.assertRaises(ModelValidationError):
            Margin(top=0, right=-1, bottom=0, left=0)
        self.assertEqual(Graph.from_json({"id": "root"}).to_json(), {"id": "root"})


if __name__ == "__main__":
    unittest.main()
