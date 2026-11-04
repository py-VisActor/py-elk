"""E07 source invariants, including mutations with recomputed receipt hashes."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import load, sha256
import validate_e07_source_bindings as audit
from validate_e05_source_bindings import canonical_sha, json_pointer


def put(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf8"))


class E07SourceBindingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = {lane: load(ROOT / path) for lane, path in audit.DOCUMENTS.items()}
        cls.registry = {c["componentId"]: c for d in cls.documents.values() for c in d["components"]}
        cls.manifest = load(ROOT / audit.MANIFEST)

    def invalid_document(self, lane, mutate):
        doc = copy.deepcopy(self.documents[lane]); mutate(doc)
        doc["componentSeals"] = {c["componentId"]: canonical_sha(c) for c in doc["components"]}
        with self.assertRaises(ValueError): audit.validate_document(doc, lane, ROOT)

    def fixture(self, root):
        for name in audit.evidence_paths(ROOT):
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())

    def test_whole_33_fixed_source_gate_and_full_e06_inheritance_pass(self):
        result = audit.check(ROOT, require_approved=True)
        self.assertEqual(result["status"], "E07_SOURCE_BINDINGS_VALIDATED", result["errors"])
        self.assertEqual(result["componentCounts"], {"A": 4, "B": 3, "R": 26})
        self.assertEqual(result["approvedEvidence"]["approvedComponents"], 33)
        self.assertTrue(result["wholeSourceApproved"])
        self.assertFalse(result["runtimeAcceptanceAssessed"])
        self.assertIs(type(result["pythonAlgorithmsVerified"]), int)
        self.assertEqual(result["pythonAlgorithmsVerified"], 0)

    def test_resealed_missing_actual_proof_ids_cannot_be_vacuous(self):
        for lane in "ABR":
            self.invalid_document(lane, lambda d: d["components"][0].update(guardProofs=[]))
        self.invalid_document("A", lambda d: d["components"][-1]["guardProofs"].pop())

    def test_renewal_inherits_every_old_proof_id_not_an_empty_summary(self):
        self.invalid_document("R", lambda d: d["components"][0]["inheritedComponent"].update(requiredProofIds=[]))
        identity = "intermediate:LongEdgeSplitter"
        index = next(i for i, c in enumerate(self.documents["R"]["components"]) if c["componentId"] == identity)
        old = self.documents["R"]["components"][index]["inheritedComponent"]
        target = json_pointer(load(ROOT / old["artifact"]["path"]), old["jsonPointer"])
        self.assertTrue(target["sourceDerivation"])
        self.invalid_document("R", lambda d: d["components"][index]["inheritedComponent"].update(requiredProofIds=[]))

    def test_resealed_selector_cannot_borrow_another_component_role(self):
        def change(d):
            inherited = d["components"][1]["inheritedComponent"]
            target = json_pointer(load(ROOT / inherited["artifact"]["path"]), "/components/0")
            inherited.update(jsonPointer="/components/0", canonicalComponentSha256=canonical_sha(target),
                             requiredProofIds=[p["id"] for p in target["guardProofs"]])
        self.invalid_document("R", change)

    def test_rebound_junction_getter_selector_keeps_exact_selected_support_role(self):
        def change(d):
            component = next(c for c in d["components"] if c["componentId"] == "components:simple-row-combine")
            link = component["inheritedArtifacts"][0]
            # The full artifact remains genuine; only its selected semantic role changes.
            link["jsonPointer"] = "/components/5/hostMappings/0"
            link["selectedSha256"] = canonical_sha(json_pointer(load(ROOT / link["artifact"]["path"]), link["jsonPointer"]))
        self.invalid_document("B", change)

    def test_complete_direction_baseline_and_ns_kernel_selectors_are_required(self):
        self.invalid_document("A", lambda d: d["components"][0]["immutableSupportEvidence"].pop())
        self.invalid_document("A", lambda d: d["components"][-1]["immutableSupportEvidence"].pop())

    def test_rebound_common_lane_and_component_contexts_fail_independently(self):
        def common(d):
            d["commonSourceContext"]["originalNodeMaximum"] = 9
            d["commonSourceContextSha256"] = canonical_sha(d["commonSourceContext"])
        self.invalid_document("A", common)
        self.invalid_document("R", lambda d: d["sourceContext"].update(scopeId="borrowed"))
        def specific(d):
            c = d["components"][-1]; c["sourceContext"]["phaseInput"] = "arbitrary graph"
            c["sourceContextSha256"] = canonical_sha(c["sourceContext"])
        self.invalid_document("A", specific)

    def test_direction_shared_proofs_and_node_role_denominator_are_not_optional(self):
        self.invalid_document("A", lambda d: d["components"][0]["sharedProofs"].pop())
        self.invalid_document("B", lambda d: d["components"][0].update(role="components:simple-row-combine"))
        self.invalid_document("A", lambda d: d["components"].append(copy.deepcopy(d["components"][0])))

    def test_source_proof_anchors_must_be_bound_and_narrative_nonempty(self):
        self.invalid_document("B", lambda d: d["components"][0]["guardProofs"][0].update(sourceSymbols=["invented helper"]))
        self.invalid_document("R", lambda d: d["components"][0]["guardProofs"][0].update(claims=[]))
        self.invalid_document("A", lambda d: d["components"][0]["guardProofs"][0].update(sourceRefs=[]))

    def test_typed_dependency_identity_order_and_exact_seal_are_checked(self):
        item = copy.deepcopy(self.registry["phase:GREEDY"])
        for deps in ([], [{"componentId": "graph:edge-reversal", "canonicalComponentSha256": "0" * 64, "meaning": "real"}],
                     [{"componentId": "direction:transpose", "canonicalComponentSha256": canonical_sha(self.registry["direction:transpose"]), "meaning": "borrow"}]):
            item["componentDependencies"] = deps
            with self.assertRaises(ValueError): audit.validate_dependencies(item, self.registry)

    def test_review_role_is_fixed_by_component_inventory_not_arbitrary_schema(self):
        for row in self.manifest["approvals"]:
            if row["lane"] in {"A", "R"}:
                review = load(ROOT / row["versionedReview"])
                changed = copy.deepcopy(review); changed["reviewer"] = "V" if row["reviewerLane"] == "B" else "B"
                badrow = copy.deepcopy(row); badrow["reviewerLane"] = changed["reviewer"]
                with self.assertRaises(ValueError): audit.review_binding(changed, badrow, row["componentId"], self.registry)

    def test_review_component_set_does_not_accept_extra_or_mismatched_seal_keys(self):
        row = next(r for r in self.manifest["approvals"] if r["componentId"] == "direction:mirror-x")
        review = load(ROOT / row["versionedReview"])
        for mutate in (lambda x: x["componentSeals"].pop("direction:mirror-y"),
                       lambda x: x["approvedComponents"].append("phase:GREEDY"),
                       lambda x: x["componentDependencies"].pop("direction:mirror-y")):
            changed = copy.deepcopy(review); mutate(changed)
            with self.assertRaises(ValueError): audit.review_binding(changed, row, row["componentId"], self.registry)

    def test_rebound_raw_review_missing_another_approved_component_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root)
            self.assertEqual(audit.check(root, require_approved=True)["errors"], [])
            manifest = load(root / audit.MANIFEST)
            row = next(r for r in manifest["approvals"] if r["componentId"] == "direction:mirror-x")
            path = root / row["versionedReview"]; review = load(path)
            review["approvedComponents"].remove("direction:mirror-y"); review["componentSeals"].pop("direction:mirror-y")
            review["componentDependencies"].pop("direction:mirror-y"); put(path, review)
            for entry in manifest["approvals"]:
                if entry["versionedReview"] == row["versionedReview"]: entry["versionedReviewSha256"] = sha256(path)
            put(root / audit.MANIFEST, manifest)
            self.assertTrue(audit.check(root, require_approved=True)["errors"])

    def test_rebound_current_scope_or_old_complete_baseline_bytes_are_not_replacement_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root)
            path = root / "references/e06-source-components-R.json"
            old = load(path); old["components"][0]["sourceDerivation"] = []; put(path, old)
            # Even rebinding an outer inherited receipt cannot replace the fixed baseline.
            source_path = root / audit.DOCUMENTS["R"]; doc = load(source_path)
            for component in doc["components"]:
                if component["inheritedComponent"]["artifact"]["path"] == "references/e06-source-components-R.json":
                    component["inheritedComponent"]["artifact"]["sha256"] = sha256(path)
            put(source_path, doc)
            self.assertTrue(audit.check(root, require_approved=True)["errors"])

    def test_new_literal_function_bindings_cannot_use_old_semantic_label_exceptions(self):
        raw = b"function actualHelper(){ return 1; }\n"
        doc = {"component": {"sourceId": "s", "symbol": "invented descriptive name", "startLine": 1,
                             "endLine": 1, "spanSha256": "0" * 64}}
        with self.assertRaises(ValueError): audit.validate_symbol_bindings(doc, {"s": raw})
        doc["component"].update(symbol="actualHelper")
        self.assertEqual(audit.validate_symbol_bindings(doc, {"s": raw})["newSemanticLabelExceptions"], 0)

    def test_source_only_receipts_cannot_promote_runtime_or_algorithm_count(self):
        self.invalid_document("R", lambda d: d.update(nativeLayoutImplemented=True))
        self.invalid_document("A", lambda d: d.update(pythonAlgorithmsVerified=True))
        self.invalid_document("B", lambda d: d["components"][0].update(nativeRuntimeAccepted=True))
        with self.assertRaises(ValueError): audit.no_runtime_claims({"wholeE07SourceGateApproved": True})


if __name__ == "__main__":
    unittest.main()
