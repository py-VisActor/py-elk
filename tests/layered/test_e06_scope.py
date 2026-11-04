"""Independent host multigraph admission; this function cannot assign ranks."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk._errors import ValidationError
from pyelk.execution import create_context
from pyelk.algorithms.layered.scope import validate_e05_slice, validate_e06_slice


def graph(count, endpoints):
    return {"id": "g", "children": [{"id": str(i), "width": 10, "height": 20} for i in range(count)],
            "edges": [{"id": "e" + str(i), "sources": [str(s)], "targets": [str(t)]}
                      for i, (s, t) in enumerate(endpoints)]}


class MultigraphAdmissionTests(unittest.TestCase):
    def test_cycles_selfloops_parallel_and_edge_limit_do_not_compute_layout(self):
        for value in (graph(0, []), graph(1, [(0, 0)] * 28), graph(2, [(0, 1)] * 27 + [(1, 0)]),
                      graph(8, [(i, i + 1) for i in range(7)] + [(0, 7)] * 21)):
            original = copy.deepcopy(value)
            context = create_context(value)
            admitted = validate_e06_slice(context)
            self.assertEqual((admitted.node_count, admitted.edge_count), (len(value["children"]), len(value["edges"])))
            self.assertEqual(value, original)
            self.assertEqual(context.working_graph.to_json(), original)

    def test_frozen_e05_policy_still_rejects_new_topologies(self):
        for value in (graph(1, [(0, 0)]), graph(2, [(0, 1), (0, 1)]), graph(2, [(0, 1), (1, 0)])):
            validate_e06_slice(create_context(value))
            with self.assertRaises(ValidationError):
                validate_e05_slice(create_context(value))

    def test_out_of_bound_or_disconnected_inputs_fail_without_mutation(self):
        for value in (graph(1, [(0, 0)] * 29), graph(9, [(i, i + 1) for i in range(8)]),
                      graph(2, [(0, 0), (1, 1)]), graph(3, [(0, 1), (1, 0)])):
            before = copy.deepcopy(value)
            with self.assertRaises(ValidationError):
                validate_e06_slice(create_context(value))
            self.assertEqual(value, before)

    def test_unchanged_numeric_seed_direction_and_shape_guards(self):
        for change in (lambda v: v.update(layoutOptions={"elk.randomSeed": 0}),
                       lambda v: v.update(layoutOptions={"elk.direction": "DOWN"}),
                       lambda v: v["children"][0].update(ports=[{"id": "p"}]),
                       lambda v: v["children"][0].update(width=1000001)):
            value = graph(1, [(0, 0)])
            change(value)
            with self.assertRaises(ValidationError):
                validate_e06_slice(create_context(value))
