"""Development trace identity controls; these do not fabricate layout evidence."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pyelk.algorithms.layered.graph import LEdge, LGraph, LNode, LPort, set_port_owner, set_source, set_target
from pyelk.algorithms.layered.pipeline import snapshot


class TraceIdentityTests(unittest.TestCase):
    def test_distinct_dummy_nodes_and_edge_segments_keep_identity_after_reordering_and_id_changes(self):
        graph = LGraph(None, None, None)
        first, second = LNode(graph, type="LONG_EDGE"), LNode(graph, type="LONG_EDGE")
        graph.layerless_nodes[:] = [first, second]
        source, target = LPort(), LPort()
        set_port_owner(source, first)
        set_port_owner(target, second)
        edge, other = LEdge(), LEdge()
        for segment in (edge, other):
            set_source(segment, source)
            set_target(segment, target)
        first.properties["ORIGIN"] = edge
        second.properties["ORIGIN"] = other
        memo = {}
        before = snapshot(graph, identities=memo)
        first.id, second.id = 20, 10
        graph.layerless_nodes.reverse()
        after = snapshot(graph, identities=memo)
        self.assertNotEqual(before["nodes"][0]["originId"], before["nodes"][1]["originId"])
        self.assertEqual(before["nodes"][0]["traceId"], after["nodes"][1]["traceId"])
        self.assertEqual(before["nodes"][1]["traceId"], after["nodes"][0]["traceId"])
        self.assertNotEqual(before["edges"][0]["traceId"], before["edges"][1]["traceId"])
        self.assertEqual(before["nodes"][0]["properties"]["ORIGIN"]["traceId"], before["edges"][0]["traceId"])
        self.assertEqual([port.owner for port in (source, target)], [first, second])
        self.assertEqual(source.outgoing_edges, [edge, other])

    def test_internal_sentinels_are_explicit_json_diagnostics_and_not_geometry_values(self):
        graph = LGraph(None, None, None)
        node = LNode(graph)
        graph.layerless_nodes.append(node)
        node.properties.update(internalInfinity=float("inf"), internalNaN=float("nan"), flags={"B", "A"})
        checked = snapshot(graph)["nodes"][0]["properties"]
        self.assertEqual(checked["internalInfinity"], {"internalNonfinite": "Infinity"})
        self.assertEqual(checked["internalNaN"], {"internalNonfinite": "NaN"})
        self.assertEqual(checked["flags"], {"setValues": ["A", "B"]})
        self.assertEqual((node.pos.x, node.pos.y), (0, 0))


if __name__ == "__main__":
    unittest.main()
