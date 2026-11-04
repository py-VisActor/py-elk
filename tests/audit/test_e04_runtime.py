"""E04 installed-receipt negatives, independent of Node, Git and raw run caches."""
import base64
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
from validate_e04_source_bindings import DOCUMENTS
from validate_e04_runtime import (
    APPROVALS, AUDIT, INSTALLED, NUMERIC, POLICY, REQUIRED_FILES, SELECTION, SUITE,
    check, effective_seed,
    historical_material, HISTORICAL_MATERIAL, HISTORICAL_WHEEL,
)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@contextmanager
def offline_copy():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        paths = {AUDIT, *REQUIRED_FILES, HISTORICAL_MATERIAL, HISTORICAL_WHEEL,
                 "references/e03-option-sources.json", "tests/fixtures/validation/cases.json",
                 *DOCUMENTS.values(), "references/e04-reviews/A-source-by-V.json", "references/e04-reviews/B-source-by-A.json"}
        paths |= {"references/metadata/" + kind + ".json" for kind in ("algorithms", "options", "categories")}
        paths |= {(Path(SUITE).parent / row["request"]).as_posix() for row in load(ROOT / SUITE)["cases"]}
        for name in paths:
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        declarations, package = historical_material(ROOT)
        for name, document in declarations.items():
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            save(destination, document)
        for name, raw in package.items():
            destination = root / "src/pyelk" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        yield root


def rebind(root, changed):
    """Let semantic controls pass SHA guards, rather than testing only stale SHA."""
    audit = load(root / AUDIT)
    if changed in REQUIRED_FILES:
        audit["filesSha256"][changed] = sha256(root / changed)
        save(root / AUDIT, audit)
    if changed == AUDIT or changed in REQUIRED_FILES:
        fingerprint = sha256(root / AUDIT)
        for path in ("UPSTREAM.json", "docs/compatibility.json"):
            document = load(root / path)

            def visit(value):
                if type(value) is dict:
                    if value.get("path") == AUDIT and "sha256" in value:
                        value["sha256"] = fingerprint
                    for child in value.values():
                        visit(child)
                elif type(value) is list:
                    for child in value:
                        visit(child)
            visit(document)
            save(root / path, document)


