"""Portable E08 runtime receipts: real positive before each targeted mutation.

One independent sparse filesystem copy is shared by this class. Every changed
file is restored after its mutation; the validator genuinely recomputes the
complete positive receipt each time. Missing actual receipts fail setup.
"""
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import layout_checks
from layout_checks import load, sha256
from audit_fixture_support import copy_files, record_reads, source_paths
from plan_suite_execution import build_plan, canonical_sha, evaluate_case, execution_key
import validate_e08_api as api_audit
from validate_e08_runtime import AUDIT, INSTALLED, APPROVALS, check, case_receipt, historical_material


def encoded_json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def fixture_paths(root):
    """Runtime read closure, including the API oracle actually read by check."""
    root = Path(root)
    audit, approval = load(root / AUDIT), load(root / APPROVALS)
    paths = source_paths(root, "E07") | {AUDIT, INSTALLED, APPROVALS, "UPSTREAM.json",
        "docs/compatibility.json", "pyproject.toml", "README.md", "references/native-contract.json",
        "references/e04-determinism-policy.json", "references/e03-option-sources.json",
        api_audit.RECORD, *audit["filesSha256"], *api_audit.reference_sources(root),
        *api_audit.native_sources(root)}
    for row in approval["reviewEvidence"].values():
        paths.add(row["path"])
        paths.update(load(root / row["path"])["filesSha256"])
    for pattern in ("scripts/*.py", "tools/reference/*.py", "tools/reference/*.cjs", "src/**/*.py"):
        paths.update(p.relative_to(root).as_posix() for p in root.glob(pattern) if p.is_file())
    paths.update(p.relative_to(root).as_posix() for p in (root / "src/pyelk").rglob("*")
                 if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    for name in ("algorithms", "options", "categories"):
        paths.add("references/metadata/" + name + ".json")
    plan = build_plan(root)
    for suite in plan["suites"].values():
        paths.add(suite["path"])
        paths.update(case["request"] for case in suite["cases"])
    oracle = root / api_audit.SUITE / "oracle"
    # verify_reference inspects all raw files and the exact file denominator.
    # E04-E07 geometry observations already live inside the portable receipt.
    paths.update(p.relative_to(root).as_posix() for p in oracle.rglob("*") if p.is_file())
    paths.add((PurePosixPath(api_audit.SUITE) / "oracle/index.json").as_posix())
    return paths


class E08RuntimeReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="pyelk-e08-audit-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        # No skip or synthesized fixture: missing real audit/receipt is an error.
        # Keep every original current-byte semantic mutation against the exact
        # E08 input closure. E09's current package has its own fresh evidence.
        material = historical_material(ROOT)
        for name, raw in material.items():
            target = cls.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        cls.copy_profile = {"copiedFiles": len(material), "copiedBytes": sum(map(len, material.values())),
                            "paths": sorted(material)}
        print(json.dumps({"fixtureCopy": "E08-runtime",
                          "copiedFiles": cls.copy_profile["copiedFiles"],
                          "copiedBytes": cls.copy_profile["copiedBytes"]}), flush=True)

    def setUp(self):
        self.saved = {}

    def tearDown(self):
        self._restore()

    def _restore(self):
        for name, raw in self.saved.items():
            path = self.root / name
            if raw is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(raw)
        self.saved.clear()

    def _write(self, name, raw):
        path = self.root / name
        if name not in self.saved:
            self.saved[name] = path.read_bytes() if path.exists() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def _save(self, name, value):
        self._write(name, encoded_json(value))

    def _rebind(self, name):
        if name != AUDIT:
            audit = load(self.root / AUDIT)
            self.assertIn(name, audit["filesSha256"])
            audit["filesSha256"][name] = sha256(self.root / name)
            self._save(AUDIT, audit)
        fingerprint = sha256(self.root / AUDIT)
        def visit(value):
            if type(value) is dict:
                if value.get("path") == AUDIT and "sha256" in value:
                    value["sha256"] = fingerprint
                for child in value.values():
                    visit(child)
            elif type(value) is list:
                for child in value:
                    visit(child)
        for declaration in ("UPSTREAM.json", "docs/compatibility.json"):
            value = load(self.root / declaration)
            visit(value)
            self._save(declaration, value)

    def _receipt(self):
        return load(self.root / INSTALLED)

    def _save_receipt(self, value):
        self._save(INSTALLED, value)
        self._rebind(INSTALLED)

    def _check(self):
        # Shared comparator defaults must read the fixture's native profile and
        # seed proof, rather than silently reading undamaged original evidence.
        with patch.object(layout_checks, "ROOT", self.root):
            return check(self.root)

    def _negative(self, mutate, target):
        self.assertEqual(self._check()["errors"], [], "Unmutated actual fixture must first pass")
        try:
            mutate()
            result = self._check()
            self.assertTrue(result["errors"])
            self.assertIn(target, " ".join(result["errors"]))
        finally:
            self._restore()

    @staticmethod
    def _put_blob(table, value):
        raw = encoded_json(value)
        fingerprint = hashlib.sha256(raw).hexdigest()
        table[fingerprint] = base64.b64encode(raw).decode("ascii")
        return fingerprint

    @staticmethod
    def _drop_unused_blobs(receipt):
        used = {obj["observationSha256"] for obj in receipt["objects"].values()}
        receipt["observationBytesBase64"] = {key: value for key, value in receipt["observationBytesBase64"].items() if key in used}
        used = {obj["commandReceiptSha256"] for obj in receipt["objects"].values()}
        for context in receipt["contexts"].values():
            used.add(context["identity"]["queryCommandSha256"])
        used.add(receipt["contexts"]["candidate"]["identity"]["installedCommandSha256"])
        receipt["commandBytesBase64"] = {key: value for key, value in receipt["commandBytesBase64"].items() if key in used}

    def _mutate_observations(self, mutate):
        receipt = self._receipt()
        selected = next(case for suite in receipt["plan"]["suites"].values() for case in suite["cases"]
                        if len(load(self.root / case["request"])["graph"].get("children", [])) >= 2)
        fingerprint = selected["requestSha256"]
        for obj in receipt["objects"].values():
            if obj["role"] == "candidate" and obj["requestSha256"] == fingerprint:
                value = json.loads(base64.b64decode(receipt["observationBytesBase64"][obj["observationSha256"]]))
                mutate(value)
                obj["observationSha256"] = self._put_blob(receipt["observationBytesBase64"], value)
        self._drop_unused_blobs(receipt)
        self._save_receipt(receipt)

    def _refresh_case_views(self, receipt):
        observed = {key: json.loads(base64.b64decode(value)) for key, value in receipt["observationBytesBase64"].items()}
        with patch.object(layout_checks, "ROOT", self.root):
            for name, suite in receipt["suites"].items():
                for index, (case, original) in enumerate(zip(suite["cases"], receipt["plan"]["suites"][name]["cases"])):
                    observations = {role: [observed[receipt["objects"][key]["observationSha256"]]
                                           for key in case["executionReferences"][role]]
                                    for role in receipt["contexts"]}
                    actual = evaluate_case(original["definition"], self.root / original["request"],
                                           observations["reference"], observations["candidate"], receipt["report"]["repeat"])
                    self.assertTrue(actual["passed"], "Identity-only mutation must preserve actual layout evaluation")
                    actual["executionReferences"] = case["executionReferences"]
                    suite["cases"][index] = case_receipt(actual)

    def _rekey_context(self, receipt, role):
        context, keys, objects = receipt["contexts"][role], {}, {}
        for old, obj in receipt["objects"].items():
            if obj["role"] != role:
                objects[old] = obj
                continue
            new = execution_key(obj["requestSha256"], context, obj["repetition"])
            keys[old] = new
            obj["executionKey"], obj["contextSha256"] = new, canonical_sha(context)
            obj["request"] = obj["request"].replace(old, new)
            obj["observation"] = obj["observation"].replace(old, new)
            obj["command"]["argv"] = [part.replace(old, new) for part in obj["command"]["argv"]]
            obj["commandReceiptSha256"] = self._put_blob(receipt["commandBytesBase64"], obj["command"])
            objects[new] = obj
        receipt["objects"] = objects
        for suite in receipt["suites"].values():
            for case in suite["cases"]:
                case["executionReferences"][role] = [keys[key] for key in case["executionReferences"][role]]
        self._drop_unused_blobs(receipt)
        self._refresh_case_views(receipt)

    def test_actual_positive_dependency_closure_has_no_external_wheel_or_cache(self):
        with record_reads(self.root) as reads:
            self.assertEqual(self._check()["errors"], [])
        self.assertTrue(reads)
        self.assertLessEqual(reads, set(self.copy_profile["paths"]))
        self.assertFalse((self.root / ".git").exists())
        self.assertFalse((self.root / ".local").exists())
        self.assertFalse(any("/oracle/" in name and "/E08-api/" not in name for name in self.copy_profile["paths"]))

    def test_empty_repeat_and_missing_original_case_cannot_pass(self):
        def empty_repeat():
            receipt = self._receipt();receipt["report"]["repeat"] = 0;self._save_receipt(receipt)
        def missing_case():
            receipt = self._receipt();receipt["suites"]["E07"]["cases"].pop();self._save_receipt(receipt)
        for mutate, target in ((empty_repeat, "Fresh repetition denominator differs"), (missing_case, "Case identities/order differ")):
            with self.subTest(target=target):
                self._negative(mutate, target)

    def test_rebound_raw_geometry_is_recomputed_instead_of_trusting_pass(self):
        def mutate(value):
            value["result"]["children"][0]["x"] = -1
        self._negative(lambda: self._mutate_observations(mutate), "Recomputed layout comparison/geometry/input/determinism failed")

    def test_rebound_raw_input_mutation_is_recomputed(self):
        def mutate(value):
            value["inputAfter"]["children"][0]["width"] += 0.25
        self._negative(lambda: self._mutate_observations(mutate), "Recomputed layout comparison/geometry/input/determinism failed")

    def test_rebound_raw_wrong_direction_cannot_keep_old_case_pass(self):
        def mirror(value):
            graph = value["result"];width = graph["width"]
            for node in graph["children"]:
                node["x"] = width - node["x"] - node["width"]
            for edge in graph.get("edges", []):
                for section in edge.get("sections", []):
                    for point in [section["startPoint"], section["endPoint"], *section.get("bendPoints", [])]:
                        point["x"] = width - point["x"]
        self._negative(lambda: self._mutate_observations(mirror), "Recomputed layout comparison/geometry/input/determinism failed")

    def test_rebound_object_command_cannot_replace_isolated_interpreter_flag(self):
        def mutate():
            receipt = self._receipt()
            obj = next(row for row in receipt["objects"].values() if row["role"] == "candidate")
            self.assertEqual(obj["command"]["argv"][1], "-I")
            obj["command"]["argv"][1] = "-E"
            obj["commandReceiptSha256"] = self._put_blob(receipt["commandBytesBase64"], obj["command"])
            self._drop_unused_blobs(receipt);self._save_receipt(receipt)
        self._negative(mutate, "Original object command role/isolation differs")

    def test_fully_rebound_identity_command_still_requires_exact_isolated_role(self):
        def mutate():
            receipt = self._receipt();command = receipt["identityCommands"][0]
            self.assertEqual(command["argv"][1], "-I");command["argv"][1] = "-E"
            new = self._put_blob(receipt["commandBytesBase64"], command)
            receipt["contexts"]["candidate"]["identity"]["queryCommandSha256"] = new
            self._rekey_context(receipt, "candidate");self._save_receipt(receipt)
        self._negative(mutate, "Original identity command role/isolation differs")

    def test_current_source_change_cannot_reuse_old_approval(self):
        name = "src/pyelk/api.py"
        self._negative(lambda: self._write(name, (self.root / name).read_bytes() + b"\n# current-byte mutation\n"),
                       "Approved E08 code bytes differ")

    def test_current_notice_change_cannot_reuse_installed_package(self):
        name = "src/pyelk/_licenses/NOTICE-E08.md"
        self._negative(lambda: self._write(name, (self.root / name).read_bytes() + b"\nchanged notice\n"),
                       "Current package file denominator/bytes differ")

    def test_readme_and_rebound_actual_metadata_remain_independent_checks(self):
        def readme():
            self._write("README.md", (self.root / "README.md").read_bytes() + b"\nchanged declaration\n")
        def metadata():
            receipt = self._receipt();record = receipt["installed"]["distributionMetadata"]
            raw = base64.b64decode(record["bytesBase64"])
            changed = raw.replace(b"Requires-Python: >=3.11", b"Requires-Python: >=3.12")
            self.assertNotEqual(changed, raw)
            record["bytesBase64"] = base64.b64encode(changed).decode("ascii")
            record["sha256"] = hashlib.sha256(changed).hexdigest();self._save_receipt(receipt)
        for mutate, target in ((readme, "Distribution README bytes differ"), (metadata, "Distribution Requires-Python differs")):
            with self.subTest(target=target):
                self._negative(mutate, target)

    def test_rebound_empty_approval_and_rejected_independent_review_fail(self):
        def empty_approval():
            approval = load(self.root / APPROVALS);approval["pythonFilesSha256"] = {}
            self._save(APPROVALS, approval);self._rebind(APPROVALS)
        def rejected_review():
            approval = load(self.root / APPROVALS)
            row = approval["reviewEvidence"]["A-execution"];review = load(self.root / row["path"])
            review["accepted"] = False
            self._save(row["path"], review);row["sha256"] = sha256(self.root / row["path"])
            self._save(APPROVALS, approval);self._rebind(APPROVALS)
        for mutate, target in ((empty_approval, "E08 host code approval denominator differs"),
                               (rejected_review, "Independent host review rejected or incomplete")):
            with self.subTest(target=target):
                self._negative(mutate, target)

    def test_native_lifecycle_and_geometry_must_bind_the_same_actual_wheel(self):
        def mutate():
            receipt = self._receipt()
            original = receipt["apiRuntime"]["installed"]["wheelSha256"]
            receipt["apiRuntime"]["installed"]["wheelSha256"] = "0" * 64 if original != "0" * 64 else "1" * 64
            # Keep V's embedded actual installed identity internally consistent;
            # the target is the independent connection to the geometry wheel.
            receipt["apiRuntime"]["installedReceiptBytesBase64"] = base64.b64encode(
                encoded_json(receipt["apiRuntime"]["installed"])).decode("ascii")
            self._save_receipt(receipt)
        self._negative(mutate, "API/lifecycle and geometry must use the same installed wheel")

    def test_original_observation_blob_bytes_are_checked_before_semantic_evaluation(self):
        def mutate():
            receipt = self._receipt();key = next(iter(receipt["observationBytesBase64"]))
            raw = base64.b64decode(receipt["observationBytesBase64"][key])
            receipt["observationBytesBase64"][key] = base64.b64encode(raw + b" ").decode("ascii")
            self._save_receipt(receipt)
        self._negative(mutate, "Original receipt bytes differ")

    def test_native_registry_and_current_declarations_cannot_promote_reference_capabilities(self):
        def counts():
            lock = load(self.root / "UPSTREAM.json")
            lock["python"]["nativeHost"]["defaultRegistryCounts"]["options"] = 243
            ledger = load(self.root / "docs/compatibility.json")
            ledger["nativeHost"] = lock["python"]["nativeHost"]
            self._save("UPSTREAM.json", lock);self._save("docs/compatibility.json", ledger)
        def obsolete_evidence():
            lock = load(self.root / "UPSTREAM.json")
            lock["python"]["runtimeEvidence"] = "references/e07-runtime-audit.json"
            self._save("UPSTREAM.json", lock)
        def promoted_algorithm():
            lock = load(self.root / "UPSTREAM.json")
            lock["python"]["implementedAlgorithms"] = ["org.eclipse.elk.layered"]
            self._save("UPSTREAM.json", lock)
        def shrunken_reference():
            lock = load(self.root / "UPSTREAM.json")
            lock["metadataCapture"]["counts"]["options"] = 9
            self._save("UPSTREAM.json", lock)
        for mutate, target in ((counts, "Native registry declaration differs"),
                               (obsolete_evidence, "Current native host declaration/evidence differs"),
                               (promoted_algorithm, "Whole-algorithm declaration was promoted"),
                               (shrunken_reference, "Reference catalogue denominator differs")):
            with self.subTest(target=target):
                self._negative(mutate, target)


if __name__ == "__main__":
    unittest.main()
