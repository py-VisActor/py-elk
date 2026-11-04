"""Offline receipt controls. No engine runs and no ignored checkout is needed."""
from contextlib import contextmanager
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_e06_source_bindings as audit
from layout_checks import load, sha256


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


@contextmanager
def fixture(*, partial=False):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name in audit.evidence_paths(ROOT):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        if partial:
            path = root / audit.MANIFEST
            manifest = load(path)
            manifest["approvals"] = [r for r in manifest["approvals"] if r["componentId"] == "graph:edge-reversal"]
            manifest["status"] = "E06_SOURCE_SCOPE_PENDING"
            manifest["globalAlgorithmSourceGate"] = "unverified-for-E06-expansion"
            manifest.pop("finalSourceDocumentsSha256", None)
            save(path, manifest)
        yield root


def row_for(manifest, identity):
    return next(row for row in manifest["approvals"] if row["componentId"] == identity)


class E06SourceBindingsTests(unittest.TestCase):
    def test_full27_is_offline_source_only_with_complete_base_review_chain(self):
        with fixture() as root, patch("subprocess.run", side_effect=AssertionError("offline must not run Git/Node")):
            report = audit.check(root, require_approved=True)
            self.assertEqual(report["status"], "E06_SOURCE_BINDINGS_VALIDATED", report)
            self.assertEqual(report["expectedComponentCounts"], {"A": 8, "B": 4, "R": 15})
            self.assertEqual(report["approvedEvidence"]["approvedComponents"], 27)
            self.assertTrue(report["wholeSourceApproved"])
            self.assertFalse(report["canonicalVerified"])
            self.assertFalse(report["runtimeAcceptanceAssessed"])
            self.assertFalse(report["mathematicalEquivalenceAutomaticallyProved"])
            self.assertIs(type(report["pythonAlgorithmsVerified"]), int)
            self.assertEqual(report["pythonAlgorithmsVerified"], 0)
            for path in (".git", ".local", "test-runs"):
                self.assertFalse((root / path).exists())

    def test_partial_receipts_do_not_approve_whole_slice(self):
        with fixture(partial=True) as root:
            report = audit.check(root)
            self.assertEqual(report["status"], "E06_SOURCE_BINDINGS_PARTIAL", report)
            self.assertFalse(report["wholeSourceApproved"])
            self.assertEqual(audit.check(root, require_approved=True)["status"], "FAIL")

    def test_whole_denominator_cannot_be_redefined_by_removing_or_duplicating_a_row(self):
        with fixture() as root:
            original = load(root / audit.MANIFEST)
            for rows in (original["approvals"][:-1], original["approvals"] + [original["approvals"][0]]):
                changed = copy.deepcopy(original); changed["approvals"] = rows
                save(root / audit.MANIFEST, changed)
                self.assertEqual(audit.check(root, require_approved=True)["status"], "FAIL")

    def test_final_document_binding_is_required_even_after_all_component_seals_match(self):
        with fixture() as root:
            original = load(root / audit.MANIFEST)
            for bad in (None, {}, {path: "0" * 64 for path in audit.DOCUMENTS.values()}):
                changed = copy.deepcopy(original); changed["finalSourceDocumentsSha256"] = bad
                save(root / audit.MANIFEST, changed)
                report = audit.check(root, require_approved=True)
                self.assertEqual(report["status"], "FAIL")
                self.assertIn("final document", " ".join(report["errors"]))

    def test_shared_proof_mutation_is_caught_without_changing_component_hash(self):
        with fixture() as root:
            document = load(root / audit.DOCUMENTS["B"])
            before = audit.canonical_sha(document["components"][0])
            path = root / "references/e05-source-components-B.json"
            inherited = load(path); inherited["components"][0]["scope"]["model"] = "unreviewed wider graph"
            save(path, inherited)
            self.assertEqual(audit.canonical_sha(document["components"][0]), before)
            self.assertEqual(audit.check(root)["status"], "FAIL")

    def test_shared_context_rebinding_does_not_expand_guard_limits(self):
        with fixture() as root:
            path = root / audit.DOCUMENTS["R"]; document = load(path)
            document["commonSourceContext"]["maximumWorkNodes"] = 999
            document["commonSourceContextSha256"] = audit.canonical_sha(document["commonSourceContext"])
            save(path, document)
            manifest = load(root / audit.MANIFEST)
            for row in manifest["approvals"]:
                if row["lane"] == "R": row["sourceContextSha256"] = audit.canonical_sha(audit.source_context(document))
            save(root / audit.MANIFEST, manifest)
            self.assertEqual(audit.check(root)["status"], "FAIL")

    def test_source_role_git_blob_and_boolean_span_line_are_rejected(self):
        with fixture() as root:
            original = load(root / audit.DOCUMENTS["A"])
            for mutate in (lambda d: d["sources"][0].update(kind="candidate-java"),
                           lambda d: d["sources"][0].update(gitBlob="0" * 40),
                           lambda d: d["components"][0]["entryAndAlgorithmHelpers"][0].update(startLine=True),
                           lambda d: d["components"][0]["entryAndAlgorithmHelpers"][0].update(symbol="")):
                document = copy.deepcopy(original); mutate(document)
                with self.assertRaises(ValueError):audit.validate_document(document, "A", root)

    def test_source_read_write_and_guard_anchors_are_not_vacuous(self):
        with fixture() as root:
            original = load(root / audit.DOCUMENTS["A"])
            for mutate in (lambda d: d["components"][0].update(writes=[]),
                           lambda d: d["components"][0]["guardProofs"][0].update(sourceRefs=[]),
                           lambda d: d["components"][0]["guardProofs"][0].update(proof=""),
                           lambda d: d["components"][0]["guardProofs"][0].update(proofRef="unknown")):
                document = copy.deepcopy(original); mutate(document)
                with self.assertRaises(ValueError):audit.validate_document(document, "A", root)

    def test_inherited_component_pointer_and_component_seal_are_checked(self):
        with fixture() as root:
            original = load(root / audit.DOCUMENTS["R"])
            for key, bad in (("jsonPointer", "/components/999"), ("canonicalComponentSha256", "0" * 64)):
                document = copy.deepcopy(original)
                document["components"][0]["inheritedSourceBindings"][0][key] = bad
                with self.assertRaises((ValueError, IndexError)):audit.validate_document(document, "R", root)

    def test_component_dependency_missing_wrong_seal_or_unknown_proof_fails(self):
        documents = [load(ROOT / path) for path in audit.DOCUMENTS.values()]
        registry = {c["componentId"]: c for d in documents for c in d["components"]}
        original = registry["phase:NETWORK_SIMPLEX"]
        for mutate in (lambda c: c.update(componentDependencies=[]),
                       lambda c: c["componentDependencies"][0].update(canonicalComponentSha256="0" * 64),
                       lambda c: c["componentDependencies"][0].update(proofIds=["does-not-exist"])):
            component = copy.deepcopy(original); mutate(component)
            with self.assertRaises(ValueError):audit.validate_dependencies(component, registry)

    def test_manifest_typed_dependency_cannot_disappear_or_bind_unknown_component(self):
        with fixture() as root:
            original = load(root / audit.MANIFEST)
            for bad in ([], [{"componentId": "missing", "canonicalComponentSha256": "0" * 64}]):
                changed = copy.deepcopy(original)
                row_for(changed, "phase:LAYER_SWEEP_BARYCENTER")["componentDependencies"] = bad
                save(root / audit.MANIFEST, changed)
                self.assertEqual(audit.check(root)["status"], "FAIL")

    def test_rebound_independent_review_still_requires_accepted_status_and_real_dependencies(self):
        with fixture() as root:
            path = root / audit.MANIFEST; original = load(path)
            target = row_for(original, "phase:LAYER_SWEEP_BARYCENTER")
            review_path = root / target["versionedReview"]; original_review = load(review_path)
            for mutate in (lambda r: r.update(status="DRAFT"),
                           lambda r: r["components"][0].update(componentDependencies=[])):
                review = copy.deepcopy(original_review); mutate(review);save(review_path, review)
                manifest = copy.deepcopy(original)
                for row in manifest["approvals"]:
                    if row["versionedReview"] == target["versionedReview"]:row["versionedReviewSha256"] = sha256(review_path)
                save(path, manifest)
                self.assertEqual(audit.check(root)["status"], "FAIL")

    def test_full_e05_original_review_history_is_not_replaced_by_current_amendment(self):
        with fixture() as root:
            path = root / audit.base.MANIFEST; manifest = load(path)
            row_for(manifest, "phase:BRANDES_KOEPF").pop("approvalHistory")
            save(path, manifest)
            report = audit.check(root)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("Full E05", " ".join(report["errors"]))

    def test_nested_source_runtime_claims_are_rejected_with_exact_integer_zero(self):
        with fixture() as root:
            original = load(root / audit.DOCUMENTS["A"])
            for bad in ({"nativeRuntimeAccepted": True}, {"pythonAlgorithmsVerified": False},
                        {"runtimeVerified": True}, {"wholeE06SourceGateApproved": True}):
                document = copy.deepcopy(original); document["components"][0]["forged"] = bad
                with self.assertRaises(ValueError):audit.validate_document(document, "A", root)

    def test_unmerged_guard_bytes_and_license_are_immutable(self):
        with fixture() as root:
            path = root / audit.UNMERGED
            raw = path.read_bytes(); path.write_bytes(raw + b"\n")
            self.assertEqual(audit.check(root)["status"], "FAIL")
            path.write_bytes(raw)
            (root / "src/pyelk/_licenses/NOTICE-E06.md").write_bytes(b"unreviewed license")
            self.assertEqual(audit.check(root)["status"], "FAIL")

    def test_required_named_proofs_cannot_be_omitted_from_otherwise_valid_dependencies(self):
        documents = [load(ROOT / path) for path in audit.DOCUMENTS.values()]
        registry = {c["componentId"]: c for d in documents for c in d["components"]}
        for identity in ("phase:NETWORK_SIMPLEX", "intermediate:LongEdgeSplitter"):
            component = copy.deepcopy(registry[identity])
            next(dep for dep in component["componentDependencies"] if "proofIds" in dep).pop("proofIds")
            with self.assertRaisesRegex(ValueError, "proof IDs"):
                audit.validate_dependencies(component, registry)

    def test_unmerged_and_inherited_component_roles_cannot_be_removed_or_swapped(self):
        with fixture() as root:
            document = load(root / audit.DOCUMENTS["A"])
            component = next(c for c in document["components"] if c["componentId"] == "import:json-to-layered")
            component.pop("immutableDefaultUnmerged")
            with self.assertRaisesRegex(ValueError, "unmerged"):
                audit.validate_document(document, "A", root)
            original = load(root / audit.DOCUMENTS["R"])
            for identity in ("phase:LAYER_SWEEP_BARYCENTER", "pipeline:default-processor-configuration"):
                document = copy.deepcopy(original)
                target = next(c for c in document["components"] if c["componentId"] == identity)
                target["inheritedSourceBindings"] = [{"artifact": {"path": audit.base.DOCUMENTS["B"], "sha256": audit.INHERITED[audit.base.DOCUMENTS["B"]]},
                    "componentId": "phase:GREEDY", "jsonPointer": "/components/0",
                    "canonicalComponentSha256": audit.canonical_sha(next(c for c in load(root / audit.base.DOCUMENTS["B"])["components"] if c["componentId"] == "phase:GREEDY"))}]
                with self.assertRaisesRegex(ValueError, "inherit|Inherited|Pipeline"):
                    audit.validate_document(document, "R", root)

    def test_independent_review_context_and_unknown_approval_rows_fail_even_if_rehashed(self):
        with fixture() as root:
            manifest = load(root / audit.MANIFEST)
            for identity in ("phase:NETWORK_SIMPLEX", "intermediate:SelfLoopPreProcessor"):
                row = row_for(manifest, identity); original = load(root / row["versionedReview"])
                changed = copy.deepcopy(original)
                if row["lane"] == "A":
                    changed["approvedComponents"].append("invented-component")
                    changed["componentSeals"]["invented-component"] = "0" * 64
                else:
                    changed["components"].append({"componentId": "invented-component", "status": "ACCEPTED_UNDER_COMPONENT_GUARDS", "canonicalComponentSha256": "0" * 64})
                with self.assertRaises(ValueError):audit.review_binding(changed, row, identity)
                if row["lane"] == "A":
                    changed = copy.deepcopy(original); changed["commonSourceContextSha256"] = "0" * 64
                    with self.assertRaisesRegex(ValueError, "context"):audit.review_binding(changed, row, identity)

    def test_all_thirteen_reviewed_range_labels_are_fixed_descriptions_and_not_callees(self):
        original = load(ROOT / audit.DOCUMENTS["A"])
        records = [(path, span) for path, span in audit.span_records(original) if path in audit.SEMANTIC_LABELS]
        self.assertEqual(len(records), 13)
        for path, span in records:
            role = audit.semantic_label_record(original, path, span)
            self.assertFalse(role["literalCallee"])
            self.assertEqual(role["sourcePath"], "lib/elk-worker.js")
            for update in ({"symbol": span["symbol"] + " invented"},
                           {"startLine": span["startLine"] + 1, "endLine": span["endLine"] + 1}):
                changed = copy.deepcopy(span); changed.update(update)
                with self.assertRaisesRegex(ValueError, "label/location"):
                    audit.semantic_label_record(original, path, changed)
        document = copy.deepcopy(original); document["sources"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "identity/role"):
            audit.semantic_label_record(document, *records[0])

    def test_actual_function_name_is_separate_from_a_valid_span_or_alias_label(self):
        # This miniature helper fixture tests symbol matching only. Complete
        # canonical validation independently requires the actual source SHA.
        raw = b"function target(){ return 1; }\n"
        span = {"sourceId": "fixture", "symbol": "target", "startLine": 1, "endLine": 1,
                "spanSha256": hashlib.sha256(raw).hexdigest(), "functionStartOffset": 0,
                "functionEndOffset": len(raw) - 1, "functionSha256": hashlib.sha256(raw[:-1]).hexdigest(), "offsetUnit": "UTF-16 code units"}
        doc = {"sources": [{"sourceId": "fixture", "sha256": hashlib.sha256(raw).hexdigest()}], "entries": [span]}
        self.assertEqual(audit.validate_canonical(doc, {"fixture": raw})["sources"], 1)
        self.assertEqual(audit.validate_symbol_bindings(doc, {"fixture": raw})["literalSymbolCount"], 1)
        span["symbol"] = "invented"
        with self.assertRaisesRegex(ValueError, "function symbol"):
            audit.validate_symbol_bindings(doc, {"fixture": raw})
        span.pop("functionStartOffset"); span.pop("functionEndOffset"); span.pop("functionSha256"); span.pop("offsetUnit")
        with self.assertRaisesRegex(ValueError, "Literal source symbol"):
            audit.validate_symbol_bindings(doc, {"fixture": raw})
        # A reviewed Property.getDefault namespace alias cannot name a
        # different function, even if its tiny helper fixture bytes are real.
        actual = load(ROOT / audit.DOCUMENTS["A"])
        alias = copy.deepcopy(actual["components"][4]["hostMappings"][1]["sourceSpans"][10])
        tiny = b"function wrongDefault(){}"
        alias["functionStartOffset"] = 0; alias["functionEndOffset"] = len(tiny)
        shaped = {"lane": "A", "sources": actual["sources"], "components": [{}, {}, {}, {},
                  {"hostMappings": [{}, {"sourceSpans": [{}] * 10 + [alias]}]}]}
        with self.assertRaisesRegex(ValueError, "function symbol"):
            audit.validate_symbol_bindings(shaped, {"elkjs-generated-worker": tiny})


if __name__ == "__main__":
    unittest.main()
