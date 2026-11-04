"""E04 binding negatives; canonical fixtures need no Git, Node or cache."""
import copy
import hashlib
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import load
from validate_e04_source_bindings import DOCUMENTS, check, validate_approved_evidence, validate_canonical, validate_document


class SourceMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = load(ROOT / "UPSTREAM.json")
        cls.documents = {lane: load(ROOT / path) for lane, path in DOCUMENTS.items()}
        cls.approvals = load(ROOT / "references/e04-component-approvals.json")

    def negative(self, change, lane="A"):
        document = copy.deepcopy(self.documents[lane])
        change(document)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            validate_document(document, self.lock, lane)

    def test_actual_source_schema_and_versioned_reviews_bind_all_components(self):
        self.assertEqual(validate_document(self.documents["A"], self.lock, "A")["components"], 17)
        self.assertEqual(validate_document(self.documents["B"], self.lock, "B")["components"], 7)
        result = validate_approved_evidence(ROOT, self.documents)
        self.assertEqual(result["approvedComponentBindings"], 24)
        self.assertIs(result["ignoredRunFilesRequired"], False)

    def test_fixed_source_role_cannot_rebind_to_another_real_locked_file(self):
        self.negative(lambda d: d["sources"][0].update(path="package.json", sha256=self.lock["sourceSha256"]["package.json"]))
        self.negative(lambda d: d["sources"][0].update(kind="candidate-java"))
        self.negative(lambda d: d["sources"][0].update(commit="0" * 40))

    def test_source_and_component_denominators_are_exact(self):
        self.negative(lambda d: d["sources"].pop())
        self.negative(lambda d: d["components"].pop())
        self.negative(lambda d: d["components"].append(copy.deepcopy(d["components"][0])))
        self.negative(lambda d: d["components"][0].update(defaultCallIndex=False))
        self.negative(lambda d: d["components"][0].update(entrySpans=[]))

    def test_proof_refs_cannot_be_nonempty_unresolved_strings(self):
        self.negative(lambda d: d["components"][0]["observedHelpers"][0].update(proofRef="invented-proof"))
        self.negative(lambda d: d["hostMappingProofs"].pop())
        self.negative(lambda d: d["hostMappingProofs"].append(copy.deepcopy(d["hostMappingProofs"][0])))
        self.negative(lambda d: d["hostMappingProofs"][0].update(retainedWrites=[]))
        self.negative(lambda d: d["components"][0]["observedHelpers"][0].update(disposition="ignore-as-noop"))

    def test_nested_runtime_and_candidate_java_claims_fail_closed(self):
        self.negative(lambda d: d.update(pythonAlgorithmsVerified=False))
        self.negative(lambda d: d["components"][0].update(nativeLayoutImplemented=True))
        self.negative(lambda d: d["components"][0].update(runtimeAccepted=True))
        self.negative(lambda d: d["licenseEvidence"].update(legalCompatibilityConclusion=True))
        self.negative(lambda d: d["candidates"].update(actualPortSource=True))

    def test_line_function_and_callsite_metadata_use_exact_types(self):
        self.negative(lambda d: d["components"][0]["entrySpans"][0].update(startLine=True))
        self.negative(lambda d: d["components"][0]["entrySpans"][0].update(spanSha256="not-a-hash"))
        self.negative(lambda d: d["components"][0]["observedHelpers"][0].update(functionStartOffset=False))
        self.negative(lambda d: d["components"][0]["observedHelpers"][0].update(offsetUnit="Python-codepoints"))
        self.negative(lambda d: d["components"][0]["callEdges"][0].update(callSiteLines=[True]))
        self.negative(lambda d: d["components"][0]["callEdges"][0].update(callee="a nonempty sentence"))

    def test_review_hash_denominator_source_and_runtime_flags_are_independent_guards(self):
        controls = [lambda m: m["approvals"].pop(),
                    lambda m: m["approvals"].append(copy.deepcopy(m["approvals"][0])),
                    lambda m: m["approvals"][0].update(sourceDocumentSha256="0" * 64),
                    lambda m: m["approvals"][0].update(versionedReviewSha256="0" * 64),
                    lambda m: m["approvals"][0].update(versionedReview="test-runs/ignored-review.json"),
                    lambda m: m["approvals"][0].update(runtimeAccepted=True)]
        for control in controls:
            manifest = copy.deepcopy(self.approvals)
            control(manifest)
            with self.assertRaises((ValueError, KeyError, TypeError)):
                validate_approved_evidence(ROOT, self.documents, manifest)

    def test_offline_copy_without_git_cache_or_raw_runs_requires_no_subprocess(self):
        paths = ["UPSTREAM.json", *DOCUMENTS.values(), "references/e04-component-approvals.json",
                 "references/e04-reviews/A-source-by-V.json", "references/e04-reviews/B-source-by-A.json",
                 "docs/decisions/0003-e04-generated-source-slice.md", "src/pyelk/_licenses/elkjs-LICENSE.md", "src/pyelk/_licenses/NOTICE.md"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in paths:
                destination = root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / path, destination)
            with patch("subprocess.run", side_effect=AssertionError("offline check must not invoke Git/Node")):
                result = check(root)
            self.assertEqual(result["status"], "E04_SOURCE_BINDINGS_VALIDATED", result)
            self.assertIs(result["canonicalVerified"], False)
            self.assertIs(result["mathematicalEquivalenceAutomaticallyProved"], False)
            self.assertFalse((root / ".git").exists())
            self.assertFalse((root / ".local").exists())
            self.assertFalse((root / "test-runs").exists())


