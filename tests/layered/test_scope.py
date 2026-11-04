"""Frozen historical E04 admission boundaries; E05 has its own public controls."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk._errors import ValidationError
from pyelk.execution import create_context
from pyelk.algorithms.layered.scope import validate_e04_slice as validate_slice


def path_graph(count=3):
    return {"id": "root", "children": [{"id": str(i), "width": 20 + i, "height": 10} for i in range(count)],
            "edges": [{"id": "e" + str(i), "sources": [str(i)], "targets": [str(i + 1)]} for i in range(count - 1)]}


class SliceAdmissionTests(unittest.TestCase):
    def reject(self, graph, constructor=None, arguments=None):
        before = copy.deepcopy(graph)
        with self.assertRaises(ValidationError):
            validate_slice(create_context(graph, constructor=constructor, layout_arguments=arguments))
        self.assertEqual(graph, before)

    def test_zero_to_four_nodes_and_arbitrary_input_order(self):
        for count in range(5):
            graph = path_graph(count)
            graph["children"].reverse()
            graph["edges"].reverse()
            checked = validate_slice(create_context(graph))
            self.assertEqual(checked.node_count, count)
        self.reject(path_graph(5))

    def test_cycles_parallel_fork_disconnected_and_root_endpoint_rejected(self):
        for edges in ([{"id": "a", "sources": ["0"], "targets": ["1"]}, {"id": "b", "sources": ["1"], "targets": ["0"]}],
                      [{"id": "a", "sources": ["0"], "targets": ["1"]}, {"id": "b", "sources": ["0"], "targets": ["1"]}],
                      [{"id": "a", "sources": ["0"], "targets": ["1"]}, {"id": "b", "sources": ["0"], "targets": ["2"]}],
                      [], [{"id": "a", "sources": ["root"], "targets": ["1"]}]):
            graph = path_graph()
            graph["edges"] = edges
            self.reject(graph)

    def test_explicit_label_port_compound_and_local_options_rejected(self):
        for key, value in (("labels", [{"text": "label"}]), ("ports", [{"id": "p"}]),
                           ("children", [{"id": "nested"}]), ("layoutOptions", {"elk.direction": "RIGHT"})):
            graph = path_graph()
            graph["children"][0][key] = value
            self.reject(graph)

    def test_preexisting_geometry_and_legacy_options_do_not_enter_wrong_branch(self):
        for key, value in (("x", 0), ("y", 0), ("width", 0), ("height", 0), ("properties", {})):
            graph = path_graph()
            graph[key] = value
            self.reject(graph)
        graph = path_graph()
        graph["children"][0]["x"] = 0
        self.reject(graph)
        graph = path_graph()
        graph["edges"][0]["sections"] = [{"id": "old", "startPoint": {"x": 0, "y": 0}, "endPoint": {"x": 1, "y": 0}}]
        self.reject(graph)

    def test_numeric_limits_zero_and_nondeterministic_seed(self):
        graph = path_graph()
        graph["children"][0].update(width=0, height=0)
        self.assertEqual(validate_slice(create_context(graph)).node_count, 3)
        graph["children"][0]["width"] = 1_000_001
        self.reject(graph)
        for options in ({"elk.randomSeed": 0}, {"elk.spacing.nodeNode": 1_000_001},
                        {"elk.layered.spacing.nodeNodeBetweenLayers": 1_000_001},
                        {"elk.padding": {"top": 1_000_001, "right": 0, "bottom": 0, "left": 0}}):
            self.reject(path_graph(), arguments={"layoutOptions": options})

    def test_direction_component_logging_and_registration_guard(self):
        for arguments in ({"layoutOptions": {"elk.direction": "DOWN"}},
                          {"layoutOptions": {"elk.separateConnectedComponents": False}},
                          {"logging": True}, {"measureExecutionTime": True}, {"logging": 0}, {"unreviewed": False}):
            self.reject(path_graph(), arguments=arguments)
        self.reject(path_graph(), constructor={"algorithms": ["layered", "stress"]})
        self.reject(path_graph(), constructor={"workerUrl": None})

    def test_business_fields_are_opaque_and_callers_unchanged(self):
        graph = path_graph()
        graph["business"] = {"properties": None, "error": {"stack": "caller"}, "$H": False}
        original = copy.deepcopy(graph)
        validate_slice(create_context(graph, layout_arguments={"logging": False, "measureExecutionTime": False}))
        self.assertEqual(graph, original)

    def test_reference_log_cleanup_and_existing_cache_are_explicitly_outside_slice(self):
        for key, value in (("logging", {}), ("$H", 0), ("$H", "user-cache")):
            graph = path_graph()
            graph[key] = value
            self.reject(graph)
        graph = path_graph()
        graph["children"][0]["$H"] = False
        self.reject(graph)

    def test_all_existing_edge_geometry_keys_are_rejected_by_presence(self):
        for key, value in (("sections", []), ("junctionPoints", []), ("bendPoints", []),
                           ("startPoint", {"x": 0, "y": 0}), ("endPoint", {"x": 0, "y": 0}), ("container", "root")):
            graph = path_graph()
            graph["edges"][0][key] = value
            self.reject(graph)

    def test_object_padding_is_only_an_internal_parser_convenience(self):
        padding = {"top": 12, "right": 12, "bottom": 12, "left": 12}
        self.reject(path_graph(), arguments={"layoutOptions": {"elk.padding": padding}})
        accepted = create_context(path_graph(), layout_arguments={"layoutOptions": {"elk.padding": "[top=12,right=12,bottom=12,left=12]"}})
        self.assertEqual(validate_slice(accepted).node_count, 3)


if __name__ == "__main__":
    unittest.main()
