"""Real Python E04 pipeline vs fixed official observations, never a fake engine."""
import asyncio
import copy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from pyelk import ELK, __version__
from pyelk.algorithms.layered.pipeline import PROCESSOR_SEQUENCE
from native_worker_controls import guarded_worker
from layout_checks import compare_observations, contained, contract, diff, geometry, load

SUITE = ROOT / "tests/fixtures/suites/E04"


def native_observation(path):
    request = load(path)
    graph, constructor, arguments = (copy.deepcopy(request[key]) for key in ("graph", "constructor", "layoutArguments"))
    instance = ELK(constructor)
    instance._controller._worker_target = guarded_worker
    result = asyncio.run(instance.layout(graph, arguments))
    trace = instance.last_trace
    instance.terminateWorker()
    return {"schema": "py-elk-layout-observation/v1", "requestSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "engine": {"name": "pyelk", "version": __version__}, "outcome": "returned", "result": result,
            "inputAfter": graph, "constructorAfter": constructor, "argumentsAfter": arguments,
            "termination": {"outcome": "returned"}}, trace


class NativeSliceConformance(unittest.TestCase):
    def test_all_twenty_one_inputs_match_public_contract_and_independent_geometry(self):
        for case in load(SUITE / "cases.json")["cases"]:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"])
                reference = load(SUITE / "oracle" / case["id"] / "run-01/observation.json")
                actual, _ = native_observation(path)
                compared = compare_observations(reference, actual, profile="native-basic-layered-v1", request=path)
                self.assertTrue(compared["passed"], str(compared.get("publicContract"))[:3500])
                self.assertEqual(compared["lifecycleObservations"]["acceptance"], "NOT_ASSESSED")
                checked = geometry(load(path), actual, case["geometry"])
                self.assertTrue(checked["passed"], str(checked))

    def test_repeated_native_instances_are_exact_and_preserve_original_inputs(self):
        for case in load(SUITE / "cases.json")["cases"]:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"])
                first, _ = native_observation(path)
                second, _ = native_observation(path)
                self.assertTrue(diff(contract(first), contract(second))["passed"])
                request = load(path)
                for actual, key in (("inputAfter", "graph"), ("constructorAfter", "constructor"), ("argumentsAfter", "layoutArguments")):
                    self.assertTrue(diff(first[actual], request[key])["passed"])

    def test_real_dispatch_and_rng_consumption_are_observed_not_filled_with_markers(self):
        for case in load(SUITE / "cases.json")["cases"]:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"])
                request = load(path)
                actual, trace = native_observation(path)
                count = len(request["graph"].get("children", []))
                self.assertEqual([step["processor"] for step in trace], list(PROCESSOR_SEQUENCE) if count else [])
                if count:
                    self.assertTrue(all(step["outcome"] == "returned" for step in trace))
                    self.assertEqual(trace[8]["strategy"], "BARYCENTER")
                    self.assertEqual(trace[9]["strategy"], "TWO_SIDED_GREEDY_SWITCH")
                    self.assertEqual(trace[-1]["after"]["random"]["primitiveDraws"], count + 8 if count >= 2 else 0)
                    self.assertEqual(trace[11]["processor"], "LabelAndNodeSizeProcessor")
                self.assertNotIn("trace", actual["result"])

    def test_raw_strict_differences_are_still_visible(self):
        case = next(c for c in load(SUITE / "cases.json")["cases"] if c["id"] == "layered-chain")
        path = contained(SUITE, case["request"])
        actual, _ = native_observation(path)
        reference = load(SUITE / "oracle" / case["id"] / "run-01/observation.json")
        compared = compare_observations(reference, actual, profile="native-basic-layered-v1", request=path)
        self.assertTrue(compared["passed"])
        self.assertFalse(compared["rawStrict"]["coordinateTolerance"]["passed"])


if __name__ == "__main__":
    unittest.main()
