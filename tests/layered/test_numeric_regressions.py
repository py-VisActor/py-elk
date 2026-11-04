"""Offline regressions bound to real fixed-elkjs observations, never runtime data.

The 12 authored numeric cases supplement the frozen E04 V21 suite. The thirteenth
case records a JS importer error and tests admission only; it claims no native
error or lifecycle compatibility. No Node installation or network is required.
"""
import asyncio
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from pyelk import ELK
from pyelk._errors import UnsupportedFeatureError, OptionValidationError
from pyelk.algorithms.layered.scope import validate_slice
from pyelk.execution import create_context
from layout_checks import compare_observations, geometry, SCHEMA


PACK = ROOT / "references/e04-numeric-regressions.json"
BUNDLED_SHA = "b1032b7cfd2a57c54c6f0e8369d7665e19a579954f7cd20a6dae28f1912ea0d7"
WORKER_SHA = "275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86"


def decoded(case):
    request_bytes = base64.b64decode(case["requestBytesBase64"], validate=True)
    observation_bytes = base64.b64decode(case["rawObservationBytesBase64"], validate=True)
    return request_bytes, json.loads(request_bytes), observation_bytes, json.loads(observation_bytes)


class FixedNumericOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_all_thirteen_original_byte_receipts_and_source_identities(self):
        self.assertEqual(self.pack["schema"], "py-elk-e04-numeric-regressions/v1")
        self.assertEqual(self.pack["baseline"]["version"], "0.12.1")
        self.assertEqual(self.pack["baseline"]["commit"], "624ae90aa37110033a8af59c5ccbb292708b4317")
        self.assertEqual(self.pack["baseline"]["workerSha256"], WORKER_SHA)
        self.assertEqual(self.pack["baseline"]["bundledSha256"], BUNDLED_SHA)
        cases = self.pack["cases"]
        self.assertEqual(len(cases), 13)
        self.assertEqual(len({case["id"] for case in cases}), 13)
        self.assertEqual(sum(case["kind"] == "positive" for case in cases), 12)
        self.assertEqual(sum(case["kind"] == "domain-negative" for case in cases), 1)
        for case in cases:
            with self.subTest(case=case["id"]):
                request_bytes, request, observation_bytes, observation = decoded(case)
                self.assertEqual(hashlib.sha256(request_bytes).hexdigest(), case["requestSha256"])
                self.assertEqual(hashlib.sha256(observation_bytes).hexdigest(), case["rawObservationSha256"])
                self.assertEqual(request["schema"], "py-elk-layout-request/v1")
                self.assertEqual(observation["schema"], SCHEMA)
                self.assertEqual(observation["requestSha256"], case["requestSha256"])
                self.assertEqual(observation["engine"], case["engine"])
                self.assertEqual(observation["engine"]["name"], "elkjs")
                self.assertEqual(observation["engine"]["version"], "0.12.1")
                self.assertEqual(observation["engine"]["entrypoint"], "lib/elk.bundled.js")
                self.assertEqual(observation["engine"]["entrypointSha256"], BUNDLED_SHA)
                self.assertEqual(observation["outcome"], case["expectedReferenceOutcome"])
                self.assertEqual(case["capture"]["exitCode"], 0)
                # FakeWorker cleanup failure is an actual receipt, never a close pass.
                self.assertEqual(observation["termination"], {
                    "outcome": "threw", "name": "TypeError",
                    "message": "this.worker.terminate is not a function",
                })

    def test_twelve_real_native_results_match_public_contract_exactly_and_geometry(self):
        for case in self.pack["cases"]:
            if case["kind"] != "positive":
                continue
            with self.subTest(case=case["id"]):
                request_bytes, request, _, reference = decoded(case)
                original = copy.deepcopy(request)
                engine = ELK(request["constructor"])
                try:
                    result = asyncio.run(engine.layout(request["graph"], request["layoutArguments"]))
                finally:
                    engine.terminateWorker()
                actual = {
                    "schema": SCHEMA, "engine": {"name": "pyelk"},
                    "requestSha256": case["requestSha256"], "outcome": "returned",
                    "result": result, "inputAfter": request["graph"],
                    "constructorAfter": request["constructor"], "argumentsAfter": request["layoutArguments"],
                }
                comparison = compare_observations(reference, actual, profile="native-basic-layered-v1", request=request_bytes)
                self.assertTrue(comparison["passed"], comparison)
                self.assertTrue(comparison["publicContract"]["exact"]["passed"], comparison)
                self.assertTrue(comparison["inputPreservation"]["preserved"], comparison)
                # Literal JS mutation/hash differences remain visible in the strict report.
                self.assertFalse(comparison["rawStrict"]["passed"])
                self.assertTrue(comparison["adaptations"])
                constraints = geometry(original, actual, case["geometryPolicy"])
                self.assertTrue(constraints["passed"], constraints)
                self.assertEqual(request, original)
                self.assertEqual(result["business"], original["graph"]["business"])

    def test_mapping_padding_remains_e03_host_convenience_and_e04_domain_negative(self):
        negative = [case for case in self.pack["cases"] if case["kind"] == "domain-negative"]
        self.assertEqual(len(negative), 1)
        _, request, _, reference = decoded(negative[0])
        original = copy.deepcopy(request)
        self.assertEqual(reference["error"], {
            "name": "Error",
            "message": "java.lang.Error: Severe implementation error in the Json to ElkGraph importer.",
        })
        context = create_context(request["graph"], constructor=request["constructor"], layout_arguments=request["layoutArguments"])
        parsed = context.resolved_options.values["org.eclipse.elk.padding"]
        self.assertEqual((parsed.top, parsed.right, parsed.bottom, parsed.left), (12, 12, 12, 12))
        with self.assertRaises(UnsupportedFeatureError) as caught:
            validate_slice(context)
        self.assertEqual((caught.exception.code, caught.exception.path), ("UNSUPPORTED_SLICE", "/layoutOptions/elk.padding"))
        engine = ELK(request["constructor"])
        try:
            with self.assertRaises(OptionValidationError) as public_error:
                asyncio.run(engine.layout(request["graph"], request["layoutArguments"]))
            self.assertEqual(public_error.exception.code,'LOCAL_PROPERTY_SCALAR_REQUIRED')
            self.assertEqual(public_error.exception.path,'/layoutOptions/elk.padding')
        finally:
            engine.terminateWorker()
        self.assertEqual(request, original)


if __name__ == "__main__":
    unittest.main()
