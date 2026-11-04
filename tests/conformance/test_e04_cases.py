"""Independent official fixtures and real E04 native slice acceptance controls.

Native checks use the public implementation. Deliberate runtime corruption is
labelled as a negative control, never presented as an alternative engine.
"""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from build_slice_suite import check_suite
from layout_checks import compare_observations, contained, diff, geometry, load, sha256, verify_capture
from pyelk import ELK, __version__
from pyelk._errors import WorkerExecutionError
from native_worker_controls import (EXTERNAL_ENGINE_GUARD, attempted_external_process_worker,
                                    guarded_worker, instrument_kernel, without_node_spacing_worker)

SUITE = ROOT / "tests/fixtures/suites/E04"
ORACLE = SUITE / "oracle"


def execute_native(path, *, worker_target=guarded_worker):
    request = load(path)
    graph, constructor, arguments = (copy.deepcopy(request[key]) for key in ("graph", "constructor", "layoutArguments"))
    elk = ELK(constructor)
    # The public API still spawns its real Python CPU worker. Test guards and
    # deliberate faults are installed in that child, not in this parent.
    elk._controller._worker_target = worker_target
    try:
        result = asyncio.run(elk.layout(graph, arguments))
    finally:
        elk.terminateWorker()
    return {"schema": "py-elk-layout-observation/v1", "requestSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "engine": {"name": "pyelk", "version": __version__}, "outcome": "returned", "result": result,
            "inputAfter": graph, "constructorAfter": constructor, "argumentsAfter": arguments,
            "termination": {"outcome": "returned"}}


def execute_kernel_instrumentation(path):
    """Only the volatile-port instrumentation test calls the kernel directly.

    Its callback deliberately contains TestCase assertions and observes writes
    in this same process; it creates no ELK instance, invokes no termination,
    and is not public-API or lifecycle acceptance. No termination is reported.
    """
    request = load(path)
    graph, constructor, arguments = (copy.deepcopy(request[key]) for key in ("graph", "constructor", "layoutArguments"))
    result = instrument_kernel(graph, constructor, arguments)
    return {"schema": "py-elk-layout-observation/v1", "requestSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "engine": {"name": "pyelk", "version": __version__}, "outcome": "returned", "result": result,
            "inputAfter": graph, "constructorAfter": constructor, "argumentsAfter": arguments}