class RuntimeEvidenceTests(unittest.TestCase):
    def negative(self, path, mutate, message=None):
        with offline_copy() as root:
            self.assertEqual(check(root)["errors"], [], "The unmodified audit fixture must pass")
            document = load(root / path)
            mutate(document)
            save(root / path, document)
            rebind(root, path)
            report = check(root)
            self.assertEqual(report["status"], "FAIL", (path, report))
            self.assertFalse(report["historicalInstalledEvidenceValidated"])
            if message:
                self.assertIn(message, " ".join(report["errors"]))

    def test_actual_current_declarations_and_installed_evidence(self):
        report = check(ROOT, historical=True)
        self.assertEqual(report["status"], "E04_RUNTIME_EVIDENCE_VALIDATED", report)
        self.assertTrue(report["historicalInstalledEvidenceValidated"])
        self.assertIs(report["runtimeReexecuted"], False)
        self.assertIs(report["mathematicalEquivalenceAutomaticallyProved"], False)
        self.assertIs(report["historicalWheelAuthenticated"], False)
        self.assertIs(type(report["pythonAlgorithmsVerified"]), int)
        self.assertEqual(report["pythonAlgorithmsVerified"], 0)
        self.assertIs(report["currentPackageBytesValidated"], False)
        self.assertIs(report["historicalPackageBytesValidated"], True)

    def test_historical_mode_checks_actual_archive_without_certifying_new_current_bytes(self):
        with offline_copy() as root:
            (root / "src/pyelk/api.py").write_bytes(b"changed current implementation\n")
            self.assertEqual(check(root)["status"], "FAIL")
            history = check(root, historical=True)
            self.assertEqual(history["status"], "E04_RUNTIME_EVIDENCE_VALIDATED", history)
            self.assertIs(history["currentPackageBytesValidated"], False)
            self.assertIs(history["runtimeReexecuted"], False)

    def test_historical_archive_or_declaration_changes_cannot_rebind_original_identity(self):
        with offline_copy() as root:
            wheel = root / HISTORICAL_WHEEL
            wheel.write_bytes(wheel.read_bytes() + b"changed")
            self.assertEqual(check(root, historical=True)["status"], "FAIL")
        with offline_copy() as root:
            material = load(root / HISTORICAL_MATERIAL)
            entry = material["declarations"]["UPSTREAM.json"]
            altered = json.loads(base64.b64decode(entry["bytesBase64"]))
            altered["python"]["packagePublished"] = True
            raw = json.dumps(altered).encode("utf-8")
            entry.update(bytesBase64=base64.b64encode(raw).decode("ascii"), sha256=hashlib.sha256(raw).hexdigest())
            save(root / HISTORICAL_MATERIAL, material)
            self.assertEqual(check(root, historical=True)["status"], "FAIL")

    def test_fresh_offline_copy_needs_no_git_node_installed_venv_or_raw_runs(self):
        with offline_copy() as root:
            with patch("subprocess.run", side_effect=AssertionError("offline audit cannot execute a backend")), \
                 patch("socket.create_connection", side_effect=AssertionError("offline audit cannot use a network")):
                report = check(root)
            self.assertEqual(report["status"], "E04_RUNTIME_EVIDENCE_VALIDATED", report)
            self.assertIs(report["ignoredRunFilesRequired"], False)
            for directory in (".git", ".local", "test-runs"):
                self.assertFalse((root / directory).exists())

    def test_full_capability_and_boolean_as_integer_promotions_fail(self):
        for mutate in (
            lambda d: d["python"].update(runtimeImplemented=False),
            lambda d: d["python"].update(implementedAlgorithms=["org.eclipse.elk.layered"]),
            lambda d: d["python"].update(packagePublished=True),
            lambda d: d["referenceFixtures"].update(pythonAlgorithmsVerified=False),
        ):
            self.negative("UPSTREAM.json", mutate)
        for mutate in (
            lambda d: d["runtimeClaims"].update(publicLayoutApiAccepted=True),
            lambda d: d["runtimeClaims"].update(lifecycleAccepted=True),
            lambda d: d["runtimeClaims"].update(releaseAccepted=True),
            lambda d: d.update(pythonAlgorithmsVerified=False),
        ):
            self.negative(AUDIT, mutate)
        self.negative("docs/compatibility.json", lambda d: d["algorithms"][3].update(coordinates="coordinates_verified"))
        self.negative("docs/compatibility.json", lambda d: d["api"][1].update(status="api_verified"))

    def test_crosscutting_identity_and_fixed_oracle_source_roles_cannot_be_relabelled(self):
        self.negative("docs/compatibility.json", lambda d: d["crossCutting"][0].update(id="invented-unrelated-capability"), "Cross-cutting")
        for path in ("lib/elk.bundled.js", "lib/elk-worker.js"):
            self.negative("UPSTREAM.json", lambda d, p=path: d["distribution"]["sha256Files"].update({p: "0" * 64}), "fingerprints")
        self.negative("UPSTREAM.json", lambda d: d["javascript"].update(repository="https://github.com/other/elkjs"), "source roles")
        self.negative("UPSTREAM.json", lambda d: d["metadataCapture"].update(entrypoint="lib/elk-worker.js"), "source roles")
        self.negative("UPSTREAM.json", lambda d: d["distribution"].update(gitHead="0" * 40), "source roles")

    def test_catalogue_master_and_slice_denominators_cannot_shrink_or_duplicate(self):
        for kind in ("algorithms", "options", "categories"):
            self.negative("docs/compatibility.json", lambda d, k=kind: d[k].pop(), "denominator")
        self.negative(AUDIT, lambda d: d["coverageDenominators"].update(sliceCases=20), "denominator")
        self.negative(SELECTION, lambda d: d.update(excludedMasterCases=19), "denominator")
        self.negative(SUITE, lambda d: d["cases"].pop(), "all21")
        self.negative(INSTALLED, lambda d: d["cases"].append(copy.deepcopy(d["cases"][0])), "case IDs")

    def test_scope_bindings_cannot_expand_drift_escape_or_drop(self):
        self.negative(AUDIT, lambda d: d["scope"].update(maximumNodes=5), "scope")
        self.negative(AUDIT, lambda d: d["scope"].update(directions=["RIGHT", "LEFT"]), "scope")
        self.negative(AUDIT, lambda d: d["filesSha256"].pop(NUMERIC), "file denominator")
        self.negative(AUDIT, lambda d: d["filesSha256"].update({INSTALLED: "0" * 64}), "evidence SHA")
        self.negative(AUDIT, lambda d: d["filesSha256"].update({"../outside.json": "0" * 64}), "file denominator")
        self.negative(APPROVALS, lambda d: d.update(globalAlgorithmSourceGate="unverified"), "Source approval")
        self.negative(APPROVALS, lambda d: d["approvals"].clear(), "approval denominator")
        self.negative("UPSTREAM.json", lambda d: d["python"]["experimentalAlgorithms"][0]["evidence"].update(path="test-runs/ignored.json"))

    def test_historical_failed_timed_out_partial_or_unisolated_commands_cannot_pass(self):
        for mutate in (
            lambda d: d["commands"].pop(),
            lambda d: d["commands"][4].update(exitCode=1),
            lambda d: d["commands"][4].update(exitCode=False),
            lambda d: d["commands"][5].update(timedOut=True),
            lambda d: d["commands"][4].update(environmentPolicy="inherited"),
            lambda d: d["commands"][1]["argv"].remove("-I"),
        ):
            self.negative(INSTALLED, mutate)

    def test_capture_argv_requires_real_role_action_same_suite_and_adapter_relationships(self):
        for index in (3, 4):
            self.negative(INSTALLED, lambda d, i=index: d["commands"][i].update(argv=["unrelated-tool", "--repeat", str(d["repeat"])]))

        def replace_arg(document, index, old, new):
            argv = document["commands"][index]["argv"]
            argv[argv.index(old)] = new

        self.negative(INSTALLED, lambda d: replace_arg(d, 3, "reference", "candidate"), "action")
        self.negative(INSTALLED, lambda d: replace_arg(d, 4, "scripts/validate_layout.py", "scripts/other.py"), "entrypoint")
        self.negative(INSTALLED, lambda d: replace_arg(d, 3, "--cases", "--wrong-cases"), "capture flags")
        self.negative(INSTALLED, lambda d: replace_arg(d, 4, d["commands"][4]["argv"][4], "tests/fixtures/validation/cases.json"), "same E04 suite")
        self.negative(INSTALLED, lambda d: replace_arg(d, 4, d["commands"][4]["argv"][6], "other-candidate-command.json"), "generated adapter")
        self.negative(INSTALLED, lambda d: replace_arg(d, 2, d["commands"][2]["argv"][4], "other-python"), "candidate interpreter")
        self.negative(INSTALLED, lambda d: replace_arg(d, 5, d["commands"][5]["argv"][10], "other-candidate-capture"), "recorded captures")

    def test_historical_windows_paths_remain_lexical_on_a_posix_offline_copy(self):
        with offline_copy() as root:
            summary = load(root / INSTALLED)

            def lexical_posix(value):
                value = value.replace("\\", "/")
                return "/historical/" + value[3:] if value.startswith("C:/") else value

            for command in summary["commands"]:
                command["argv"] = [lexical_posix(arg) for arg in command["argv"]]
                command["cwd"] = lexical_posix(command["cwd"])
            save(root / INSTALLED, summary)
            rebind(root, INSTALLED)
            self.assertEqual(check(root)["status"], "E04_RUNTIME_EVIDENCE_VALIDATED")

    def test_case_success_requires_original_request_identity_all_independent_checks_and_repeats(self):
        for mutate in (
            lambda d: d["cases"][0].update(requestSha256="0" * 64),
            lambda d: d["cases"][0].update(candidateGeometry=False),
            lambda d: d["cases"][0].update(nativePublicTolerance=False),
            lambda d: d["cases"][0].update(candidateInputPreserved=False),
            lambda d: d["cases"][0].update(strictPassed=True),
            lambda d: d["cases"][0].update(repetitionsCompared=1),
            lambda d: d.update(repeat=True),
            lambda d: d.update(historicalEvidenceOnly=False),
            lambda d: d.pop("fullAlgorithmAccepted"),
        ):
            self.negative(INSTALLED, mutate)

    def test_seed_default_context_and_source_policy_cannot_be_invented(self):
        for mutate in (
            lambda d: d["cases"][5]["candidateDeterminism"].update(seed=0),
            lambda d: d["cases"][5]["candidateDeterminism"].update(seedSource="explicit-request"),
            lambda d: d["cases"][0]["referenceDeterminism"].update(passed=False),
        ):
            self.negative(INSTALLED, mutate, "deterministic context")
        self.negative(POLICY, lambda d: d.update(defaultSeed=True), "default seed")
        self.negative(POLICY, lambda d: d["sourceEvidence"].update(sha256="0" * 64), "source receipt")

    def test_rebound_seed_source_must_declare_unique_integer_one(self):
        for duplicate, default in ((False, 7), (False, True), (True, 1)):
            with self.subTest(duplicate=duplicate, default=default), offline_copy() as root:
                path = root / "references/e03-option-sources.json"
                sources = load(path)
                option = next(row for row in sources["options"] if row["id"] == "org.eclipse.elk.randomSeed")
                option["declaredDefault"] = default
                if duplicate:
                    sources["options"].append(copy.deepcopy(option))
                save(path, sources)
                policy = load(root / POLICY)
                policy["sourceEvidence"]["sha256"] = sha256(path)
                save(root / POLICY, policy)
                rebind(root, POLICY)
                report = check(root)
                self.assertEqual(report["status"], "FAIL", report)
                self.assertIn("seed", " ".join(report["errors"]))

    def test_three_seed_aliases_follow_selected_scope_local_override_and_conflict_rules(self):
        def request(local, selected=None, constructor=None):
            return {"constructor": constructor or {}, "layoutArguments": {} if selected is None else {"layoutOptions": selected},
                    "graph": {"layoutOptions": local}}

        for alias in ("randomSeed", "elk.randomSeed", "org.eclipse.elk.randomSeed"):
            self.assertEqual(effective_seed(request({alias: 7})), (7, "explicit-request"))
            with self.assertRaises(ValueError):
                effective_seed(request({alias: 0}))
        for local, selected in (({"randomSeed": 7, "elk.randomSeed": 17}, None),
                                ({}, {"randomSeed": 7, "org.eclipse.elk.randomSeed": 17})):
            with self.assertRaises(ValueError):
                effective_seed(request(local, selected))
        self.assertEqual(effective_seed(request({"randomSeed": 1}, {"elk.randomSeed": 0})), (1, "explicit-request"))
        self.assertEqual(effective_seed(request({}, {}, {"defaultLayoutOptions": {"randomSeed": 0}})), (1, "fixed-source-default"))
        for invalid in (None, False, 1.5, "invalid"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                effective_seed(request({"randomSeed": 1}, {"randomSeed": invalid}))

    def test_installed_package_must_match_current_python_and_license_bytes(self):
        self.negative(INSTALLED, lambda d: d["packageFilesSha256"].update({"algorithms/layered/phases.py": "0" * 64}), "package bytes")
        self.negative(INSTALLED, lambda d: d["packageFilesSha256"].pop("_licenses/NOTICE.md"), "file denominator")
        self.negative(INSTALLED, lambda d: d["packageFilesSha256"].update({"../outside.py": "0" * 64}), "file denominator")
        # Old execution-time tooling is historical identity, not a current-tool lock.
        with offline_copy() as root:
            summary = load(root / INSTALLED)
            summary["sourceSha256AtExecution"]["scripts/check.py"] = "1" * 64
            save(root / INSTALLED, summary)
            rebind(root, INSTALLED)
            self.assertEqual(check(root)["status"], "E04_RUNTIME_EVIDENCE_VALIDATED")

    def test_numeric_raw_hash_engine_domain_and_close_error_remain_independent(self):
        self.negative(NUMERIC, lambda d: d.update(fullAlgorithmAccepted=True), "Complete capability")
        self.negative(NUMERIC, lambda d: d["cases"][0].update(extra={"lifecycleAccepted": True}), "Complete capability")
        self.negative(NUMERIC, lambda d: d["cases"][0].update(requestSha256="0" * 64), "bytes SHA")
        self.negative(NUMERIC, lambda d: d["cases"][0]["engine"].update(entrypointSha256="0" * 64), "engine receipt")
        self.negative(NUMERIC, lambda d: d["cases"].pop(), "case denominator")

        def alter_observation(document, edit):
            case = document["cases"][0]
            observation = json.loads(base64.b64decode(case["rawObservationBytesBase64"]))
            edit(observation)
            raw = (json.dumps(observation) + "\n").encode("utf-8")
            case["rawObservationBytesBase64"] = base64.b64encode(raw).decode("ascii")
            case["rawObservationSha256"] = hashlib.sha256(raw).hexdigest()

        self.negative(NUMERIC, lambda d: alter_observation(d, lambda o: o.update(outcome="threw")), "reference outcome")
        self.negative(NUMERIC, lambda d: alter_observation(d, lambda o: o.update(termination={"outcome": "returned"})), "close error")

    def test_syntax_valid_historical_wheel_hash_is_not_independently_authenticated(self):
        with offline_copy() as root:
            summary = load(root / INSTALLED)
            summary["wheelSha256"] = "0" * 64
            save(root / INSTALLED, summary)
            rebind(root, INSTALLED)
            report = check(root)
            # An unsigned, fully rebound summary cannot authenticate missing bytes.
            self.assertEqual(report["status"], "E04_RUNTIME_EVIDENCE_VALIDATED", report)
            self.assertIs(report["historicalWheelAuthenticated"], False)
            self.assertIn("cannot independently authenticate historical wheel hashes", report["limitation"])


if __name__ == "__main__":
    unittest.main()
