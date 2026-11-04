"""E06 official bytes and real native executions; expected layouts are JS only.

The prepared requests were independently chosen before E06 native admission.
Synthetic mutations below test rejection, never count as engine conformance.
"""
import asyncio
import copy
import hashlib
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from build_e06_suite import check_suite
from layout_checks import (compare_observations, contained, contract, determinism, diff,
                           geometry, load, sha256, verify_capture)
from pyelk import ELK, __version__
from native_worker_controls import (guarded_worker, without_loop_postprocessor_worker,
                                    without_reversed_restorer_worker)
from pyelk._errors import UnsupportedFeatureError

SUITE = ROOT / "tests/fixtures/suites/E06"
ORACLE = SUITE / "oracle"
DEFAULT_SEQUENCE = (
    "EdgeAndLayerConstraintEdgeReverser", "GreedyCycleBreaker", "LayerConstraintPreprocessor",
    "NetworkSimplexLayerer", "LayerConstraintPostprocessor", "LongEdgeSplitter", "PortSideProcessor",
    "PortListSorter", "LayerSweepCrossingMinimizer", "LayerSweepCrossingMinimizer",
    "InLayerConstraintProcessor", "LabelAndNodeSizeProcessor", "InnermostNodeMarginCalculator",
    "BKNodePlacer", "LayerSizeAndGraphHeightCalculator", "OrthogonalEdgeRouter", "LongEdgeJoiner",
    "EndLabelSorter", "ReversedEdgeRestorer",
)
LOOP_SEQUENCE = (
    "EdgeAndLayerConstraintEdgeReverser", "SelfLoopPreProcessor", "GreedyCycleBreaker", "LayerConstraintPreprocessor",
    "NetworkSimplexLayerer", "LayerConstraintPostprocessor", "LongEdgeSplitter", "PortSideProcessor", "PortListSorter",
    "LayerSweepCrossingMinimizer", "LayerSweepCrossingMinimizer", "SelfLoopPortRestorer", "InLayerConstraintProcessor",
    "LabelAndNodeSizeProcessor", "InnermostNodeMarginCalculator", "SelfLoopRouter", "BKNodePlacer",
    "LayerSizeAndGraphHeightCalculator", "OrthogonalEdgeRouter", "LongEdgeJoiner", "SelfLoopPostProcessor",
    "EndLabelSorter", "ReversedEdgeRestorer",
)


def native_observation(path, *, worker_target=guarded_worker):
    request = load(path)
    graph, constructor, arguments = (copy.deepcopy(request[key]) for key in ("graph", "constructor", "layoutArguments"))
    instance = ELK(constructor)
    instance._controller._worker_target = worker_target
    try:
        result = asyncio.run(instance.layout(graph, arguments))
        trace = instance.last_trace
    finally:
        instance.terminateWorker()
    return {"schema": "py-elk-layout-observation/v1", "requestSha256": sha256(path),
            "engine": {"name": "pyelk", "version": __version__}, "outcome": "returned", "result": result,
            "inputAfter": graph, "constructorAfter": constructor, "argumentsAfter": arguments,
            "termination": {"outcome": "returned"}}, trace


def holder_edges(state):
    """Detached loop edges remain real objects, not absent from denominators."""
    return [entry["edge"] for node in state["nodes"]
            for loop in node["properties"].get("SELF_LOOP_HOLDER", {}).get("loops", []) for entry in loop["edges"]]


def identities(test, state):
    nodes = {n["traceId"]: n for n in state["nodes"]}
    test.assertEqual(len(nodes), len(state["nodes"]))
    visible = {p["traceId"]: (n, p) for n in state["nodes"] for p in n["ports"]}
    test.assertEqual(len(visible), sum(len(n["ports"]) for n in state["nodes"]))
    ports = dict(visible)
    for n in state["nodes"]:
        for p in n["properties"].get("SELF_LOOP_HOLDER", {}).get("ports", []):
            identity = p["reference"]["traceId"]
            if p["owner"] is None:
                test.assertNotIn(identity, visible)
                test.assertTrue(p["isHidden"])
            else:
                test.assertEqual(p["owner"]["traceId"], n["traceId"])
                test.assertIn(identity, visible)
            ports[identity] = (n, p)
    edges = {e["traceId"]: e for e in state["edges"]}
    test.assertEqual(len(edges), len(state["edges"]))
    incoming, outgoing = [], []
    for node, port in visible.values():
        for key, endpoint, seen in (("incomingTraceIds", "target", incoming), ("outgoingTraceIds", "source", outgoing)):
            for identity in port[key]:
                test.assertIn(identity, edges)
                test.assertEqual(edges[identity][endpoint]["traceId"], port["traceId"])
                test.assertEqual(edges[identity][endpoint]["node"], node["originId"])
                seen.append(identity)
        for vector in (port["pos"], port["size"], port["anchor"]):
            test.assertTrue(all(type(value) in (int, float) and math.isfinite(value) for value in vector.values()))
    test.assertCountEqual(incoming, edges)
    test.assertCountEqual(outgoing, edges)
    for edge in holder_edges(state):
        identity = edge["reference"]["traceId"]
        if identity in edges:
            test.assertEqual(edges[identity]["source"], edge["source"])
            test.assertEqual(edges[identity]["target"], edge["target"])
        else:
            test.assertIsNone(edge["source"])
            test.assertIsNone(edge["target"])
            edges[identity] = {**edge, "traceId": identity, "originId": edge["reference"]["edge"]}
    test.assertLessEqual(len(nodes), 176)
    test.assertLessEqual(len(edges), 196)
    test.assertLessEqual(len(ports), 392)
    return nodes, ports, edges


