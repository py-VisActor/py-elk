"""Owner tests for host data ownership, order and validation invariants."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pyelk._errors import ModelValidationError
from pyelk.model import Anchor, Graph, Margin, TypedId


def encoded(value):
    # JSON formatting here checks value types/order, not original request bytes.
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def sample():
    return {
        "business": {"$H": False, "error": {"stack": "caller-stack"}, "null": None},
        "id": "root",
        "children": [
            {"id": 1, "width": 0, "height": 5.0, "ports": [{"id": "p", "width": 0}],
             "children": [{"id": "nested", "height": -0.0}],
             "edges": [{"id": "local", "sources": ["p"], "targets": ["nested"]}]},
            {"id": "1", "width": 2, "labels": [{"text": "未命名", "width": 3}]},
        ],
        "edges": [{"id": "global", "sources": [1, "p"], "targets": ["1", "nested"],
                   "sections": [{"id": "s1", "startPoint": {"x": -1, "y": 0},
                                 "endPoint": {"x": 2, "y": 3}, "bendPoints": []}]}],
    }


class OrderedModelTests(unittest.TestCase):
    def assert_error(self, raw, code, path):
        with self.assertRaises(ModelValidationError) as raised:
            Graph.from_json(raw)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(raised.exception.path, path)

    def test_round_trip_preserves_every_field_type_and_container_order(self):
        raw = sample()
        before = encoded(raw)
        graph = Graph.from_json(raw)
        self.assertEqual(encoded(graph.to_json()), before)
        self.assertEqual(encoded(raw), before)
        self.assertNotIn("x", graph.root.to_json())
        self.assertNotIn("width", graph.root.to_json())

    def test_all_valid_project_request_graphs_round_trip(self):
        paths = sorted((ROOT / "tests/fixtures/validation/requests").glob("*.json"))
        checked = 0
        for path in paths:
            request = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(request.get("graph"), dict) or path.stem == "error-unknown-endpoint":
                continue
            with self.subTest(request=path.name):
                raw = request["graph"]
                before = encoded(raw)
                self.assertEqual(encoded(Graph.from_json(raw).to_json()), before)
                self.assertEqual(encoded(raw), before)
                checked += 1
        self.assertGreaterEqual(checked, 20)

    def test_nodes_ports_edges_and_indexes_have_declared_order(self):
        graph = Graph.from_json(sample())
        self.assertEqual([n.id for n in graph.nodes], ["root", 1, "nested", "1"])
        self.assertEqual([p.id for p in graph.ports], ["p"])
        self.assertEqual([e.id for e in graph.edges], ["global", "local"])
        self.assertEqual(list(graph.node_index), [TypedId.from_value(n.id) for n in graph.nodes])
        self.assertEqual(graph.root.children, (graph.node(1), graph.node("1")))
        self.assertIsNone(graph.root.parent)
        self.assertIs(graph.node("nested").parent, graph.node(1))
        self.assertIs(graph.port("p").owner, graph.node(1))
        self.assertIs(graph.edge("local").owner, graph.node(1))
        self.assertEqual(graph.edge("global").sources, (1, "p"))
        self.assertEqual(graph.edge("global").source_endpoints, (graph.node(1), graph.port("p")))
        self.assertEqual(graph.edge("global").target_endpoints, (graph.node("1"), graph.node("nested")))

    def test_input_output_element_and_second_graph_are_independent(self):
        raw = sample()
        first = Graph.from_json(raw)
        second = Graph.from_json(raw)
        original = encoded(raw)
        raw["business"]["$H"] = 5
        raw["children"][0]["width"] = 99
        self.assertEqual(encoded(first.to_json()), original)
        exported = first.to_json()
        exported["children"][0]["ports"][0]["width"] = 20
        node_export = first.node(1).to_json()
        node_export["children"][0]["height"] = 900
        first.node(1).set_property("width", 1e-12)
        first.port("p").set_property("business", {"nested": []})
        self.assertEqual(first.node(1).to_json()["width"], 1e-12)
        self.assertEqual(first.port("p").to_json()["width"], 0)
        self.assertEqual(encoded(second.to_json()), original)

    def test_set_property_clones_and_preserves_exact_small_changes(self):
        graph = Graph.from_json({"id": "root", "width": 0})
        new_value = {"array": [False, None, {"$H": 0, "error": {"stack": "business"}}]}
        graph.root.set_property("business", new_value)
        new_value["array"].clear()
        self.assertEqual(len(graph.to_json()["business"]["array"]), 3)
        graph.root.set_property("width", 1e-14)
        self.assertEqual(graph.to_json()["width"], 1e-14)
        self.assertEqual(list(graph.to_json()), ["id", "width", "business"])

    def test_set_property_rejects_structure_and_is_atomic(self):
        graph = Graph.from_json(sample())
        before = encoded(graph.to_json())
        for element in (graph.root, graph.port("p"), graph.edge("global")):
            for key in ("id", "children", "ports", "edges", "labels", "sources", "targets", "sections"):
                with self.subTest(element=element.path, key=key):
                    with self.assertRaises(ModelValidationError) as raised:
                        element.set_property(key, [])
                    self.assertEqual(raised.exception.code, "STRUCTURAL_MUTATION")
        for value in (-1, True, None, float("nan")):
            with self.assertRaises(ModelValidationError):
                graph.node(1).set_property("width", value)
        with self.assertRaises(ModelValidationError) as raised:
            graph.root.set_property("a/b~c", {"value": float("inf")})
        self.assertEqual(raised.exception.path, "/a~1b~0c/value")
        with self.assertRaises(ModelValidationError) as raised:
            graph.edge("global").set_property("junctionPoints", [{"x": False, "y": 0}])
        self.assertEqual(raised.exception.path, "/edges/0/junctionPoints/0/x")
        self.assertEqual(encoded(graph.to_json()), before)

    def test_identity_and_indexes_cannot_be_replaced_by_public_fields(self):
        graph = Graph.from_json(sample())
        with self.assertRaises(TypeError):
            graph.node_index[TypedId("string", "new")] = graph.root
        with self.assertRaises(AttributeError):
            graph.root.id = "changed"
        with self.assertRaises(AttributeError):
            graph.nodes = ()
        with self.assertRaises(KeyError):
            graph.node("missing")

    def test_typed_ids_preserve_integer_string_empty_and_large_integer(self):
        huge = 10 ** 100
        graph = Graph.from_json({"id": "", "children": [{"id": 0}, {"id": "0"}, {"id": huge}]})
        self.assertIsNot(graph.node(0), graph.node("0"))
        self.assertEqual(graph.node(huge).id, huge)
        self.assertEqual(graph.root.id, "")
        self.assertNotEqual(TypedId.from_value(0), TypedId.from_value("0"))
        for value in (False, True, 1.0, None, [], {}):
            with self.subTest(value=value):
                self.assert_error({"id": value}, "INVALID_ID", "/id")
        with self.assertRaises(ModelValidationError):
            TypedId("integer", False)
        with self.assertRaises(ModelValidationError):
            TypedId("string", 1)

    def test_global_duplicates_include_root_ports_and_edges(self):
        cases = [
            ({"id": "r", "children": [{"id": "r"}]}, "/children/0/id"),
            ({"id": "r", "ports": [{"id": "r"}]}, "/ports/0/id"),
            ({"id": "r", "edges": [{"id": "r", "sources": ["r"], "targets": ["r"]}]}, "/edges/0/id"),
            ({"id": "r", "children": [{"id": "n", "ports": [{"id": "p"}]},
                                       {"id": "p"}]}, "/children/1/id"),
        ]
        for raw, path in cases:
            with self.subTest(path=path):
                self.assert_error(raw, "DUPLICATE_ID", path)

    def test_dimensions_are_explicit_finite_nonnegative_and_not_boolean(self):
        for value in (None, False, "2", -0.001, float("inf"), float("nan")):
            with self.subTest(value=value):
                code = "INVALID_JSON" if type(value) is float and value != value or value == float("inf") else "INVALID_NUMBER"
                self.assert_error({"id": "r", "children": [{"id": "n", "width": value}]}, code, "/children/0/width")
        self.assert_error({"id": "r", "ports": [{"id": "p", "height": -1}]}, "INVALID_NUMBER", "/ports/0/height")
        self.assert_error({"id": "r", "labels": [{"height": True}]}, "INVALID_NUMBER", "/labels/0/height")

    def test_missing_null_and_empty_core_containers_are_distinct(self):
        for key in ("children", "ports", "edges", "labels"):
            with self.subTest(key=key):
                self.assert_error({"id": "r", key: None}, "INVALID_CONTAINER", "/" + key)
                raw = {"id": "r", key: []}
                self.assertEqual(encoded(Graph.from_json(raw).to_json()), encoded(raw))
        self.assertEqual(Graph.from_json({"id": "r"}).to_json(), {"id": "r"})

    def test_edge_endpoints_have_explicit_types_and_paths(self):
        for key in ("sources", "targets"):
            for value, code, suffix in [([], "MISSING_ENDPOINT", ""),
                                         (None, "INVALID_CONTAINER", ""),
                                         ([False], "INVALID_ID", "/0"),
                                         (["missing"], "UNKNOWN_ENDPOINT", "/0")]:
                edge = {"id": "e", "sources": ["r"], "targets": ["r"]}
                edge[key] = value
                with self.subTest(key=key, value=value):
                    self.assert_error({"id": "r", "edges": [edge]}, code, "/edges/0/" + key + suffix)
        self.assert_error({"id": "r", "edges": [{"id": "e", "source": "r", "target": "r"}]},
                          "UNSUPPORTED_EDGE", "/edges/0")
        # Edge IDs never become connectable shapes.
        self.assert_error({"id": "r", "edges": [{"id": "e", "sources": ["e"], "targets": ["r"]}]},
                          "UNKNOWN_ENDPOINT", "/edges/0/sources/0")

    def test_labels_optional_identity_is_not_endpoint_identity(self):
        raw = {"id": "r", "labels": [{"id": "r"}, {"text": "anonymous"}]}
        self.assertEqual(Graph.from_json(raw).to_json(), raw)
        self.assert_error({"id": "r", "labels": [{"id": False}]}, "INVALID_ID", "/labels/0/id")
        raw["edges"] = [{"id": "e", "sources": ["anonymous"], "targets": ["r"]}]
        self.assert_error(raw, "UNKNOWN_ENDPOINT", "/edges/0/sources/0")

    def test_sections_and_points_preserve_values_but_validate_declared_types(self):
        raw = sample()
        section = raw["edges"][0]["sections"][0]
        section["incomingSections"] = [3, "unknown-topology-not-resolved"]
        section["business"] = {"startPoint": None, "sections": False}
        self.assertEqual(encoded(Graph.from_json(raw).to_json()), encoded(raw))
        section["startPoint"]["x"] = False
        self.assert_error(raw, "INVALID_NUMBER", "/edges/0/sections/0/startPoint/x")
        for value in (None, {}, [None]):
            bad = sample()
            bad["edges"][0]["sections"] = value
            expected = "/edges/0/sections/0" if value == [None] else "/edges/0/sections"
            self.assert_error(bad, "INVALID_ELEMENT" if value == [None] else "INVALID_CONTAINER", expected)
        bad = sample()
        bad["edges"][0]["sections"][0]["incomingSections"] = None
        self.assert_error(bad, "INVALID_CONTAINER", "/edges/0/sections/0/incomingSections")

    def test_layout_option_container_check_does_not_resolve_values(self):
        placements = [
            (lambda raw: raw, "/layoutOptions"),
            (lambda raw: raw["children"][0], "/children/0/layoutOptions"),
            (lambda raw: raw["children"][0]["ports"][0], "/children/0/ports/0/layoutOptions"),
            (lambda raw: raw["children"][1]["labels"][0], "/children/1/labels/0/layoutOptions"),
            (lambda raw: raw["edges"][0], "/edges/0/layoutOptions"),
            (lambda raw: raw["edges"][0]["sections"][0], "/edges/0/sections/0/layoutOptions"),
        ]
        for place, path in placements:
            for invalid in (None, False, 0, ""):
                with self.subTest(path=path, invalid=invalid):
                    raw = sample()
                    place(raw)["layoutOptions"] = invalid
                    self.assert_error(raw, "INVALID_CONTAINER", path)
            raw = sample()
            place(raw)["layoutOptions"] = {"unknown-option": None, "elk.algorithm": False}
            self.assertEqual(encoded(Graph.from_json(raw).to_json()), encoded(raw))
        graph = Graph.from_json(sample())
        before = encoded(graph.to_json())
        for element in (graph.root, graph.port("p"), graph.edge("global")):
            with self.assertRaises(ModelValidationError):
                element.set_property("layoutOptions", None)
        self.assertEqual(encoded(graph.to_json()), before)

    def test_input_requires_json_and_owned_repeated_references(self):
        self.assert_error([], "INVALID_GRAPH", "")
        self.assert_error({}, "MISSING_ID", "/id")
        self.assert_error({"id": "r", "data": (1, 2)}, "INVALID_JSON", "/data")
        self.assert_error({"id": "r", "data": {3: "bad"}}, "INVALID_JSON", "/data")
        cycle = {}; cycle["self"] = cycle
        self.assert_error({"id": "r", "data": cycle}, "INVALID_JSON", "/data/self")
        shared = {"items": []}
        graph = Graph.from_json({"id": "r", "a": shared, "b": shared})
        result = graph.to_json()
        result["a"]["items"].append(1)
        self.assertEqual(result["b"]["items"], [])

    def test_anchor_margin_are_internal_and_validate_finite_numbers(self):
        anchor = Anchor(x=-2, y=0)
        margin = Margin(top=1, right=2, bottom=3, left=4)
        self.assertEqual((anchor.x, anchor.y), (-2, 0))
        self.assertEqual((margin.top, margin.right, margin.bottom, margin.left), (1, 2, 3, 4))
        with self.assertRaises(TypeError):
            Margin(1, 2, 3, 4)
        with self.assertRaises(ModelValidationError):
            Anchor(x=True, y=0)
        with self.assertRaises(ModelValidationError):
            Margin(left=-1)
        self.assertEqual(Graph.from_json({"id": "r"}).to_json(), {"id": "r"})


if __name__ == "__main__":
    unittest.main()