class E04OfficialOracleCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selection = check_suite(SUITE)
        cls.index = verify_capture(ORACLE)
        cls.provenance = load(SUITE / "oracle-provenance.json")
        cls.cases = load(SUITE / "cases.json")["cases"]

    def records(self):
        for captured in self.index["cases"]:
            request = load(contained(ORACLE, captured["request"]))
            for observation in captured["observations"]:
                yield captured, request, load(contained(ORACLE, observation))

    def test_membership_bytes_and_oracle_provenance_do_not_claim_candidate_acceptance(self):
        self.assertEqual(self.index["role"], "reference")
        self.assertEqual(self.index["status"], "CAPTURED")
        self.assertEqual(self.index["repeat"], 2)
        self.assertEqual(self.index["failures"], [])
        self.assertEqual(len(self.index["cases"]), 21)
        self.assertEqual([c["id"] for c in self.index["cases"]], [c["id"] for c in self.cases])
        self.assertEqual(self.provenance["sourceIndexSha256"], sha256(ORACLE / "index.json"))
        self.assertEqual(self.provenance["snapshotIndexSha256"], sha256(ORACLE / "index.json"))
        self.assertEqual(self.provenance["suiteSha256"], sha256(SUITE / "cases.json"))
        self.assertEqual(self.provenance["selectionSha256"], sha256(SUITE / "selection.json"))
        self.assertIsNone(self.provenance["candidateCapture"])
        self.assertIs(type(self.provenance["pythonAlgorithmsVerified"]), int)
        self.assertEqual(self.provenance["pythonAlgorithmsVerified"], 0)
        self.assertEqual(self.provenance["masterDenominator"], 25)
        self.assertEqual(self.provenance["selectedMaster"], 5)
        self.assertEqual(self.provenance["projectVariantCount"], 16)
        self.assertEqual(self.provenance["observationCount"], 42)

    def test_every_engine_outcome_and_copied_request_is_genuine_locked_oracle(self):
        definitions = {case["id"]: case for case in self.cases}
        lock = load(ROOT / "UPSTREAM.json")
        for captured, request, observed in self.records():
            with self.subTest(case=captured["id"]):
                original_path = contained(SUITE, definitions[captured["id"]]["request"])
                self.assertEqual(original_path.read_bytes(), contained(ORACLE, captured["request"]).read_bytes())
                self.assertEqual(observed["requestSha256"], sha256(original_path))
                self.assertEqual(observed["engine"]["name"], "elkjs")
                self.assertEqual(observed["engine"]["version"], lock["javascript"]["version"])
                self.assertEqual(observed["engine"]["entrypointSha256"], lock["distribution"]["sha256Files"]["lib/elk.bundled.js"])
                self.assertEqual(observed["outcome"], "returned")
                self.assertTrue(diff(observed["constructorAfter"], request["constructor"])["passed"])
                self.assertTrue(diff(observed["argumentsAfter"], request["layoutArguments"])["passed"])
                self.assertTrue(diff(observed["result"], observed["inputAfter"])["passed"])

    def test_all_42_official_observations_satisfy_independent_geometry(self):
        checked = 0
        for captured, request, observed in self.records():
            with self.subTest(case=captured["id"]):
                result = geometry(request, observed, captured["definition"]["geometry"])
                self.assertTrue(result["passed"], result)
                checked += 1
        self.assertEqual(checked, 42)

    def test_same_request_repetitions_are_strictly_deterministic_in_this_sample(self):
        for captured in self.index["cases"]:
            with self.subTest(case=captured["id"]):
                observations = [load(contained(ORACLE, o)) for o in captured["observations"]]
                self.assertEqual(len(observations), 2)
                compared = compare_observations(observations[0], observations[1])
                self.assertTrue(compared["exact"]["passed"], compared)
                self.assertTrue(compared["passed"], compared)

    def test_arrays_ids_business_hashes_and_stack_survive_in_the_oracle(self):
        project_checked = 0
        for captured, request, observed in self.records():
            expected, result = request["graph"], observed["result"]
            with self.subTest(case=captured["id"]):
                self.assertEqual([n["id"] for n in result.get("children", [])], [n["id"] for n in expected.get("children", [])])
                self.assertEqual([e["id"] for e in result.get("edges", [])], [e["id"] for e in expected.get("edges", [])])
                if captured["id"].startswith("e04-"):
                    self.assertTrue(diff(result["business"], expected["business"])["passed"])
                    self.assertIs(result["business"]["$H"], False)
                    self.assertEqual(result["business"]["error"]["stack"], "business-stack")
                    project_checked += 1
        self.assertEqual(project_checked, 32)

    def test_synthetic_geometry_damage_is_rejected_independently_of_json_match(self):
        captured = next(c for c in self.index["cases"] if c["id"] == "e04-default-two-positive")
        request = load(contained(ORACLE, captured["request"]))
        original = load(contained(ORACLE, captured["observations"][0]))
        broken = copy.deepcopy(original)
        broken["result"]["children"][1]["x"] = broken["result"]["children"][0]["x"]
        self.assertFalse(geometry(request, broken, captured["definition"]["geometry"])["passed"])
        # Even two identical broken observations do not defeat the geometry gate.
        self.assertTrue(compare_observations(broken, broken)["passed"])
        self.assertFalse(geometry(request, broken, captured["definition"]["geometry"])["passed"])

    def test_synthetic_section_identity_and_order_damage_are_never_normalized(self):
        captured = next(c for c in self.index["cases"] if c["id"] == "e04-default-chain-unequal")
        original = load(contained(ORACLE, captured["observations"][0]))
        section_changed = copy.deepcopy(original)
        section_changed["result"]["edges"][0]["sections"][0]["id"] = "synthetic-wrong-section"
        self.assertFalse(compare_observations(original, section_changed)["passed"])
        reordered = copy.deepcopy(original)
        reordered["result"]["children"].reverse()
        self.assertFalse(compare_observations(original, reordered)["passed"])
        request = load(contained(ORACLE, captured["request"]))
        self.assertFalse(geometry(request, reordered, captured["definition"]["geometry"])["passed"])


