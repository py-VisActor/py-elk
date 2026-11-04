"""Frozen E05 official inputs, real native conformance, separate tool controls.

Preparation provenance remains its original pre-candidate historical record.
Synthetic fixtures test only the comparer; real native tests call the public API.
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
from build_e05_suite import check_suite
from layout_checks import compare_observations, contained, contract, determinism, diff, geometry, load, sha256, verify_capture
from pyelk import ELK, __version__
from native_worker_controls import guarded_worker

SUITE = ROOT / "tests/fixtures/suites/E05"
ORACLE = SUITE / "oracle"
EXPECTED_PROCESSORS = (
    "EdgeAndLayerConstraintEdgeReverser", "GreedyCycleBreaker", "LayerConstraintPreprocessor",
    "NetworkSimplexLayerer", "LayerConstraintPostprocessor", "LongEdgeSplitter", "PortSideProcessor",
    "PortListSorter", "LayerSweepCrossingMinimizer", "LayerSweepCrossingMinimizer",
    "InLayerConstraintProcessor", "LabelAndNodeSizeProcessor", "InnermostNodeMarginCalculator",
    "BKNodePlacer", "LayerSizeAndGraphHeightCalculator", "OrthogonalEdgeRouter", "LongEdgeJoiner",
    "EndLabelSorter", "ReversedEdgeRestorer",
)


def native_observation(path):
    """Execute Python; the only expected result is the pre-existing official capture."""
    request = load(path)
    graph, constructor, arguments = (copy.deepcopy(request[key]) for key in ("graph", "constructor", "layoutArguments"))
    instance = ELK(constructor)
    instance._controller._worker_target = guarded_worker
    try:
        result = asyncio.run(instance.layout(graph, arguments))
        trace = instance.last_trace
    finally:
        instance.terminateWorker()
    return {"schema": "py-elk-layout-observation/v1", "requestSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "engine": {"name": "pyelk", "version": __version__}, "outcome": "returned", "result": result,
            "inputAfter": graph, "constructorAfter": constructor, "argumentsAfter": arguments,
            "termination": {"outcome": "returned"}}, trace


def assert_adjacency(test, state):
    """Check actual graph identity/denominators independently of phase code."""
    nodes = {n["traceId"]: n for n in state["nodes"]}
    test.assertEqual(len(nodes), len(state["nodes"]))
    ports = {p["traceId"]: (n, p) for n in state["nodes"] for p in n["ports"]}
    test.assertEqual(len(ports), sum(len(n["ports"]) for n in state["nodes"]))
    edges = {e["traceId"]: e for e in state["edges"]}
    test.assertEqual(len(edges), len(state["edges"]))
    test.assertLessEqual(len(nodes), 64)
    test.assertLessEqual(len(edges), 84)
    test.assertLessEqual(len(ports), 168)
    incoming, outgoing = [], []
    for n, p in ports.values():
        test.assertEqual(len(p["incoming"]), len(p["incomingTraceIds"]))
        test.assertEqual(len(p["outgoing"]), len(p["outgoingTraceIds"]))
        for key, endpoint, seen in (("incomingTraceIds", "target", incoming), ("outgoingTraceIds", "source", outgoing)):
            for identity in p[key]:
                test.assertIn(identity, edges)
                test.assertEqual(edges[identity][endpoint]["traceId"], p["traceId"])
                test.assertEqual(edges[identity][endpoint]["node"], n["originId"])
                seen.append(identity)
        for vector in (p["pos"], p["size"], p["anchor"]):
            test.assertTrue(all(type(v) in (int, float) and math.isfinite(v) for v in vector.values()))
    test.assertCountEqual(incoming, list(edges))
    test.assertCountEqual(outgoing, list(edges))
    for edge in edges.values():
        for endpoint in ("source", "target"):
            test.assertIn(edge[endpoint]["traceId"], ports)
    return nodes, ports, edges


class E05NativeConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # These requests and genuine observations were frozen before native DAG
        # implementation. Do not generate expected coordinates from this API.
        check_suite(SUITE)
        verify_capture(ORACLE)
        cls.cases = load(SUITE / "cases.json")["cases"]

    def test_all_36_real_python_results_match_frozen_reference_and_independent_geometry(self):
        self.assertEqual(len(self.cases), 36)
        for case in self.cases:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"])
                reference = load(ORACLE / case["id"] / "run-01/observation.json")
                actual, _ = native_observation(path)
                compared = compare_observations(reference, actual, profile="native-basic-layered-v1", request=path)
                self.assertTrue(compared["passed"], str(compared.get("publicContract"))[:3500])
                self.assertTrue(compared["inputPreservation"]["preserved"])
                self.assertEqual(compared["lifecycleObservations"]["acceptance"], "NOT_ASSESSED")
                self.assertTrue(geometry(load(path), actual, case["geometry"])["passed"])
                request, result = load(path)["graph"], actual["result"]
                for key in ("children", "edges"):
                    self.assertEqual([x["id"] for x in result.get(key, [])], [x["id"] for x in request.get(key, [])])
                for source, edge in zip(request.get("edges", []), result.get("edges", [])):
                    self.assertEqual(edge["sources"], source["sources"])
                    self.assertEqual(edge["targets"], source["targets"])
                    self.assertEqual(len(edge["sections"]), 1)
                    section = edge["sections"][0]
                    self.assertEqual(section["id"], edge["id"] + "_s0")
                    self.assertEqual(section["incomingShape"], source["sources"][0])
                    self.assertEqual(section["outgoingShape"], source["targets"][0])
                    self.assertEqual(edge["container"], request["id"])

    def test_exact_repeat_and_each_original_input_remain_independent(self):
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

    def test_real_trace_preserves_identity_adjacency_and_rank_dummy_restoration(self):
        maximum_dummies = 0
        for case in self.cases:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"])
                request = load(path)["graph"]
                actual, trace = native_observation(path)
                originals = {n["id"] for n in request.get("children", [])}
                original_edges = {e["id"]: e for e in request.get("edges", [])}
                self.assertEqual([step["processor"] for step in trace], list(EXPECTED_PROCESSORS) if originals else [])
                if not originals:
                    continue
                self.assertEqual(trace[8]["strategy"], "BARYCENTER")
                self.assertEqual(trace[9]["strategy"], "TWO_SIDED_GREEDY_SWITCH")
                for step in trace:
                    self.assertEqual(step["outcome"], "returned")
                    for state in (step["before"], step["after"]):
                        assert_adjacency(self, state)
                        self.assertEqual({n["originId"] for n in state["nodes"] if n["type"] == "NORMAL"}, originals)
                    before, after = step["before"]["random"], step["after"]["random"]
                    self.assertIs(type(after["state48"]), int)
                    self.assertTrue(0 <= after["state48"] < 2 ** 48)
                    self.assertGreaterEqual(after["primitiveDraws"], before["primitiveDraws"])
                    if step["processor"] not in ("GreedyCycleBreaker", "LayerSweepCrossingMinimizer", "OrthogonalEdgeRouter"):
                        self.assertEqual(after, before)
                prior, split, joined = trace[5]["before"], trace[5]["after"], trace[16]["after"]
                ranks = {name: i for i, layer in enumerate(prior["layers"]) for name in layer["nodes"]}
                self.assertEqual(set(ranks), originals)
                self.assertTrue(all(layer["nodes"] for layer in prior["layers"]))
                self.assertLessEqual(len(prior["layers"]), 8)
                expected_dummies = 0
                for edge in original_edges.values():
                    span = ranks[edge["targets"][0]] - ranks[edge["sources"][0]]
                    self.assertGreaterEqual(span, 1)
                    expected_dummies += span - 1
                dummies = [n for n in split["nodes"] if n["type"] == "LONG_EDGE"]
                maximum_dummies = max(maximum_dummies, len(dummies))
                self.assertEqual(len(dummies), expected_dummies)
                self.assertEqual(len(split["edges"]), len(original_edges) + expected_dummies)
                self.assertEqual(len(split["nodes"]), len(originals) + expected_dummies)
                split_nodes = {n["traceId"]: n for n in split["nodes"]}
                split_ports = {p["traceId"]: n for n in split["nodes"] for p in n["ports"]}
                split_edges = {e["traceId"]: e for e in split["edges"]}
                heads = {e["originId"]: e["traceId"] for e in prior["edges"]}
                visited_segments = []
                for identity, original in original_edges.items():
                    edge = split_edges[heads[identity]]
                    self.assertEqual(edge["source"]["node"], original["sources"][0])
                    chain = []
                    while True:
                        self.assertNotIn(edge["traceId"], chain)
                        chain.append(edge["traceId"])
                        self.assertEqual(edge["originId"], identity)
                        target = split_ports[edge["target"]["traceId"]]
                        if target["type"] == "NORMAL":
                            self.assertEqual(target["originId"], original["targets"][0])
                            break
                        outgoing = [e for p in target["ports"] for e in p["outgoingTraceIds"]]
                        self.assertEqual(len(outgoing), 1)
                        edge = split_edges[outgoing[0]]
                    self.assertEqual(len(chain), ranks[original["targets"][0]] - ranks[original["sources"][0]])
                    visited_segments.extend(chain)
                self.assertCountEqual(visited_segments, list(split_edges))
                for dummy in dummies:
                    self.assertEqual(dummy["size"], {"x": 0.0, "y": 1.0})
                    self.assertEqual(dummy["properties"]["PORT_CONSTRAINTS"], "FIXED_POS")
                    self.assertEqual(len(dummy["ports"]), 2)
                    self.assertEqual({p["side"] for p in dummy["ports"]}, {"WEST", "EAST"})
                    self.assertTrue(all(p["pos"]["y"] == 0.0 and p["anchor"] == {"x": 0.0, "y": 0.0} for p in dummy["ports"]))
                self.assertEqual(len(joined["nodes"]), len(originals))
                self.assertTrue(all(n["type"] == "NORMAL" for n in joined["nodes"]))
                self.assertCountEqual([e["originId"] for e in joined["edges"]], list(original_edges))
                head_ids = {e["originId"]: e["traceId"] for e in prior["edges"]}
                for edge in joined["edges"]:
                    original = original_edges[edge["originId"]]
                    self.assertEqual(edge["traceId"], head_ids[edge["originId"]])
                    self.assertEqual(edge["source"]["node"], original["sources"][0])
                    self.assertEqual(edge["target"]["node"], original["targets"][0])
                self.assertNotIn("trace", actual["result"])
        self.assertGreaterEqual(maximum_dummies, 4)

    def test_independent_checks_reject_equal_broken_geometry_and_trace_identity(self):
        case = next(c for c in self.cases if c["id"] == "e05-multiskip-permuted-eight")
        path = contained(SUITE, case["request"])
        actual, trace = native_observation(path)
        broken = copy.deepcopy(actual)
        broken["result"]["edges"][0]["sections"][0]["startPoint"] = {"x": -100, "y": -100}
        self.assertTrue(compare_observations(broken, copy.deepcopy(broken))["passed"])
        self.assertFalse(geometry(load(path), broken, case["geometry"])["passed"])
        altered = copy.deepcopy(trace[5]["after"])
        self.assertGreater(len(altered["edges"]), 1)
        altered["edges"][1]["traceId"] = altered["edges"][0]["traceId"]
        with self.assertRaises(AssertionError):
            assert_adjacency(self, altered)


class E05OfficialPreparationCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selection = check_suite(SUITE)
        cls.index = verify_capture(ORACLE)
        cls.provenance = load(SUITE / "oracle-provenance.json")
        cls.cases = load(SUITE / "cases.json")["cases"]

    def records(self):
        for captured in self.index["cases"]:
            path = contained(ORACLE, captured["request"])
            request = load(path)
            for observation in captured["observations"]:
                yield captured, path, request, load(contained(ORACLE, observation))

    def test_genuine_reference_membership_and_fingerprints_do_not_claim_candidate(self):
        self.assertEqual(self.index["role"], "reference")
        self.assertEqual(self.index["status"], "CAPTURED")
        self.assertEqual(self.index["failures"], [])
        self.assertEqual(len(self.index["cases"]), 36)
        self.assertEqual(self.index["repeat"], 2)
        self.assertEqual([c["id"] for c in self.index["cases"]], [c["id"] for c in self.cases])
        for key in ("sourceIndexSha256", "snapshotIndexSha256"):
            self.assertEqual(self.provenance[key], sha256(ORACLE / "index.json"))
        self.assertEqual(self.provenance["suiteSha256"], sha256(SUITE / "cases.json"))
        self.assertEqual(self.provenance["selectionSha256"], sha256(SUITE / "selection.json"))
        self.assertEqual(self.provenance["observationCount"], 72)
        self.assertEqual(self.provenance["masterDenominator"], 25)
        self.assertEqual(self.provenance["selectedMaster"], 12)
        self.assertEqual(self.provenance["excludedMaster"], 13)
        self.assertEqual(self.provenance["projectVariantCount"], 24)
        self.assertIsNone(self.provenance["candidateCapture"])
        self.assertIs(type(self.provenance["pythonAlgorithmsVerified"]), int)
        self.assertEqual(self.provenance["pythonAlgorithmsVerified"], 0)

    def test_all_72_original_requests_outcomes_and_shape_hashes_are_preserved(self):
        definitions = {case["id"]: case for case in self.cases}
        lock = load(ROOT / "UPSTREAM.json")
        count = 0
        for captured, path, request, observed in self.records():
            with self.subTest(case=captured["id"]):
                original = contained(SUITE, definitions[captured["id"]]["request"])
                self.assertEqual(original.read_bytes(), path.read_bytes())
                self.assertEqual(observed["requestSha256"], sha256(path))
                self.assertEqual(observed["engine"]["name"], "elkjs")
                self.assertEqual(observed["engine"]["version"], "0.12.1")
                self.assertEqual(observed["engine"]["entrypointSha256"], lock["distribution"]["sha256Files"]["lib/elk.bundled.js"])
                self.assertEqual(observed["outcome"], "returned")
                self.assertTrue(diff(observed["inputAfter"], observed["result"])["passed"])
                self.assertTrue(diff(observed["constructorAfter"], request["constructor"])["passed"])
                self.assertTrue(diff(observed["argumentsAfter"], request["layoutArguments"])["passed"])
                shapes = [observed["result"], *observed["result"].get("children", [])]
                self.assertTrue(any("$H" in shape for shape in shapes))
                for shape in shapes:
                    if "$H" in shape:
                        self.assertIs(type(shape["$H"]), int)
                # Cleanup outcome is archived separately; no worker-close pass.
                self.assertEqual(observed["termination"]["outcome"], "threw")
                count += 1
        self.assertEqual(count, 72)

    def test_all_official_observations_pass_independent_geometry_and_original_identity(self):
        count = 0
        for captured, _, request, observed in self.records():
            with self.subTest(case=captured["id"]):
                self.assertTrue(geometry(request, observed, captured["definition"]["geometry"])["passed"])
                expected, actual = request["graph"], observed["result"]
                for key in ("children", "edges"):
                    self.assertEqual([e["id"] for e in actual.get(key, [])], [e["id"] for e in expected.get(key, [])])
                for source, result in zip(expected.get("edges", []), actual.get("edges", [])):
                    self.assertEqual(result["sources"], source["sources"])
                    self.assertEqual(result["targets"], source["targets"])
                    self.assertEqual(len(result["sections"]), 1)
                    self.assertEqual(result["sections"][0]["id"], source["id"] + "_s0")
                count += 1
        self.assertEqual(count, 72)

    def test_complete_repeated_official_contract_is_exact_under_existing_source_policy(self):
        for captured in self.index["cases"]:
            request = load(contained(ORACLE, captured["request"]))
            observations = [load(contained(ORACLE, path)) for path in captured["observations"]]
            self.assertEqual(len(observations), 2)
            compared = determinism(observations, request, policy="elkjs-0.12.1-default-seed-v1")
            self.assertTrue(compared["passed"], captured["id"])

    def synthetic_profile_fixture(self):
        captured = next(case for case in self.index["cases"] if case["id"] == "e05-multiskip-permuted-eight")
        path = contained(ORACLE, captured["request"])
        request = load(path)
        reference = load(contained(ORACLE, captured["observations"][0]))
        synthetic = copy.deepcopy(reference)
        synthetic["engine"] = {"name": "pyelk", "toolFixture": "synthetic-comparer-control-not-native-execution"}
        for shape in [synthetic["result"], *synthetic["result"].get("children", [])]:
            shape.pop("$H", None)
        synthetic["inputAfter"] = copy.deepcopy(request["graph"])
        synthetic["constructorAfter"] = copy.deepcopy(request["constructor"])
        synthetic["argumentsAfter"] = copy.deepcopy(request["layoutArguments"])
        synthetic["termination"] = {"outcome": "returned"}
        return captured, path, request, reference, synthetic

    def test_synthetic_comparer_fixture_uses_only_existing_finite_shape_hash_rules(self):
        _, path, _, reference, synthetic = self.synthetic_profile_fixture()
        compared = compare_observations(reference, synthetic, profile="native-basic-layered-v1", request=path)
        self.assertTrue(compared["passed"])
        self.assertFalse(compared["rawStrict"]["passed"])
        self.assertEqual({a["rule"] for a in compared["adaptations"]}, {"GWT-SHAPE-HASH-01", "NATIVE-INPUT-01"})
        for invalid in (False, None, "user-hash", 1.5):
            altered = copy.deepcopy(reference)
            altered["result"]["$H"] = invalid
            altered["inputAfter"]["$H"] = invalid
            self.assertFalse(compare_observations(altered, synthetic, profile="native-basic-layered-v1", request=path)["passed"])

    def test_synthetic_wrong_business_stack_sections_order_and_dummy_leak_are_not_adapted(self):
        _, path, _, reference, synthetic = self.synthetic_profile_fixture()
        for mutate in (lambda o: o["result"]["business"].update({"$H": 0}),
                       lambda o: o["result"]["business"]["error"].update(stack="changed"),
                       lambda o: o["result"]["edges"][0]["sections"][0].update(id="wrong-id"),
                       lambda o: o["result"]["children"].reverse(),
                       lambda o: o["result"]["edges"].pop(),
                       lambda o: o["result"]["children"].append({"id": "synthetic-dummy", "width": 0, "height": 0, "x": 0, "y": 0})):
            altered = copy.deepcopy(synthetic); mutate(altered)
            self.assertFalse(compare_observations(reference, altered, profile="native-basic-layered-v1", request=path)["passed"])

    def test_synthetic_equal_broken_oracles_do_not_bypass_independent_route_geometry(self):
        case, _, request, reference, _ = self.synthetic_profile_fixture()
        broken = copy.deepcopy(reference)
        section = broken["result"]["edges"][0]["sections"][0]
        section["startPoint"] = {"x": -100, "y": -100}
        self.assertTrue(compare_observations(broken, copy.deepcopy(broken))["passed"])
        self.assertFalse(geometry(request, broken, case["definition"]["geometry"])["passed"])


if __name__ == "__main__":
    unittest.main()
