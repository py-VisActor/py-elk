"""E03 provenance/claim counterexamples on actual sealed source material."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import load
from validate_e03_foundations import validate_manifest, validate_sources


class FoundationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = load(ROOT / "UPSTREAM.json")
        cls.model = load(ROOT / "references/e03-model-sources.json")
        cls.options = load(ROOT / "references/e03-option-sources.json")
        cls.manifest = load(ROOT / "references/e03-audit.json")

    def source_control(self, mutate, options=False):
        source = copy.deepcopy(self.options if options else self.model)
        schema = source["schema"]
        mutate(source)
        with self.assertRaises((ValueError, KeyError)):
            validate_sources(source, self.lock, schema)

    def manifest_control(self, mutate):
        manifest = copy.deepcopy(self.manifest)
        mutate(manifest)
        with self.assertRaises((ValueError, KeyError)):
            validate_manifest(manifest, self.lock)

    def test_real_receipts_and_manifest(self):
        for source in (self.model, self.options):
            validate_sources(source, self.lock, source["schema"])
        validate_manifest(self.manifest, self.lock)

    def test_source_denominator_cannot_disappear_or_duplicate(self):
        self.source_control(lambda d: d.update(sources=[]))
        self.source_control(lambda d: d["sources"].append(copy.deepcopy(d["sources"][0])))

    def test_source_identity_must_bind_fixed_path_commit_and_bytes(self):
        for key, value in (("path", "lib/not-the-source.js"), ("commit", "0" * 40), ("sha256", "0" * 64)):
            self.source_control(lambda d: d["sources"][0].update({key: value}))

    def test_captured_metadata_cannot_be_relabelled_as_git(self):
        self.source_control(lambda d: next(s for s in d["sources"] if s["kind"] == "captured-official-metadata").update(kind="locked-git-source"), options=True)

    def test_invalid_range_or_boolean_line_number_is_rejected(self):
        for start, end in ((False, 2), (0, 1), (2, 1), (1, True)):
            self.source_control(lambda d: d["sources"][0].update(lineRanges=[{"startLine": start, "endLine": end}]))

    def test_claims_cannot_be_empty_duplicate_or_undifferentiated(self):
        self.source_control(lambda d: d.update(claims=[]))
        self.source_control(lambda d: d["claims"].append(copy.deepcopy(d["claims"][0])))
        self.source_control(lambda d: [c.update(kind="host-design") for c in d["claims"]])

    def test_source_fact_requires_known_reference_and_cannot_hide_runtime_claim(self):
        self.source_control(lambda d: d["claims"][0].update(sourceIds=["invented"]))
        self.source_control(lambda d: d["claims"][0].update(sourceIds=[]))
        self.source_control(lambda d: d["claims"][0].update(nativeLayoutImplemented=True))

    def test_claim_role_binding_and_description_type_cannot_be_forged(self):
        self.source_control(lambda d: d["claims"][0].update(description={"nativeLayoutImplemented": True}))
        self.source_control(lambda d: d["claims"][-1].update(sourceIds=""))
        self.source_control(lambda d: d.update(claims=[d["claims"][0], d["claims"][-1]]))
        self.source_control(lambda d: d["sources"][0].update(kind="unknown-source-kind"))

    def test_option_receipt_requires_nine_exact_schema_only_entries(self):
        self.source_control(lambda d: d.update(options=[]), options=True)
        self.source_control(lambda d: d["options"][0].update(layoutImplemented=True), options=True)
        self.source_control(lambda d: d["options"][0].update(status="runtime-executed"), options=True)
        self.source_control(lambda d: d["options"][-1].update(declaredDefault=7), options=True)
        self.source_control(lambda d: d["options"][0].update(declaredDefault="org.eclipse.elk.layered"), options=True)
        self.source_control(lambda d: d["options"][0].update(alias="algorithm", sourceIds=[]), options=True)

    def test_frozen_design_cannot_hide_revision_direction_or_parsing_policy(self):
        for key, value in (("status", "draft"), ("revision", True), ("directionRemains", "RIGHT"),
                           ("path", "docs/other.md"), ("algorithmFallbackOrigin", "default")):
            self.source_control(lambda d: d["design"].update({key: value}), options=True)

    def test_model_evidence_must_be_sealed_and_bound_to_actual_decision(self):
        self.source_control(lambda d: d.update(status="unsealed"))
        self.source_control(lambda d: d.update(designDocument="README.md"))

    def test_host_provenance_cannot_promote_algorithms_or_source_gate(self):
        self.source_control(lambda d: d.update(pythonAlgorithmsVerified=1))
        self.source_control(lambda d: d.update(pythonAlgorithmsVerified=False))
        self.source_control(lambda d: d.update(algorithmSourceGate="verified"))
        self.source_control(lambda d: d.update(nativeLayoutImplemented=True))

    def test_manifest_runtime_claims_are_exact_and_complete(self):
        self.manifest_control(lambda d: d["runtimeClaims"].update(nativeLayoutImplemented=True))
        self.manifest_control(lambda d: d["runtimeClaims"].update(randomSequenceAccepted=True))
        self.manifest_control(lambda d: d["runtimeClaims"].update(internalModelAvailable=1))
        self.manifest_control(lambda d: d["runtimeClaims"].pop("lifecycleAccepted"))

    def test_component_kind_or_denominator_cannot_be_forged(self):
        self.manifest_control(lambda d: d["components"].pop())
        self.manifest_control(lambda d: d["components"].append(copy.deepcopy(d["components"][0])))
        self.manifest_control(lambda d: d["components"][0].update(layoutAlgorithm=True))
        self.manifest_control(lambda d: d["components"][0].update(symbol="NotImplemented"))

    def test_policy_does_not_hide_identity_ownership_or_registry_boundary(self):
        for key, value in (("booleanOrFloatIds", True), ("inputAndExportCopies", "shallow"),
                           ("diagnosticOptionCount", 9), ("directionDefault", "RIGHT"),
                           ("runtimeReadsReferences", True), ("geometryAndLayoutAccepted", True)):
            self.manifest_control(lambda d: d["policy"].update({key: value}))


if __name__ == "__main__":
    unittest.main()