class E06NativeConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_suite(SUITE)
        cls.index = verify_capture(ORACLE)
        cls.cases = load(SUITE / "cases.json")["cases"]

    def test_same_52_official_requests_and_full_master_denominator_are_frozen(self):
        self.assertEqual(len(self.cases), 52)
        self.assertEqual(len(self.index["cases"]), 52)
        self.assertEqual(self.index["repeat"], 3)
        self.assertEqual(self.index["suiteSha256"], sha256(SUITE / "cases.json"))
        selection = load(SUITE / "selection.json")
        self.assertEqual(selection["master"]["caseCount"], 25)
        self.assertEqual(sum(row["included"] for row in selection["masterCases"]), 15)
        self.assertEqual(sum(not row["included"] for row in selection["masterCases"]), 10)
        for definition, captured in zip(self.cases, self.index["cases"]):
            self.assertEqual(definition, captured["definition"])
            self.assertEqual(contained(SUITE, definition["request"]).read_bytes(), contained(ORACLE, captured["request"]).read_bytes())

    def test_official_provenance_binds_the_complete_original_snapshot_without_python_claim(self):
        provenance = load(SUITE / "oracle-provenance.json")
        self.assertEqual(provenance["schema"], "py-elk-e06-oracle-provenance/v1")
        self.assertEqual(provenance["suiteSha256"], sha256(SUITE / "cases.json"))
        self.assertEqual(provenance["selectionSha256"], sha256(SUITE / "selection.json"))
        self.assertEqual(provenance["sourceIndexSha256"], sha256(ORACLE / "index.json"))
        self.assertEqual(provenance["snapshotIndexSha256"], sha256(ORACLE / "index.json"))
        for key, expected in (("caseCount", 52), ("repeat", 3), ("observationCount", 156),
                              ("masterDenominator", 25), ("selectedMaster", 15), ("excludedMaster", 10),
                              ("projectVariantCount", 37), ("pythonAlgorithmsVerified", 0)):
            self.assertIs(type(provenance[key]), int)
            self.assertEqual(provenance[key], expected)
        self.assertEqual(provenance["rawSnapshotFiles"], len([p for p in ORACLE.rglob("*") if p.is_file()]))
        self.assertIsNone(provenance["candidateCapture"])
        for path, fingerprint in provenance["toolSha256"].items():
            self.assertEqual(fingerprint, self.index["sourceSha256"][path])

    def test_all_52_real_native_results_match_official_contract_geometry_and_original_ids(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"])
                actual, _ = native_observation(path)
                reference = load(ORACLE / case["id"] / "run-01/observation.json")
                compared = compare_observations(reference, actual, profile="native-basic-layered-v1", request=path)
                self.assertTrue(compared["passed"], str(compared.get("publicContract"))[:3500])
                self.assertTrue(compared["inputPreservation"]["preserved"])
                self.assertEqual(compared["lifecycleObservations"]["acceptance"], "NOT_ASSESSED")
                self.assertTrue(geometry(load(path), actual, case["geometry"])["passed"])
                original, result = load(path)["graph"], actual["result"]
                for key in ("children", "edges"):
                    self.assertEqual([x["id"] for x in result.get(key, [])], [x["id"] for x in original.get(key, [])])
                for before, edge in zip(original.get("edges", []), result.get("edges", [])):
                    self.assertTrue(diff(before["sources"], edge["sources"])["passed"])
                    self.assertTrue(diff(before["targets"], edge["targets"])["passed"])
                    self.assertEqual(len(edge["sections"]), 1)
                    section = edge["sections"][0]
                    self.assertEqual(section["id"], before["id"] + "_s0")
                    self.assertEqual(section["incomingShape"], before["sources"][0])
                    self.assertEqual(section["outgoingShape"], before["targets"][0])
                    self.assertEqual(edge["container"], original["id"])
                for before, after in [(original, result), *zip(original.get("children", []), result.get("children", [])),
                                      *zip(original.get("edges", []), result.get("edges", []))]:
                    for key in before:
                        if key not in {"children", "edges"}:
                            self.assertTrue(diff(before[key], after[key])["passed"], key)

    def test_official_repeat_three_is_exact_and_same_bytes_input_binding_is_required(self):
        for captured in self.index["cases"]:
            with self.subTest(case=captured["id"]):
                request = load(ORACLE / captured["request"])
                observations = [load(ORACLE / p) for p in captured["observations"]]
                self.assertTrue(determinism(observations, request, policy="elkjs-0.12.1-default-seed-v1")["passed"])
                for observation in observations:
                    self.assertEqual(observation["requestSha256"], captured["requestSha256"])
                    self.assertTrue(diff(observation["result"], observation["inputAfter"])["passed"])

    def test_real_native_repeat_inputs_and_per_call_trace_are_independent(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"])
                first, first_trace = native_observation(path)
                second, second_trace = native_observation(path)
                self.assertTrue(diff(contract(first), contract(second))["passed"])
                self.assertTrue(diff(first_trace, second_trace)["passed"])
                self.assertTrue(determinism([first, second], load(path), policy="elkjs-0.12.1-default-seed-v1")["passed"])
                for key, original in (("inputAfter", "graph"), ("constructorAfter", "constructor"), ("argumentsAfter", "layoutArguments")):
                    self.assertTrue(diff(first[key], load(path)[original])["passed"])

    def test_real_trace_keeps_hidden_originals_and_recovers_all_dummy_chains(self):
        maximum_nodes = maximum_original_edges = 0
        for case in self.cases:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"])
                request = load(path)["graph"]
                _, trace = native_observation(path)
                originals = {n["id"] for n in request.get("children", [])}
                original_edges = {e["id"]: e for e in request.get("edges", [])}
                loops = {identity for identity, e in original_edges.items() if e["sources"] == e["targets"]}
                expected = LOOP_SEQUENCE if loops else DEFAULT_SEQUENCE
                self.assertEqual([step["processor"] for step in trace], list(expected) if originals else [])
                if not originals:
                    continue
                initial_nodes, initial_ports, initial_edges = identities(self, trace[0]["before"])
                initial_originals = {e["originId"]: identity for identity, e in initial_edges.items()}
                self.assertEqual(set(initial_originals), set(original_edges))
                self.assertEqual(len(initial_ports), 2 * len(original_edges))
                maximum_original_edges = max(maximum_original_edges, len(initial_edges))
                by_name = {step["processor"]: step for step in trace if step["processor"] != "LayerSweepCrossingMinimizer"}
                sweeps = [step["strategy"] for step in trace if step["processor"] == "LayerSweepCrossingMinimizer"]
                self.assertEqual(sweeps, ["BARYCENTER", "TWO_SIDED_GREEDY_SWITCH"])
                for step in trace:
                    self.assertEqual(step["outcome"], "returned")
                    for state in (step["before"], step["after"]):
                        nodes, ports, edges = identities(self, state)
                        self.assertEqual({n["originId"] for n in nodes.values() if n["type"] == "NORMAL"}, originals)
                        self.assertTrue(set(initial_ports) <= set(ports))
                        self.assertTrue(set(initial_edges) <= set(edges))
                        self.assertTrue(all(edges[identity]["originId"] == origin for origin, identity in initial_originals.items()))
                        self.assertEqual({e["originId"] for e in edges.values()}, set(original_edges))
                        for node in nodes.values():
                            if node["type"] == "NORMAL": self.assertEqual(node["properties"]["ORIGINAL_PORT_CONSTRAINTS"], "FREE")
                        maximum_nodes = max(maximum_nodes, len(nodes))
                    before, after = step["before"]["random"], step["after"]["random"]
                    self.assertIs(type(after["state48"]), int)
                    self.assertTrue(0 <= after["state48"] < 2 ** 48)
                    self.assertGreaterEqual(after["primitiveDraws"], before["primitiveDraws"])
                    if step["processor"] not in {"GreedyCycleBreaker", "LayerSweepCrossingMinimizer", "OrthogonalEdgeRouter"}:
                        self.assertEqual(after, before)
                splitting = by_name["LongEdgeSplitter"]
                ranks = {name: i for i, layer in enumerate(splitting["before"]["layers"]) for name in layer["nodes"]}
                self.assertEqual(set(ranks), originals)
                self.assertTrue(all(layer["nodes"] for layer in splitting["before"]["layers"]))
                self.assertLessEqual(len(splitting["before"]["layers"]), 8)
                expected_dummies = 0
                for edge in splitting["before"]["edges"]:
                    span = ranks[edge["target"]["node"]] - ranks[edge["source"]["node"]]
                    self.assertGreaterEqual(span, 1)
                    expected_dummies += span - 1
                sn, sp, se = identities(self, splitting["after"])
                self.assertEqual(sum(n["type"] == "LONG_EDGE" for n in sn.values()), expected_dummies)
                self.assertEqual(len(se), len(original_edges) + expected_dummies)
                self.assertEqual(len(sp), 2 * len(original_edges) + 2 * expected_dummies)
                final_nodes, final_ports, final_edges = identities(self, trace[-1]["after"])
                self.assertEqual(set(final_nodes), set(initial_nodes))
                self.assertEqual(set(final_ports), set(initial_ports))
                self.assertEqual(set(final_edges), set(initial_edges))
                for edge in final_edges.values():
                    original = original_edges[edge["originId"]]
                    self.assertEqual(edge["source"]["node"], original["sources"][0])
                    self.assertEqual(edge["target"]["node"], original["targets"][0])
                    self.assertIs(edge["properties"].get("REVERSED", False), False)
        self.assertGreater(maximum_nodes, 64, "The independently prepared stress input must exercise the new internal bound")
        self.assertEqual(maximum_original_edges, 28)

    def test_missing_loop_postprocessor_cannot_lose_an_edge_and_pass(self):
        path = SUITE / "requests/master/layered-self-loop.json"
        actual, _ = native_observation(path)
        reference = load(ORACLE / "layered-self-loop/run-01/observation.json")
        self.assertTrue(compare_observations(reference, actual, profile="native-basic-layered-v1", request=path)["passed"])
        damaged, trace = native_observation(path, worker_target=without_loop_postprocessor_worker)
        self.assertFalse(compare_observations(reference, damaged, profile="native-basic-layered-v1", request=path)["passed"])
        final = trace[-1]["after"]
        self.assertTrue(any(edge["source"] is None for edge in holder_edges(final)),
                        "The omitted real postprocessor must leave an actual detached loop")

    def test_missing_restorer_cannot_hide_wrong_direction_at_equal_coordinates(self):
        path = SUITE / "requests/project/e06-cycle-six-zero.json"
        normal, normal_trace = native_observation(path)
        reference = load(ORACLE / "e06-cycle-six-zero/run-01/observation.json")
        self.assertTrue(compare_observations(reference, normal, profile="native-basic-layered-v1", request=path)["passed"])
        damaged, trace = native_observation(path, worker_target=without_reversed_restorer_worker)
        # Full Source transfer has no old slice guard. At coincident endpoints
        # JSON coordinates can hide reversal, so check actual object ownership.
        originals = {edge['id']:edge for edge in load(path)['graph']['edges']}
        final = trace[-1]['after']
        unrestored = [edge for edge in final['edges'] if edge['properties'].get('REVERSED',False)]
        self.assertTrue(unrestored)
        self.assertTrue(any(edge['source']['node'] != originals[edge['originId']]['sources'][0]
                            for edge in unrestored))
        self.assertTrue(all(not edge['properties'].get('REVERSED',False)
                            for edge in normal_trace[-1]['after']['edges']))

    def test_synthetic_geometry_and_public_endpoint_mutations_cannot_pass(self):
        case = next(c for c in self.cases if c["id"] == "layered-parallel-edges")
        path = contained(SUITE, case["request"])
        reference = load(ORACLE / case["id"] / "run-01/observation.json")
        candidate, _ = native_observation(path)
        self.assertTrue(compare_observations(reference, candidate, profile="native-basic-layered-v1", request=path)["passed"])
        moved = copy.deepcopy(candidate); moved["result"]["children"][0]["x"] = -10 ** 9
        self.assertFalse(compare_observations(reference, moved, profile="native-basic-layered-v1", request=path)["passed"])
        self.assertFalse(geometry(load(path), moved, case["geometry"])["passed"])
        changed = copy.deepcopy(candidate); changed["result"]["edges"][0]["sections"][0]["incomingShape"] = "wrong"
        self.assertFalse(compare_observations(reference, changed, profile="native-basic-layered-v1", request=path)["passed"])


if __name__ == "__main__":
    unittest.main()