def canonical_fixture():
    prefix = 'const marker = "🦊";\n'
    target = "function target(){ return 1; }"
    caller = "function caller(){\n  return target();\n}"
    text = prefix + target + "\n" + caller + "\n"
    raw = text.encode("utf-8")
    rows = text.splitlines()

    def span(symbol, code, start, end):
        index = text.index(code)
        a = len(text[:index].encode("utf-16-le")) // 2
        return {"sourceId": "fixture-worker", "symbol": symbol, "startLine": start, "endLine": end,
                "spanSha256": hashlib.sha256(("\n".join(rows[start - 1:end]) + "\n").encode()).hexdigest(),
                "functionStartOffset": a, "functionEndOffset": a + len(code.encode("utf-16-le")) // 2,
                "offsetUnit": "UTF-16 code units", "functionSha256": hashlib.sha256(code.encode()).hexdigest()}

    target_span = span("target", target, 2, 2)
    caller_span = span("caller", caller, 3, 5)
    document = {"sources": [{"sourceId": "fixture-worker", "sha256": hashlib.sha256(raw).hexdigest()}],
                "entries": [target_span, caller_span], "callEdges": [{"caller": "caller", "callee": "target",
                    "calleeSpan": copy.deepcopy(target_span), "callSiteLines": [4]}]}
    return document, {"fixture-worker": raw}, text


class CanonicalByteFixtureTests(unittest.TestCase):
    def test_small_utf16_astral_fixture_checks_actual_calls_and_function_bytes(self):
        document, blobs, _ = canonical_fixture()
        result = validate_canonical(document, blobs)
        self.assertEqual(result["sources"], 1)
        self.assertEqual(result["staticCallEdges"], 1)
        self.assertGreaterEqual(result["functionOffsetOccurrences"], 2)

    def test_crlf_working_copy_cannot_replace_the_canonical_blob(self):
        document, blobs, _ = canonical_fixture()
        blobs["fixture-worker"] = blobs["fixture-worker"].replace(b"\n", b"\r\n")
        with self.assertRaisesRegex(ValueError, "source SHA"):
            validate_canonical(document, blobs)

    def test_python_codepoint_offsets_are_not_utf16_offsets(self):
        document, blobs, text = canonical_fixture()
        document["entries"][1]["functionStartOffset"] = text.index("function caller")
        with self.assertRaisesRegex(ValueError, "UTF16 function SHA"):
            validate_canonical(document, blobs)

    def test_span_drift_or_upper_bound_fails_even_with_intact_source_sha(self):
        for change in (lambda d: d["entries"][0].update(spanSha256="0" * 64),
                       lambda d: d["entries"][0].update(endLine=999)):
            document, blobs, _ = canonical_fixture()
            change(document)
            with self.assertRaises(ValueError):
                validate_canonical(document, blobs)

    def test_callsite_cannot_be_a_declaration_outside_the_caller(self):
        document, blobs, _ = canonical_fixture()
        document["callEdges"][0]["callSiteLines"] = [2]
        with self.assertRaisesRegex(ValueError, "outside caller"):
            validate_canonical(document, blobs)

    def test_callsite_requires_the_actual_callee_token_and_bounded_caller(self):
        document, blobs, _ = canonical_fixture()
        document["callEdges"][0]["callSiteLines"] = [3]
        with self.assertRaisesRegex(ValueError, "token missing"):
            validate_canonical(document, blobs)
        document, blobs, _ = canonical_fixture()
        document["callEdges"][0]["caller"] = "invented"
        with self.assertRaisesRegex(ValueError, "no bounded"):
            validate_canonical(document, blobs)


if __name__ == "__main__":
    unittest.main()
