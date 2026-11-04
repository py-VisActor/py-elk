"""Actual E07 native outputs versus the same 72 pinned official inputs.

Raw official differences remain available. Generated negative controls never
count as successful algorithm/API/lifecycle conformance.
"""
import asyncio
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from build_e07_suite import check_suite, classify_request
from layout_checks import (compare_observations, contained, contract, determinism, diff,
                           geometry, load, sha256, verify_capture)
from pyelk import ELK, __version__
from native_worker_controls import guarded_worker

SUITE = ROOT / "tests/fixtures/suites/E07"
ORACLE = SUITE / "oracle"


def native_observation(path):
    request = load(path)
    graph, constructor, arguments = (copy.deepcopy(request[k]) for k in ("graph", "constructor", "layoutArguments"))
    instance = ELK(constructor)
    instance._controller._worker_target = guarded_worker
    try:
        result = asyncio.run(instance.layout(graph, arguments))
        trace = instance.last_trace
    finally:
        instance.terminateWorker()
    return {"schema": "py-elk-layout-observation/v1", "requestSha256": sha256(path),
            "engine": {"name": "pyelk", "version": __version__}, "outcome": "returned", "result": result,
            "inputAfter": graph, "constructorAfter": constructor, "argumentsAfter": arguments,
            "termination": {"outcome": "returned"}}, trace


def weak_component_count(graph):
    adjacent = {node["id"]: set() for node in graph.get("children", [])}
    for edge in graph.get("edges", []):
        source, target = edge["sources"][0], edge["targets"][0]
        adjacent[source].add(target); adjacent[target].add(source)
    unseen, count = set(adjacent), 0
    while unseen:
        pending = [next(iter(unseen))]; count += 1
        while pending:
            node = pending.pop()
            if node in unseen:
                unseen.remove(node); pending.extend(adjacent[node] & unseen)
    return count


class E07NativeConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        check_suite(SUITE)
        cls.index = verify_capture(ORACLE)
        cls.cases = load(SUITE / "cases.json")["cases"]

    def test_same_72_inputs_full_25_master_and_actual_official_provenance(self):
        selected = load(SUITE / "selection.json"); provenance = load(SUITE / "oracle-provenance.json")
        self.assertEqual((len(self.cases), len(self.index["cases"]), self.index["repeat"]), (72, 72, 3))
        self.assertEqual((selected["master"]["caseCount"], selected["selectedMasterCases"],
                          selected["excludedMasterCases"], selected["projectVariantCount"]), (25, 22, 3, 50))
        for key, value in (("caseCount", 72), ("repeat", 3), ("observationCount", 216),
                           ("masterDenominator", 25), ("selectedMaster", 22), ("excludedMaster", 3),
                           ("projectVariantCount", 50), ("pythonAlgorithmsVerified", 0)):
            self.assertIs(type(provenance[key]), int); self.assertEqual(provenance[key], value)
        self.assertEqual(provenance["suiteSha256"], sha256(SUITE / "cases.json"))
        self.assertEqual(provenance["selectionSha256"], sha256(SUITE / "selection.json"))
        self.assertEqual(provenance["sourceIndexSha256"], sha256(ORACLE / "index.json"))
        self.assertEqual(provenance["snapshotIndexSha256"], sha256(ORACLE / "index.json"))
        self.assertEqual(provenance["rawSnapshotFiles"], len([p for p in ORACLE.rglob("*") if p.is_file()]))
        self.assertIsNone(provenance["candidateCapture"])
        for path, fingerprint in provenance["toolSha256"].items():
            self.assertEqual(fingerprint, self.index["sourceSha256"][path])
        for definition, captured in zip(self.cases, self.index["cases"]):
            self.assertEqual(definition, captured["definition"])
            self.assertEqual(contained(SUITE, definition["request"]).read_bytes(), contained(ORACLE, captured["request"]).read_bytes())

    def test_all_real_native_results_match_official_contract_geometry_and_original_ids(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"]); actual, _ = native_observation(path)
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
                    self.assertEqual(edge["container"], original["id"])
                    self.assertEqual(len(edge["sections"]), 1)
                    section = edge["sections"][0]
                    self.assertEqual(section["id"], before["id"] + "_s0")
                    self.assertEqual((section["incomingShape"], section["outgoingShape"]), (before["sources"][0], before["targets"][0]))

    def test_official_repeat_three_and_all_caller_owned_inputs_are_bound(self):
        for captured in self.index["cases"]:
            with self.subTest(case=captured["id"]):
                request = load(ORACLE / captured["request"])
                observations = [load(ORACLE / p) for p in captured["observations"]]
                self.assertTrue(determinism(observations, request, policy="elkjs-0.12.1-default-seed-v1")["passed"])
                for item in observations:
                    self.assertEqual(item["requestSha256"], captured["requestSha256"])
                    self.assertTrue(diff(item["result"], item["inputAfter"])["passed"])
                    self.assertTrue(diff(item["constructorAfter"], request["constructor"])["passed"])
                    self.assertTrue(diff(item["argumentsAfter"], request["layoutArguments"])["passed"])

    def test_real_native_repeated_calls_and_trace_are_exact_and_independent(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"])
                first, first_trace = native_observation(path); second, second_trace = native_observation(path)
                self.assertTrue(diff(contract(first), contract(second))["passed"])
                self.assertTrue(diff(first_trace, second_trace)["passed"])
                self.assertTrue(determinism([first, second], load(path), policy="elkjs-0.12.1-default-seed-v1")["passed"])
                for key, original in (("inputAfter", "graph"), ("constructorAfter", "constructor"), ("argumentsAfter", "layoutArguments")):
                    self.assertTrue(diff(first[key], load(path)[original])["passed"])

    def test_processor_counts_follow_global_flags_direction_and_component_mode(self):
        counts = set()
        for case in self.cases:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"]); request = load(path); graph = request["graph"]
                selected = classify_request(request); policy = selected["geometry"]
                _, trace = native_observation(path)
                components = weak_component_count(graph) if "layerFrame" in policy else int(bool(graph.get("children")))
                loop = any(edge["sources"] == edge["targets"] for edge in graph.get("edges", []))
                per_component = (23 if loop else 19) + (0 if policy["direction"] == "RIGHT" else 2)
                self.assertEqual(len(trace), components * per_component)
                counts.add(per_component)
                self.assertTrue(all(step["outcome"] == "returned" for step in trace))
                self.assertEqual(sum(step["processor"] == "NetworkSimplexLayerer" for step in trace), components)
                self.assertEqual(sum(step["processor"] == "LayerSweepCrossingMinimizer" for step in trace), components * 2)
                self.assertEqual(sum(step["processor"] == "SelfLoopPreProcessor" for step in trace), components if loop else 0)
        self.assertEqual(counts, {19, 21, 23, 25})


if __name__ == "__main__":
    unittest.main()
