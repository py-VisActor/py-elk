"""Independent metadata negative controls using the actual official E02 corpus."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import load
from validate_e02_contract import validate_definition, validate_manifest, validate_probes


class ProbeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = load(ROOT / "UPSTREAM.json")
        cls.bundle = load(ROOT / "references/e02-contract-probes.json")
        cls.definition = load(ROOT / "references/native-contract.json")

    def test_real_official_corpus_and_frozen_contract(self):
        probes = validate_probes(self.bundle, self.lock)
        validate_definition(self.definition, probes, self.lock)
        self.assertEqual(len(probes), self.bundle["probeCount"])

    def test_manifest_cannot_hide_runtime_claims_denominator_or_raw_boundary(self):
        original = load(ROOT / "references/e02-audit.json")
        validate_manifest(original, self.definition, self.bundle)
        mutations = [lambda m: m["runtimeClaims"].update(publicApiAccepted=True),
                     lambda m: m.update(probeCount=1), lambda m: m.update(sourceRecords=False),
                     lambda m: m["comparison"].update(rawStrictRetained=False),
                     lambda m: m["comparison"].update(lifecycleAcceptance="accepted"),
                     lambda m: m["comparison"].update(inputPreservation="coordinateTolerance"),
                     lambda m: m["comparison"]["coordinates"].update(absTol=100),
                     lambda m: m["comparison"].update(geometryAndDeterminism="accepted by profile"),
                     lambda m: m.update(algorithmSourceGate="verified")]
        for mutate in mutations:
            manifest = copy.deepcopy(original)
            mutate(manifest)
            with self.assertRaises(ValueError):
                validate_manifest(manifest, self.definition, self.bundle)

    def probe_control(self, mutate):
        bundle = copy.deepcopy(self.bundle)
        mutate(bundle)
        with self.assertRaises((ValueError, KeyError)):
            validate_probes(bundle, self.lock)

    def definition_control(self, mutate):
        definition = copy.deepcopy(self.definition)
        mutate(definition)
        with self.assertRaises((ValueError, KeyError)):
            validate_definition(definition, validate_probes(self.bundle, self.lock), self.lock)

    def test_probe_dropped_without_denominator_update(self):
        self.probe_control(lambda b: b["probes"].pop())

    def test_probe_duplicate_identity(self):
        self.probe_control(lambda b: b["probes"][1].update(id=b["probes"][0]["id"]))

    def test_request_byte_tamper_and_parsed_input_tamper(self):
        self.probe_control(lambda b: b["probes"][0].update(requestBytesBase64=base64.b64encode(b'{}').decode()))
        self.probe_control(lambda b: b["probes"][0]["input"].update(id="invented"))

    def test_boolean_and_number_are_not_interchangeable_in_request(self):
        bundle = copy.deepcopy(self.bundle)
        probe = next(p for p in bundle["probes"] if p["id"] == "constructor-false")
        probe["input"]["constructor"]["value"] = 0
        with self.assertRaises(ValueError):
            validate_probes(bundle, self.lock)

    def test_forged_observation_request_identity(self):
        self.probe_control(lambda b: b["probes"][0]["observation"].update(requestSha256="0" * 64))

    def test_failed_or_boolean_exit_cannot_be_captured(self):
        for exit_code in (1, None, False):
            self.probe_control(lambda b: b["probes"][0]["process"].update(exitCode=exit_code))

    def test_unknown_timeout_or_method_cannot_count(self):
        self.probe_control(lambda b: b["probes"][0]["observation"]["calls"][0].update(outcome="timeout"))
        self.probe_control(lambda b: b["probes"][0]["observation"]["calls"][0].update(method="terminateWorker"))

    def test_final_termination_timeout_cannot_count_even_with_exit_zero(self):
        self.probe_control(lambda b: b["probes"][0]["observation"]["finalTermination"].update(outcome="timed_out"))
        self.probe_control(lambda b: b["probes"][0]["observation"].pop("finalTermination"))

    def test_official_probe_cannot_claim_native_python_acceptance(self):
        self.probe_control(lambda b: b.update(pythonAlgorithmsVerified=1))
        self.definition_control(lambda d: d["runtimeClaims"].update(publicApiAccepted=True))

    def test_nested_host_and_error_design_cannot_claim_runtime_acceptance(self):
        for key in ("termination", "concurrency", "cancellation"):
            self.definition_control(lambda d: d["hostDesign"][key].update(accepted=True))
        self.definition_control(lambda d: d["hostDesign"]["concurrency"].update(cpuParallelismClaim=True))
        self.definition_control(lambda d: d["errorContract"].update(runtimeImplementation="implemented"))

    def test_source_and_fact_receipts_cannot_be_empty_or_duplicate(self):
        for key in ("sourceEvidence", "observations"):
            self.definition_control(lambda d: d.update({key: []}))
            self.definition_control(lambda d: d[key].append(copy.deepcopy(d[key][0])))
        self.definition_control(lambda d: d["observations"][0].update(probes=[]))
        self.definition_control(lambda d: d["observations"][0].update(sourceIds=["invented"]))

    def test_thrown_outcome_requires_exact_error_fields(self):
        def remove_error(bundle, group):
            for probe in bundle["probes"]:
                record = probe["observation"]["constructor"] if group == "constructor" else next(
                    (call for call in probe["observation"]["calls"] if call["outcome"] == "threw"), None)
                if record and record["outcome"] == "threw":
                    record.pop("error")
                    return
            self.fail("Real probe corpus lacks a thrown outcome")
        for group in ("constructor", "calls"):
            self.probe_control(lambda b: remove_error(b, group))

    def test_draft_or_unsealed_contract_cannot_be_accepted(self):
        self.definition_control(lambda d: d.update(status="draft"))
        self.definition_control(lambda d: d.update(evidenceSealStatus="pending"))

    def test_wildcard_private_field_rule_cannot_replace_shape_paths(self):
        self.definition_control(lambda d: d["adaptations"][1].update(allowedReferencePaths=["/**/$H"]))

    def test_raw_strict_or_lifecycle_boundary_cannot_disappear(self):
        self.definition_control(lambda d: d["reportContract"]["fields"].remove("rawStrict"))
        self.definition_control(lambda d: d["reportContract"].update(lifecycleAcceptance="accepted"))

    def test_stale_fact_receipt_is_rejected(self):
        self.definition_control(lambda d: d["observations"][0]["probes"][0].update(rawObservationSha256="0" * 64))

    def test_request_reserialization_is_not_original_byte_identity(self):
        bundle = copy.deepcopy(self.bundle)
        probe = bundle["probes"][0]
        raw = json.dumps(probe["input"], separators=(",", ":")).encode()
        self.assertNotEqual(hashlib.sha256(raw).hexdigest(), probe["requestSha256"])
        probe["requestBytesBase64"] = base64.b64encode(raw).decode()
        with self.assertRaises(ValueError):
            validate_probes(bundle, self.lock)


if __name__ == "__main__":
    unittest.main()
