"""Partial source/approval negatives; offline fixtures never run an engine."""
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
from layout_checks import load, sha256
import validate_e05_source_bindings as audit
from validate_e04_source_bindings import validate_canonical


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


@contextmanager
def offline_fixture(*, partial=True):
    """Versioned-only partial-approval fixture, independent of live progress.

    Keep the five initial explicit approvals to exercise a partial gate even
    after root approves the full source proposal. Never derive its denominator
    from the mutable fixture or run ignored observations/engines.
    """
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = load(ROOT / audit.MANIFEST)
        if partial:
            manifest["approvals"] = [row for row in manifest["approvals"]
                                     if row["componentId"] in audit.REQUIRED_APPROVAL_IDS]
            manifest["status"] = "E05_SOURCE_SCOPE_PENDING"
            manifest["globalAlgorithmSourceGate"] = "unverified-for-E05-expansion"
        paths = {audit.MANIFEST, audit.SCOPE, *audit.LICENSES, *audit.INHERITED}
        paths |= {path for path in audit.AUXILIARY if (ROOT / path).is_file()}
        paths |= {path for path in audit.DOCUMENTS.values() if (ROOT / path).is_file()}
        paths |= audit.versioned_review_paths(manifest)
        for name in paths:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        save(root / audit.MANIFEST, manifest)
        yield root