class E04IndependentNativeCases(unittest.TestCase):
    def test_all_frozen_inputs_use_real_public_api_and_preserve_raw_requests(self):
        # Membership and original expected observations predate implementation.
        cases = load(SUITE / "cases.json")["cases"]
        self.assertEqual(len(cases), 21)
        for case in cases:
            with self.subTest(case=case["id"]):
                path = contained(SUITE, case["request"])
                before = path.read_bytes()
                reference = load(ORACLE / case["id"] / "run-01/observation.json")
                candidate = execute_native(path)
                compared = compare_observations(reference, candidate, profile="native-basic-layered-v1", request=path)
                self.assertTrue(compared["passed"], compared.get("publicContract"))
                self.assertTrue(compared["inputPreservation"]["preserved"])
                self.assertTrue(geometry(load(path), candidate, case["geometry"])["passed"])
                self.assertEqual(path.read_bytes(), before)
                expected = load(path)["graph"]
                for key in ("children", "edges"):
                    self.assertEqual([x["id"] for x in candidate["result"].get(key, [])], [x["id"] for x in expected.get(key, [])])

    def test_serial_call_constructor_result_and_trace_aliases_are_isolated(self):
        path = SUITE / "requests/project/e04-spacing-padding-seed17.json"
        request = load(path)
        constructor = {"defaultLayoutOptions": {"elk.direction": "RIGHT"}}
        elk = ELK(constructor)
        constructor["defaultLayoutOptions"]["elk.direction"] = "DOWN"
        graph, arguments = copy.deepcopy(request["graph"]), copy.deepcopy(request["layoutArguments"])
        try:
            first = asyncio.run(elk.layout(graph, arguments))
            expected = copy.deepcopy(first)
            first["business"]["error"]["stack"] = "changed result only"
            first["children"][0]["x"] = -99
            trace = elk.last_trace
            trace[0]["processor"] = "changed trace only"
            self.assertNotEqual(elk.last_trace[0]["processor"], "changed trace only")
            second = asyncio.run(elk.layout(graph, arguments))
            self.assertTrue(diff(second, expected)["passed"])
            self.assertTrue(diff(graph, request["graph"])["passed"])
            self.assertTrue(diff(arguments, request["layoutArguments"])["passed"])
        finally:
            elk.terminateWorker()

    def test_removing_required_node_spacing_operation_is_rejected_by_real_pipeline(self):
        path = SUITE / "requests/project/e04-default-chain-unequal.json"
        reference = load(ORACLE / "e04-default-chain-unequal/run-01/observation.json")
        case = next(c for c in load(SUITE / "cases.json")["cases"] if c["id"] == "e04-default-chain-unequal")
        normal = execute_native(path)
        self.assertTrue(compare_observations(reference, normal, profile="native-basic-layered-v1", request=path)["passed"])
        self.assertTrue(geometry(load(path), normal, case["geometry"])["passed"])
        # Deliberate damage to a real dispatch entry; no synthetic success data.
        omitted = execute_native(path, worker_target=without_node_spacing_worker)
        compared = compare_observations(reference, omitted, profile="native-basic-layered-v1", request=path)
        self.assertFalse(compared["passed"])
        self.assertFalse(compared["publicContract"]["exact"]["passed"])
        self.assertFalse(compared["publicContract"]["coordinateTolerance"]["passed"])
        # Full BK can legitimately process the actual uncentered port state.
        # Geometry checks attachment/overlap/routing; a boundary port remains
        # geometrically legal, so exact source conformance is a separate gate.
        self.assertTrue(geometry(load(path), omitted, case["geometry"])["passed"])

    def test_source_required_volatile_port_ids_and_center_writes_are_observable(self):
        from pyelk.algorithms.layered.processors import INTERMEDIATE_PROCESSORS, label_and_node_size_processor

        path = SUITE / "requests/project/e04-default-chain-unequal.json"
        reference = load(ORACLE / "e04-default-chain-unequal/run-01/observation.json")
        case = next(c for c in load(SUITE / "cases.json")["cases"] if c["id"] == "e04-default-chain-unequal")
        calls = []

        def inject_then_execute_real_node_spacing(work):
            # Use the actual import/layering/splitting/ordering prefix. The
            # source adapter visits prepared layers, never layerless nodes.
            self.assertFalse(work.layerless_nodes)
            self.assertTrue(work.layers)
            nodes = [node for layer in work.layers for node in layer.nodes]
            self.assertTrue(any(len(node.ports) == 2 for node in nodes))
            for node in nodes:
                self.assertEqual(node.type, "NORMAL")
                self.assertEqual(node.properties["PORT_CONSTRAINTS"], "FIXED_ORDER")
                for port in node.ports:
                    port.id, port.pos.x, port.pos.y = 77, -91, -93
            label_and_node_size_processor(work)
            for node in nodes:
                self.assertEqual([port.id for port in node.ports], list(range(len(node.ports))))
                for port in node.ports:
                    self.assertEqual(port.pos.y, node.size.y / 2)
                    self.assertEqual(port.pos.x, node.size.x if port.side == "EAST" else 0)
            calls.append(len(nodes))

        with patch.dict(INTERMEDIATE_PROCESSORS, {"LabelAndNodeSizeProcessor": inject_then_execute_real_node_spacing}):
            actual = execute_kernel_instrumentation(path)
        self.assertEqual(calls, [len(load(path)["graph"]["children"])])
        self.assertTrue(compare_observations(reference, actual, profile="native-basic-layered-v1", request=path)["passed"])
        self.assertTrue(geometry(load(path), actual, case["geometry"])["passed"])

    def test_external_engine_launch_guard_really_runs_inside_the_native_child(self):
        path = SUITE / "requests/project/e04-default-chain-unequal.json"
        # A real pristine public-API/spawn result must pass before the fault.
        reference = load(ORACLE / "e04-default-chain-unequal/run-01/observation.json")
        normal = execute_native(path)
        self.assertTrue(compare_observations(reference, normal, profile="native-basic-layered-v1", request=path)["passed"])
        with self.assertRaises(WorkerExecutionError) as caught:
            execute_native(path, worker_target=attempted_external_process_worker)
        self.assertEqual(caught.exception.code, "WORKER_EXECUTION_FAILED")
        self.assertEqual(caught.exception.message, EXTERNAL_ENGINE_GUARD)


if __name__ == "__main__":
    unittest.main()
