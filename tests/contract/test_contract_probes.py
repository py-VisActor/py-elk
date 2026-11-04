"""Offline checks of captured official facts, never native Python API acceptance."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import diff


class OfficialContractProbeFacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = json.loads((ROOT / "references/e02-contract-probes.json").read_text(encoding="utf-8"))
        cls.probes = {p["id"]: p for p in cls.capture["probes"]}

    def call(self, identity, number=0):
        return self.probes[identity]["observation"]["calls"][number]

    def test_complete_capture_has_unique_ids_and_no_native_acceptance(self):
        self.assertEqual(self.capture["schema"], "py-elk-contract-probes/v1")
        self.assertEqual(self.capture["status"], "CAPTURED")
        self.assertEqual(self.capture["probeCount"], len(self.probes))
        self.assertEqual(self.capture["pythonAlgorithmsVerified"], 0)
        for probe in self.probes.values():
            self.assertEqual(probe["process"]["exitCode"], 0, probe["id"])
            self.assertIsNone(probe["process"]["signal"])
            self.assertIsNone(probe["process"]["spawnError"])
            self.assertTrue(probe["observation"])

    def test_locked_sources_and_real_collector_identity(self):
        lock = json.loads((ROOT / "UPSTREAM.json").read_text(encoding="utf-8"))
        self.assertEqual(self.capture["baseline"]["commit"], lock["javascript"]["commit"])
        self.assertEqual(self.capture["baseline"]["entrypointSha256"], lock["distribution"]["sha256Files"]["lib/elk.bundled.js"])
        self.assertEqual(hashlib.sha256((ROOT / self.capture["tool"]["path"]).read_bytes()).hexdigest(), self.capture["tool"]["sha256"])
        for source in self.capture["sources"]:
            self.assertEqual(source["commit"], lock["javascript"]["commit"])
            self.assertTrue(source["sourceId"])
            expected = lock["sourceSha256"].get(source["path"], lock["distribution"]["sha256Files"].get(source["path"]))
            self.assertEqual(source["sha256"], expected)

    def test_exact_request_bytes_bind_input_and_observation(self):
        for probe in self.probes.values():
            with self.subTest(probe=probe["id"]):
                raw = base64.b64decode(probe["requestBytesBase64"], validate=True)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), probe["requestSha256"])
                self.assertEqual(probe["observation"]["requestSha256"], probe["requestSha256"])
                self.assertTrue(diff(json.loads(raw), probe["input"])["passed"])

    def test_omitted_undefined_and_explicit_values_remain_distinct_descriptors(self):
        self.assertEqual(self.probes["constructor-omitted"]["input"]["constructor"]["kind"], "omitted")
        self.assertEqual(self.probes["constructor-undefined"]["input"]["constructor"]["kind"], "undefined")
        for name, expected in (("null", None), ("false", False), ("zero", 0), ("empty-string", "")):
            form = self.probes["constructor-" + name]["input"]["constructor"]
            self.assertEqual(form["kind"], "value")
            self.assertIs(type(form["value"]), type(expected))
            self.assertEqual(form["value"], expected)
        call = self.call("layout-options-undefined")
        self.assertEqual(call["actualArguments"]["explicitlyUndefinedFields"], ["layoutOptions"])

    def test_constructor_null_is_sync_error_but_falsy_primitive_forms_return(self):
        error = self.probes["constructor-null"]["observation"]["constructor"]
        self.assertEqual(error["outcome"], "threw")
        self.assertEqual(error["returnStyle"], "synchronous_throw")
        self.assertEqual(error["error"]["name"], "TypeError")
        for name in ("omitted", "undefined", "empty-object", "false", "zero", "empty-string"):
            self.assertEqual(self.probes["constructor-" + name]["observation"]["constructor"]["outcome"], "returned")

    def test_call_null_and_missing_graph_have_distinct_error_return_styles(self):
        null_args = self.call("layout-arguments-null")
        missing_graph = self.call("graph-omitted")
        self.assertEqual((null_args["outcome"], null_args["returnStyle"], null_args["error"]["name"]), ("threw", "synchronous_throw", "TypeError"))
        self.assertEqual((missing_graph["outcome"], missing_graph["returnStyle"], missing_graph["error"]["name"]), ("threw", "promise", "Error"))
        self.assertEqual(missing_graph["error"]["message"], "Missing mandatory parameter 'graph'.")

    def test_global_replacement_and_root_precedence_are_observed(self):
        def coordinates(identity):
            nodes = self.call(identity)["result"]["value"]["children"]
            return nodes[0], nodes[1]
        a, b = coordinates("precedence-constructor-default")
        self.assertGreater(b["y"], a["y"])
        a, b = coordinates("precedence-empty-call-replaces")
        self.assertGreater(b["x"], a["x"])
        a, b = coordinates("precedence-call-replaces")
        self.assertLess(b["x"], a["x"])
        a, b = coordinates("precedence-root-local-wins")
        self.assertGreater(b["x"], a["x"])

    def test_successful_graph_side_effects_are_recorded_not_normalized(self):
        for probe in self.probes.values():
            for call in probe["observation"]["calls"]:
                if call["method"] == "layout" and call["outcome"] == "returned":
                    self.assertTrue(diff(call["result"], call["after"]["graph"])["passed"], probe["id"])
                    self.assertTrue(diff(call["before"]["constructor"], call["after"]["constructor"])["passed"], probe["id"])
                    self.assertTrue(diff(call["before"]["arguments"], call["after"]["arguments"])["passed"], probe["id"])

    def test_same_input_logging_is_added_then_cleared(self):
        first, second = self.probes["logging-same-graph-reuse"]["observation"]["calls"]
        self.assertIn("logging", first["after"]["graph"]["value"])
        self.assertTrue(diff(first["after"]["graph"], second["before"]["graph"])["passed"])
        self.assertNotIn("logging", second["after"]["graph"]["value"])

    def test_user_hash_collisions_are_visible_and_business_fields_survive(self):
        for owner in ("root", "child"):
            for name in ("zero", "false", "null"):
                call = self.call("user-hash-" + owner + "-" + name)
                before, after = call["before"]["graph"]["value"], call["after"]["graph"]["value"]
                before, after = (before, after) if owner == "root" else (before["children"][0], after["children"][0])
                self.assertIs(type(after["$H"]), int)
                self.assertFalse(diff(before["$H"], after["$H"])["passed"])
            for name in ("string", "positive-integer"):
                call = self.call("user-hash-" + owner + "-" + name)
                before, after = call["before"]["graph"]["value"], call["after"]["graph"]["value"]
                before, after = (before, after) if owner == "root" else (before["children"][0], after["children"][0])
                self.assertTrue(diff(before["$H"], after["$H"])["passed"])
        call = self.call("user-hash-nested-business")
        before, after = call["before"]["graph"]["value"], call["after"]["graph"]["value"]
        self.assertEqual(after["business"], before["business"])
        self.assertEqual(after["business"]["error"]["stack"], "user-owned stack must survive")
        self.assertIs(after["children"][0]["data"]["$H"], False)

    def test_known_errors_change_only_new_shape_hashes(self):
        for identity in ("error-unknown-endpoint", "error-unknown-algorithm"):
            probe = self.probes[identity]
            self.assertEqual(probe["observation"]["calls"][0]["outcome"], "threw")
            self.assertTrue(probe["flags"][0]["graphOnlyNewShapeHashAdditions"])

    def test_failed_fake_worker_termination_does_not_mean_closed(self):
        for identity in ("lifecycle-terminate-before-layout", "lifecycle-repeat-terminate"):
            calls = self.probes[identity]["observation"]["calls"]
            for call in calls:
                if call["method"] == "terminateWorker":
                    self.assertEqual(call["outcome"], "threw")
                    self.assertEqual(call["error"]["name"], "TypeError")
                    self.assertEqual(call["error"]["message"], "this.worker.terminate is not a function")
            self.assertEqual(calls[-1]["outcome"], "returned")


if __name__ == "__main__":
    unittest.main()
