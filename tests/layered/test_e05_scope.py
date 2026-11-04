"""E05 host admission controls; accepting a structure never fabricates layout."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk._errors import ValidationError
from pyelk.execution import create_context
from pyelk.algorithms.layered.scope import validate_e04_slice, validate_e05_slice


def dag(count=8):
    return {"id": "root", "children": [{"id": str(i), "width": 10 + i, "height": 20} for i in range(count)],
            "edges": [{"id": str(i) + "-" + str(j), "sources": [str(i)], "targets": [str(j)]}
                      for i in range(count) for j in range(i + 1, count)]}


class DagAdmissionTests(unittest.TestCase):
    def test_eight_original_node_dense_dag_is_structurally_accepted_without_computing_ranks(self):
        original = dag()
        before = copy.deepcopy(original)
        context = create_context(original)
        admitted = validate_e05_slice(context)
        self.assertEqual((admitted.node_count, admitted.edge_count), (8, 28))
        self.assertEqual(original, before)
        self.assertEqual(context.working_graph.to_json(), before)
        with self.assertRaises(ValidationError):
            validate_e04_slice(context)

    def test_zero_singleton_and_nonpath_multi_source_dags(self):
        for graph in (dag(0), dag(1), dag(4)):
            validate_e05_slice(create_context(graph))
        graph = dag(4)
        graph["edges"] = [{"id": "a", "sources": ["0"], "targets": ["2"]},
                          {"id": "b", "sources": ["1"], "targets": ["2"]},
                          {"id": "c", "sources": ["2"], "targets": ["3"]}]
        graph["children"].reverse()
        validate_e05_slice(create_context(graph))

    def test_cycles_parallel_self_disconnected_and_nine_nodes_fail(self):
        graphs = [dag(9)]
        for edge in ({"id": "back", "sources": ["2"], "targets": ["0"]},
                     {"id": "self", "sources": ["0"], "targets": ["0"]},
                     {"id": "dup", "sources": ["0"], "targets": ["1"]}):
            graph = dag(3)
            graph["edges"].append(edge)
            graphs.append(graph)
        graph = dag(3)
        graph["edges"] = graph["edges"][:1]
        graphs.append(graph)
        for graph in graphs:
            with self.subTest(graph=graph), self.assertRaises(ValidationError):
                validate_e05_slice(create_context(graph))

    def test_topology_expansion_does_not_loosen_padding_or_existing_geometry(self):
        graph = dag(3)
        with self.assertRaises(ValidationError):
            validate_e05_slice(create_context(graph, layout_arguments={"layoutOptions": {
                "elk.padding": {"top": 0, "right": 0, "bottom": 0, "left": 0}}}))
        graph["edges"][0]["junctionPoints"] = []
        with self.assertRaises(ValidationError):
            validate_e05_slice(create_context(graph))


if __name__ == "__main__":
    unittest.main()