class SourceMetadataTests(unittest.TestCase):
    def test_structured_component_and_review_dependencies_cannot_be_dropped_or_rebound(self):
        for identity in audit.NS_DEPENDENTS:
            for bad in (None, {}, {"missing-component": audit.NS_SEAL}, {"phase:NETWORK_SIMPLEX": "0" * 64}):
                with self.subTest(component=identity, dependency=bad), offline_fixture(partial=False) as root:
                    path = root / audit.MANIFEST; manifest = load(path)
                    row = next(r for r in manifest["approvals"] if r["componentId"] == identity)
                    if bad is None:
                        row.pop("componentDependencies")
                    else:
                        row["componentDependencies"] = bad
                    save(path, manifest)
                    report = audit.check(root, require_approved=True)
                    self.assertEqual(report["status"], "FAIL", report)
                    self.assertIn("dependency", " ".join(report["errors"]))
        for bad in (None, {}, {"componentId": "missing-component", "canonicalComponentSha256": "0" * 64, "basis": "fake"}):
            with offline_fixture(partial=False) as root:
                manifest = load(root / audit.MANIFEST)
                row = next(r for r in manifest["approvals"] if r["componentId"] == "phase:LAYER_SWEEP_BARYCENTER")
                path = root / row["versionedReview"]; review = load(path)
                if bad is None:
                    review.pop("dependency")
                else:
                    review["dependency"] = bad
                save(path, review)
                for item in manifest["approvals"]:
                    if item["versionedReview"] == row["versionedReview"]:
                        item["versionedReviewSha256"] = sha256(path)
                save(root / audit.MANIFEST, manifest)
                self.assertEqual(audit.check(root, require_approved=True)["status"], "FAIL")

    def test_bk_amendment_must_retain_its_versioned_full_source_review(self):
        for change in (lambda row: row.pop("approvalHistory"),
                       lambda row: row["approvalHistory"][0]["previousApproval"].update(canonicalComponentSha256="0" * 64),
                       lambda row: row["approvalHistory"][0]["previousApproval"].update(versionedReviewSha256="0" * 64)):
            with offline_fixture(partial=False) as root:
                path = root / audit.MANIFEST; manifest = load(path)
                change(next(r for r in manifest["approvals"] if r["componentId"] == "phase:BRANDES_KOEPF"))
                save(path, manifest)
                self.assertEqual(audit.check(root, require_approved=True)["status"], "FAIL")
        with offline_fixture(partial=False) as root:
            manifest = load(root / audit.MANIFEST)
            row = next(r for r in manifest["approvals"] if r["componentId"] == "phase:BRANDES_KOEPF")
            path = root / row["versionedReview"]; review = load(path)
            review["priorFullReview"]["sha256"] = "0" * 64
            save(path, review); row["versionedReviewSha256"] = sha256(path)
            save(root / audit.MANIFEST, manifest)
            self.assertEqual(audit.check(root, require_approved=True)["status"], "FAIL")

    def test_whole_source_gate_binds_all_three_final_documents_without_runtime_claim(self):
        with offline_fixture(partial=False) as root, patch("subprocess.run", side_effect=AssertionError("No engine offline")):
            report = audit.check(root, require_approved=True)
            self.assertEqual(report["status"], "E05_SOURCE_BINDINGS_VALIDATED", report)
            self.assertEqual(report["approvedEvidence"]["approvedComponents"], 22)
            self.assertTrue(report["wholeSourceApproved"])
            self.assertFalse(report["canonicalVerified"])
            self.assertFalse(report["runtimeAcceptanceAssessed"])
            path = root / audit.MANIFEST
            for bad in (None, {}, {p: "0" * 64 for p in audit.DOCUMENTS.values()}):
                manifest = load(path)
                manifest["finalSourceDocumentsSha256"] = bad
                save(path, manifest)
                changed = audit.check(root, require_approved=True)
                self.assertEqual(changed["status"], "FAIL", changed)
                self.assertIn("final document", " ".join(changed["errors"]))

    def test_partial_positive_is_versioned_only_and_cannot_authenticate_whole_gate(self):
        with offline_fixture() as root, patch("subprocess.run", side_effect=AssertionError("No Git/Node offline")):
            report = audit.check(root)
            self.assertEqual(report["status"], "E05_SOURCE_BINDINGS_PARTIAL", report)
            self.assertTrue(report["fullDenominatorFrozen"])
            self.assertEqual(report["expectedComponentCounts"], {"A": 17, "B": 4, "R": 1})
            self.assertFalse(report["wholeSourceApproved"])
            self.assertFalse(report["canonicalVerified"])
            self.assertIs(report["runtimeAcceptanceAssessed"], False)
            self.assertIs(type(report["pythonAlgorithmsVerified"]), int)
            self.assertEqual(report["pythonAlgorithmsVerified"], 0)
            self.assertFalse((root / "test-runs").exists())
            self.assertFalse((root / ".local").exists())
            self.assertFalse((root / ".git").exists())
            self.assertEqual(audit.check(root, require_approved=True)["status"], "FAIL")

    def test_dropping_a_known_component_cannot_make_its_own_denominator(self):
        with offline_fixture() as root:
            path = root / audit.DOCUMENTS["A"]; document = load(path)
            document["components"] = [c for c in document["components"] if c["componentId"] != "intermediate:LongEdgeJoiner"]
            document["componentSeals"].pop("intermediate:LongEdgeJoiner")
            save(path, document)
            report = audit.check(root)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("denominator", " ".join(report["errors"]))

    def test_source_role_wrong_blob_and_empty_symbol_are_rejected(self):
        for change in (lambda d: d["sources"][0].update(kind="candidate-Java-source"),
                       lambda d: d["sources"][0].update(gitBlob="0" * 40),
                       lambda d: d["components"][0]["entryAndAlgorithmHelpers"][0].update(symbol="")):
            with offline_fixture() as root:
                document = load(root / audit.DOCUMENTS["A"]); change(document)
                with self.assertRaises(ValueError):audit.validate_document(document, "A", root)

    def test_shared_source_registry_change_is_rejected_even_with_rebound_context(self):
        with offline_fixture() as root:
            path = root / audit.DOCUMENTS["A"]; document = load(path)
            old_seal = audit.canonical_sha(document["components"][0])
            document["sources"][0]["path"] = "src/other-implementation.js"
            save(path, document)
            manifest = load(root / audit.MANIFEST)
            for approval in manifest["approvals"]:
                if approval["lane"] == "A":
                    approval["sourceContextSha256"] = audit.canonical_sha(audit.source_context(document))
            save(root / audit.MANIFEST, manifest)
            self.assertEqual(audit.canonical_sha(document["components"][0]), old_seal)
            self.assertEqual(audit.check(root)["status"], "FAIL")

    def test_inherited_shared_proof_change_cannot_hide_behind_same_component_hash(self):
        with offline_fixture() as root:
            document = load(root / audit.DOCUMENTS["B"])
            before = audit.canonical_sha(document["components"][0])
            path = root / "references/e04-source-components-B.json"
            inherited = load(path); inherited["components"][0]["observedTransitiveHelperDispositions"][0]["meaning"] = "wrong shared proof"
            save(path, inherited)
            self.assertEqual(audit.canonical_sha(document["components"][0]), before)
            report = audit.check(root)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("shared proof", " ".join(report["errors"]))

    def test_embedded_host_proof_change_changes_component_seal(self):
        with offline_fixture() as root:
            path = root / audit.DOCUMENTS["A"]; document = load(path)
            component = document["components"][0]
            component["hostMappings"][1]["semantics"] = "Read every mutable default as one global shared object"
            document["componentSeals"][component["componentId"]] = audit.canonical_sha(component)
            save(path, document)
            report = audit.check(root)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("seal", " ".join(report["errors"]))

    def test_inherited_pointer_cannot_be_vacuous_or_escape_source_registry(self):
        with offline_fixture() as root:
            component = load(root / audit.DOCUMENTS["B"])["components"][0]
            component["hostMappingRefs"][0]["jsonPointer"] = "/not-a-real-proof"
            with self.assertRaises(KeyError):audit.inherited_artifacts(component, root)
            component["hostMappingRefs"][0]["artifact"]["path"] = "../outside.json"
            with self.assertRaises(ValueError):audit.inherited_artifacts(component, root)

    def test_missing_or_string_instead_of_host_proof_spans_is_not_a_proof(self):
        for bad in ([], "nonempty-but-not-an-array"):
            with offline_fixture() as root:
                document = load(root / audit.DOCUMENTS["A"])
                document["components"][0]["hostMappings"][0]["sourceSpans"] = bad
                with self.assertRaises(ValueError):audit.validate_document(document, "A", root)

    def test_invented_local_proof_and_unbound_guard_symbol_are_not_closure(self):
        with offline_fixture() as root:
            document = load(root / audit.DOCUMENTS["A"])
            document["components"][0]["sourceDerivation"][0]["proofRef"] = "invented-proof"
            with self.assertRaises(ValueError):audit.validate_document(document, "A", root)
            document = load(root / audit.DOCUMENTS["B"])
            document["components"][0]["guardProofs"][0]["sourceSymbols"] = ["unbound-source-function"]
            with self.assertRaises(ValueError):audit.validate_document(document, "B", root)

    def test_narrative_consequences_cannot_replace_bounded_source_proofs(self):
        with offline_fixture() as root:
            original = load(root / audit.DOCUMENTS["A"])
            audit.validate_document(original, "A", root)
            for component_id, proof_id in (
                ("intermediate:InnermostNodeMarginCalculator", "MG-G1-REAL-UNION"),
                ("import:json-to-layered", "IMP-G1-ORDER-AND-IDENTITY")):
                changed = copy.deepcopy(original)
                component = next(c for c in changed["components"] if c["componentId"] == component_id)
                proof = next(p for p in component["guardProofs"] if p["id"] == proof_id)
                proof.pop("sourceRefs")
                with self.assertRaises(ValueError):audit.validate_document(changed, "A", root)
            changed = copy.deepcopy(original)
            component = next(c for c in changed["components"] if c["componentId"] == "intermediate:InnermostNodeMarginCalculator")
            component["guardProofs"][0]["id"] = "renamed-missing-union-anchor"
            with self.assertRaises(ValueError):audit.validate_document(changed, "A", root)
            changed = copy.deepcopy(original)
            component = next(c for c in changed["components"] if c["componentId"] == "intermediate:LabelAndNodeSizeProcessor")
            component["newObservedHelperMappings"] = []
            with self.assertRaises(ValueError):audit.validate_document(changed, "A", root)

    def test_review_ids_status_and_seals_are_semantic_not_just_new_sha(self):
        for change in (lambda d: d.update(status="draft"), lambda d: d.update(approvedComponents=[]),
                       lambda d: d["componentSeals"].update({"graph:indexed-target": "0" * 64}),
                       lambda d: d.update(wholeE05SourceGateApproved=True)):
            with offline_fixture() as root:
                manifest = load(root / audit.MANIFEST)
                row = next(r for r in manifest["approvals"] if r["componentId"] == "graph:indexed-target")
                path = root / row["versionedReview"]; review = load(path); change(review); save(path, review)
                for item in manifest["approvals"]:
                    if item["versionedReview"] == row["versionedReview"]:
                        item["versionedReviewSha256"] = sha256(path)
                save(root / audit.MANIFEST, manifest)
                self.assertEqual(audit.check(root)["status"], "FAIL")

    def test_partial_manifest_cannot_promote_runtime_or_erase_whole_denominator(self):
        for change in (lambda d: d["approvals"][0].update(runtimeAccepted=True),
                       lambda d: d.update(globalAlgorithmSourceGate="verified", status="E05_SOURCE_SCOPE_VERIFIED"),
                       lambda d: d["approvals"].append(copy.deepcopy(d["approvals"][0]))):
            with offline_fixture() as root:
                manifest = load(root / audit.MANIFEST); change(manifest); save(root / audit.MANIFEST, manifest)
                self.assertEqual(audit.check(root)["status"], "FAIL")

    def test_context_transition_cannot_remove_history_or_invent_canonical_identity(self):
        for change in (lambda r: r.pop("sourceContextHistory"),
                       lambda r: r["sourceContextHistory"][0].update(previousSha256="0" * 64),
                       lambda r: r["sourceContextHistory"][0]["canonicalSourceIdentityChecks"][0].update(gitBlob="0" * 40)):
            with offline_fixture() as root:
                manifest = load(root / audit.MANIFEST)
                change(next(r for r in manifest["approvals"] if r["componentId"] == "phase:GREEDY"))
                save(root / audit.MANIFEST, manifest)
                self.assertEqual(audit.check(root)["status"], "FAIL")

    def test_planned_module_path_is_lexical_and_cannot_claim_existence(self):
        with offline_fixture() as root:
            document = load(root / audit.DOCUMENTS["B"])
            component = next(c for c in document["components"] if c["componentId"] == "phase:LAYER_SWEEP_BARYCENTER")
            self.assertFalse((root / component["plannedPythonModule"]).exists())
            audit.validate_document(document, "B", root)
            for key, value in (("plannedPythonModule", ""), ("plannedPythonModule", "../outside.py"), ("existsClaimed", True)):
                changed = copy.deepcopy(document)
                next(c for c in changed["components"] if c["componentId"] == component["componentId"])[key] = value
                with self.assertRaises(ValueError):audit.validate_document(changed, "B", root)


def tiny_fixture(call="beta"):
    source = "// astral character: 😀\nfunction alpha(){\n  " + call + "();\n}\nfunction beta(){\n  return 1;\n}\n"
    raw = source.encode("utf-8"); rows = source.splitlines()
    def span(name, first, last):
        a = source.index("function " + name); b = source.index("\n}", a) + 2
        return {"sourceId": "tiny", "symbol": name, "startLine": first, "endLine": last,
                "spanSha256": hashlib.sha256(("\n".join(rows[first-1:last]) + "\n").encode()).hexdigest(),
                "functionStartOffset": len(source[:a].encode("utf-16-le")) // 2,
                "functionEndOffset": len(source[:b].encode("utf-16-le")) // 2,
                "offsetUnit": "UTF-16 code units", "functionSha256": hashlib.sha256(source[a:b].encode()).hexdigest()}
    a, b = span("alpha", 2, 4), span("beta", 5, 7)
    document = {"sources": [{"sourceId": "tiny", "sha256": hashlib.sha256(raw).hexdigest()}],
                "functions": [a, b], "calls": [{"caller": "alpha", "callee": "beta", "callSiteLines": [3], "calleeSpan": b}]}
    return document, {"tiny": raw}


class CanonicalSourceTests(unittest.TestCase):
    def test_utf16_and_lexical_calls_work_without_git_node_or_upstream(self):
        document, blobs = tiny_fixture()
        self.assertEqual(validate_canonical(document, blobs)["staticCallEdges"], 1)
        audit.validate_function_line_alignment(document, blobs)

    def test_correct_hash_of_another_function_does_not_bind_this_lf_span(self):
        document, blobs = tiny_fixture(); a, b = document["functions"]
        for key in ("functionStartOffset", "functionEndOffset", "functionSha256"):
            a[key] = b[key]
        # Both individual byte hashes are real; their asserted relationship is false.
        validate_canonical(document, blobs)
        with self.assertRaises(ValueError):audit.validate_function_line_alignment(document, blobs)

    def test_canonical_hashes_do_not_validate_a_wrong_declaration_excerpt(self):
        raw = b"VALUE = 1;\n"
        blobs = {"tiny": raw}
        span = {"sourceId": "tiny", "symbol": "VALUE", "startLine": 1, "endLine": 1, "spanSha256": hashlib.sha256(raw).hexdigest()}
        document = {"sources": [{"sourceId": "tiny", "sha256": hashlib.sha256(raw).hexdigest()}],
                    "declaration": {"assignment": "VALUE = 1;", "sourceSpan": span}}
        audit.validate_function_line_alignment(document, blobs)
        document["declaration"]["assignment"] = "VALUE = 99;"
        # Original span/body SHA receipts remain correct, but the claim is false.
        validate_canonical(document, blobs)
        with self.assertRaises(ValueError):audit.validate_function_line_alignment(document, blobs)

    def test_wrong_callsite_codepoint_offsets_and_out_of_bounds_spans_fail(self):
        for mutate in (lambda d: d["calls"][0].update(callSiteLines=[5]),
                       lambda d: d["functions"][0].update(functionStartOffset=d["functions"][0]["functionStartOffset"]-1),
                       lambda d: d["functions"][0].update(endLine=99)):
            document, blobs = tiny_fixture(); mutate(document)
            with self.assertRaises(ValueError):validate_canonical(document, blobs)

    def test_static_callee_prefix_is_not_the_claimed_function_call(self):
        document, blobs = tiny_fixture(call="$beta")
        with self.assertRaises(ValueError):validate_canonical(document, blobs)


if __name__ == "__main__":
    unittest.main()
