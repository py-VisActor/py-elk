"""Audit current E08 package and portable actual-run receipts, without execution.

Fresh execution is provided by validate_e08_api.py and plan_suite_execution.py.
The portable receipt records the original sharing protocol, not a synthetic
legacy capture index. It proves consistency, not historical authentication.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from layout_checks import ROOT, contained, contract, load, sha256, write
from plan_suite_execution import (COUNTS, PROFILE, POLICY, build_plan, canonical_sha,
                                  execution_key, evaluate_case, validate_environment, validate_timing, VERSION_QUERY)
from validate_e04_runtime import digest, embedded_json, exact, historical_path, no_full_acceptance, require
from validate_e06_runtime import validate_metadata
from validate_e07_source_bindings import check as kernel_sources

AUDIT = "references/e08-runtime-audit.json"
INSTALLED = "references/e08-installed-check.json"
APPROVALS = "references/e08-component-approvals.json"
CONTRACT = "references/e08-host-contract.json"
SCOPE_ID = "E08-ADR0007-revision1"
HISTORY = "references/history/E08"
HISTORY_ARCHIVE_SHA = "a621343aa1952e4c4908728f5c2faf3d292f809f448f009da67f6bdb9624b10d"
HISTORY_MANIFEST_SHA = "a96378a1b50f5660bc29411ef1c259c6f96209906d0470564264bc6ff63a4686"
HOST_PYTHON = {"src/pyelk/__init__.py", "src/pyelk/api.py", "src/pyelk/_errors.py",
               "src/pyelk/metadata/__init__.py", "src/pyelk/metadata/_data.py",
               "src/pyelk/execution/__init__.py", "src/pyelk/execution/lifecycle.py", "src/pyelk/execution/worker.py"}
REVIEW_FILES = {
    "A-execution": {"src/pyelk/execution/__init__.py", "src/pyelk/execution/lifecycle.py", "src/pyelk/execution/worker.py",
                    "references/e08-execution-sources.json"},
    "V-api-metadata": {"src/pyelk/api.py", "src/pyelk/_errors.py", "src/pyelk/metadata/__init__.py",
                       "src/pyelk/metadata/_data.py", "references/e08-api-metadata-sources.json", "references/e08-metadata-schema.json"},
    "B-reference-and-runtime": {"tools/reference/capture_e08_api.cjs", "scripts/validate_e08_api.py",
                                "tests/conformance/test_e08_api_lifecycle.py",
                                "scripts/validate_e08_runtime.py", "scripts/export_e08_installed_evidence.py"},
}


def code_hashes(root):
    root = Path(root)
    paths = [*root.glob("scripts/*.py"), *root.glob("tools/reference/*.cjs"),
             *root.glob("tools/reference/*.py"), *root.glob("src/**/*.py")]
    return {p.relative_to(root).as_posix(): sha256(p) for p in sorted(paths)}


def package_hashes(root):
    package = Path(root) / "src/pyelk"
    return {p.relative_to(package).as_posix(): sha256(p) for p in sorted(package.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and
            (p.suffix == ".py" or p.relative_to(package).parts[0] == "_licenses" or p.name == "py.typed")}


def validate_package(installed, root):
    require(installed["status"] == "INSTALLED_WHEEL_BYTES_MATCH" and installed["isolatedInterpreter"] is True,
            "Current installed identity/isolation differs")
    digest(installed["wheelSha256"])
    exact(installed["packageFilesSha256"], package_hashes(root), "Current package file denominator/bytes differ")
    require("_licenses/NOTICE-E08.md" in installed["packageFilesSha256"], "E08 source notice missing")
    require("/src/pyelk" not in installed["modulePath"].replace("\\", "/"), "Source-tree installation is forbidden")
    return validate_metadata({"wheelVersion": installed["version"],
                              "distributionMetadata": installed["distributionMetadata"]}, root)


def command_ok(command):
    exact(command["exitCode"], 0, "Actual process did not succeed")
    exact(command["timedOut"], False, "Actual process timed out")
    require(type(command["argv"]) is list and bool(command["argv"]) and
            all(type(part) is str for part in command["argv"]), "Invalid actual command argv")
    for key in ("stdoutSha256", "stderrSha256"):
        digest(command[key])


def decode_blobs(blobs):
    require(type(blobs) is dict and bool(blobs), "Missing original raw receipt bytes")
    result = {}
    for fingerprint, encoded in blobs.items():
        digest(fingerprint)
        raw = base64.b64decode(encoded, validate=True)
        require(hashlib.sha256(raw).hexdigest() == fingerprint, "Original receipt bytes differ")
        result[fingerprint] = embedded_json(raw)
    return result


def validate_observation(value, context, request_sha):
    contract(value)
    require(value["requestSha256"] == request_sha and value["outcome"] == "returned", "Raw observation request/outcome differs")
    engine, identity = value["engine"], context["identity"]
    require(engine["name"] == identity["name"], "Raw observation engine differs")
    if context["role"] == "reference":
        require(engine["version"] == identity["baseline"] and engine["node"] == identity["version"] and
                engine["entrypointSha256"] == identity["entrypointSha256"], "Raw reference identity differs")
    else:
        require(engine["version"] == identity["version"] and engine["python"] == identity["pythonIdentity"]["version"] and
                historical_path(engine["modulePath"]) == historical_path(identity["modulePath"].replace("\\", "/") + "/__init__.py") and
                historical_path(engine["executable"]) == historical_path(identity["python"]), "Raw candidate identity differs")
        exact(engine["sourceSha256"], {n: h for n, h in identity["packageFilesSha256"].items() if n.endswith(".py")},
              "Raw candidate package bytes differ")


def case_receipt(value):
    """Bind the entire real view without copying megabytes of strict diffs.

    Validation recomputes this value from original observations every time;
    this digest never bypasses comparison, geometry or determinism evaluation.
    """
    return {"id": value["id"], "passed": value["passed"], "caseViewSha256": canonical_sha(value),
            "executionReferences": value["executionReferences"]}


def validate_layout_receipt(receipt, root):
    root = Path(root)
    require(receipt["schema"] == "py-elk-e08-current-installed-evidence/v1", "E08 installed receipt schema differs")
    no_full_acceptance(receipt)
    report, plan, contexts, objects = (receipt[key] for key in ("report", "plan", "contexts", "objects"))
    exact(plan, build_plan(root), "Original suite plan/request/policy differs")
    require(report["schema"] == "py-elk-suite-execution-run/v1" and report["passed"] is True and
            report["status"] == "SUITE_EXECUTION_REUSE_PASS" and report["executionMode"] == "shared-request",
            "Actual shared execution failed")
    repeat = report["repeat"]
    require(type(repeat) is int and repeat >= 3, "Fresh repetition denominator differs")
    exact(report["caseCount"], 181, "Case denominator differs")
    exact(report["uniqueRequests"], 149, "Unique request denominator differs")
    exact(report["suiteCounts"], COUNTS, "Suite denominators differ")
    exact(report["actualLayoutProcesses"], 149 * 2 * repeat, "Actual layout process denominator differs")
    exact(report["sourceSha256"], code_hashes(root), "Current execution adapter/source bytes differ")
    require(set(contexts) == {"reference", "candidate"}, "Engine role denominator differs")
    installed = receipt["installed"]
    metadata = validate_package(installed, root)
    for role, context in contexts.items():
        require(context["role"] == role, "Context role differs")
        validate_environment(context)
        exact(context["sourceSha256"], report["sourceSha256"], "Object source context differs")
        require(context["concurrency"] == report["jobs"], "Actual concurrency differs")
        require(context["seedPolicySha256"] == sha256(root / "references/e04-determinism-policy.json"),
                "Determinism policy bytes differ")
        identity, cwd = context["identity"], context["workingDirectory"].replace("\\", "/")
        expected_argv = ([identity["node"], cwd + "/tools/reference/capture_layout.cjs", identity["package"]]
                         if role == "reference" else [identity["python"], "-I", cwd + "/scripts/run_pyelk_candidate.py"])
        expected_argv += ["<REQUEST>", "<OBSERVATION>"]
        require(len(context["argvTemplate"]) == len(expected_argv) and
                all(historical_path(a) == historical_path(b) for a, b in zip(context["argvTemplate"], expected_argv)),
                "Actual engine collector entrypoint differs")
        if role == "reference":
            distribution = load(root / "UPSTREAM.json")["distribution"]["sha256Files"]
            require(all(identity["packageFilesSha256"].get(name) == fingerprint for name, fingerprint in distribution.items()),
                    "Reference distribution bytes differ")
    candidate = contexts["candidate"]["identity"]
    for key in ("wheelSha256", "modulePath", "version", "packageFilesSha256"):
        exact(candidate[key], installed[key], "Candidate/installed identity differs: " + key)
    require(contexts["candidate"]["argvTemplate"][1] == "-I" and
            contexts["reference"]["identity"]["baseline"] == "0.12.1", "Engine isolation/baseline differs")
    expected = {execution_key(h, contexts[role], i) for h in plan["requests"]
                for role in contexts for i in range(repeat)}
    require(set(objects) == expected and len(objects) == 149 * 2 * repeat, "Execution object denominator differs")
    observed = decode_blobs(receipt["observationBytesBase64"])
    commands = decode_blobs(receipt["commandBytesBase64"])
    require(set(observed) == {row["observationSha256"] for row in objects.values()}, "Raw observation denominator differs")
    command_keys = {row["commandReceiptSha256"] for row in objects.values()} | {
        contexts["candidate"]["identity"]["queryCommandSha256"], contexts["reference"]["identity"]["queryCommandSha256"],
        contexts["candidate"]["identity"]["installedCommandSha256"]}
    require(set(commands) == command_keys, "Original command receipt denominator differs")
    for key, obj in objects.items():
        role, i, fingerprint = obj["role"], obj["repetition"], obj["requestSha256"]
        require(role in contexts and type(i) is int and 0 <= i < repeat and fingerprint in plan["requests"],
                "Object role/request/repetition differs")
        context = contexts[role]
        require(obj["scope"] == {"kind": "request"} and key == obj["executionKey"] == execution_key(fingerprint, context, i),
                "Execution identity differs")
        require(obj["contextSha256"] == canonical_sha(context), "Execution context binding differs")
        for name in ("commandReceiptSha256", "observationSha256"):
            digest(obj[name])
        require(obj["request"] == "objects/" + key + "/request.json" and
                obj["observation"] == "objects/" + key + "/observation.json", "Object raw path/slot differs")
        command = obj["command"]
        command_ok(command)
        exact(commands[obj["commandReceiptSha256"]], command, "Original raw command record differs")
        validate_observation(observed[obj["observationSha256"]], context, fingerprint)
        origin = context["actualExecutionRoot"].replace("\\", "/") + "/objects/" + key
        argv = [*context["argvTemplate"][:-2], origin + "/request.json", origin + "/observation.json"]
        require(len(command["argv"]) == len(argv) and
                all(historical_path(a) == historical_path(b) for a, b in zip(command["argv"], argv)) and
                historical_path(command["cwd"]) == historical_path(context["workingDirectory"]),
                "Original object command role/isolation differs")
    suites = receipt["suites"]
    require(set(suites) == set(COUNTS), "Suite report denominator differs")
    for name, count in COUNTS.items():
        suite = suites[name]
        require(suite["passed"] is True and type(suite["caseCount"]) is int and suite["caseCount"] == count,
                "Suite evaluation failed")
        cases = suite["cases"]
        require([case["id"] for case in cases] == [case["caseId"] for case in plan["suites"][name]["cases"]],
                "Case identities/order differ")
        for case, original in zip(cases, plan["suites"][name]["cases"]):
            require(case["passed"] is True, "A case evaluation failed")
            h = original["requestSha256"]
            exact(case["executionReferences"], {role: [execution_key(h, contexts[role], i) for i in range(repeat)]
                                               for role in contexts}, "Case observation references differ")
            observations = {role: [observed[objects[key]["observationSha256"]] for key in case["executionReferences"][role]]
                            for role in contexts}
            actual = evaluate_case(original["definition"], contained(root, original["request"]),
                                   observations["reference"], observations["candidate"], repeat)
            actual["executionReferences"] = case["executionReferences"]
            require(actual["passed"] is True, "Recomputed layout comparison/geometry/input/determinism failed")
            require(all(row["rawStrict"]["passed"] is False and row["rawStrict"]["exact"]["differences"]
                        for row in actual["comparisons"]), "Original strict differences were erased")
            exact(case, case_receipt(actual), "Stored suite view differs from independently recomputed original observations")
    require(type(receipt["identityCommands"]) is list and len(receipt["identityCommands"]) == 3, "Identity command denominator differs")
    cwd = contexts["candidate"]["workingDirectory"].replace("\\", "/")
    identity = contexts["candidate"]["identity"]
    identity_roles = [
        (identity["queryCommandSha256"], [identity["python"], "-I", "-c", VERSION_QUERY]),
        (contexts["reference"]["identity"]["queryCommandSha256"], [contexts["reference"]["identity"]["node"], "--version"]),
        (identity["installedCommandSha256"], [identity["python"], "-I", cwd + "/scripts/verify_installed_wheel.py", identity["wheel"],
                                               "--out", contexts["candidate"]["actualExecutionRoot"].replace("\\", "/") + "/installed-wheel.json"]),
    ]
    for row, (fingerprint, argv) in zip(receipt["identityCommands"], identity_roles):
        command_ok(row)
        exact(commands[fingerprint], row, "Original identity command bytes differ")
        require(len(row["argv"]) == len(argv) and all(historical_path(a) == historical_path(b) for a, b in zip(row["argv"], argv)) and
                historical_path(row["cwd"]) == historical_path(cwd), "Original identity command role/isolation differs")
    validate_timing(report, objects, receipt["identityCommands"])
    from validate_e08_api import validate_candidate_receipt
    native = receipt["apiRuntime"]
    validate_candidate_receipt(native, root)
    exact(native["installed"], installed, "API/lifecycle and geometry must use the same installed wheel")
    require(historical_path(native["candidatePython"]) == historical_path(contexts["candidate"]["identity"]["python"]),
            "API/lifecycle and geometry interpreter identities differ")
    return metadata


def historical_material(root=ROOT):
    """Return the frozen E08 audit read closure; never import its package."""
    root = Path(root)
    manifest_path = root / HISTORY / "manifest.json"
    archive_path = root / HISTORY / "audit-material.zip"
    require(sha256(manifest_path) == HISTORY_MANIFEST_SHA, "Historical E08 manifest bytes differ")
    manifest = load(manifest_path)
    require(sha256(archive_path) == manifest["archiveSha256"] == HISTORY_ARCHIVE_SHA,
            "Historical E08 audit archive bytes differ")
    require(sha256(root / HISTORY / manifest["wheel"]) == manifest["wheelSha256"] ==
            "aeb7071779897bfbf09f2f85a80d29f8d07e6d9767d1b13b8cefe31fd3a522aa",
            "Historical E08 wheel bytes differ")
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and set(names) == set(manifest["filesSha256"]),
                "Historical E08 input denominator differs")
        material = {}
        for name in names:
            require(type(name) is str and not name.startswith("/") and "\\" not in name and ":" not in name and
                    all(part not in ("", ".", "..") for part in name.split("/")),
                    "Historical E08 input path escapes archive")
            raw = archive.read(name)
            require(hashlib.sha256(raw).hexdigest() == manifest["filesSha256"][name],
                    "Historical E08 input bytes differ: " + name)
            material[name] = raw
    return material


def check(root=ROOT, *, historical=False):
    root = Path(root)
    try:
        if historical:
            material = historical_material(root)
            with tempfile.TemporaryDirectory(prefix="pyelk-e08-history-") as folder:
                frozen = Path(folder)
                for name, raw in material.items():
                    target = frozen / name
                    require(target.resolve().is_relative_to(frozen.resolve()), "Historical E08 path escapes extraction root")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
                import layout_checks
                previous = layout_checks.ROOT
                try:
                    layout_checks.ROOT = frozen
                    result = check(frozen)
                finally:
                    layout_checks.ROOT = previous
            require(not result["errors"], "Frozen E08 audit failed: " + str(result["errors"]))
            return {"schema": "py-elk-e08-runtime-validation/v1", "status": "E08_HISTORICAL_RUNTIME_EVIDENCE_VALIDATED",
                    "errors": [], "currentPackageBytesValidated": False, "currentDistributionMetadataValidated": False,
                    "historicalPackageBytesValidated": True, "historicalDistributionMetadataValidated": True,
                    "runtimeReexecuted": False, "historicalExecutionAuthenticated": False,
                    "pythonAlgorithmsVerified": 0,
                    "limitation": "Frozen E08 original bytes and raw receipts recomputed. No archived package execution or current E09 certification."}
        audit = load(root / AUDIT)
        require(audit["schema"] == "py-elk-e08-runtime-audit/v1" and audit["scope"] == SCOPE_ID,
                "E08 runtime audit identity differs")
        no_full_acceptance(audit)
        lock, ledger = load(root / "UPSTREAM.json"), load(root / "docs/compatibility.json")
        native_host = lock["python"]["nativeHost"]
        require(lock["python"]["runtimeEvidence"] == AUDIT and native_host["scope"] == SCOPE_ID and
                native_host["evidence"] == {"path": AUDIT, "sha256": sha256(root / AUDIT)},
                "Current native host declaration/evidence differs")
        exact(ledger["nativeHost"], native_host, "Current host ledgers disagree")
        exact(native_host["defaultRegistryCounts"], {"algorithms": 1, "options": 9, "categories": 1},
              "Native registry declaration differs")
        exact(lock["python"]["implementedAlgorithms"], [], "Whole-algorithm declaration was promoted")
        no_full_acceptance(native_host)
        exact(lock["metadataCapture"]["counts"], {"algorithms": 12, "options": 243, "categories": 8},
              "Reference catalogue denominator differs")
        require(set(audit["filesSha256"]) == {INSTALLED, APPROVALS, CONTRACT,
                "references/e08-api-validation.json", "references/e08-api-metadata-sources.json",
                "references/e08-execution-sources.json", "references/e08-metadata-schema.json"},
                "E08 evidence file denominator differs")
        for name, fingerprint in audit["filesSha256"].items():
            require(sha256(contained(root, name)) == fingerprint, "E08 evidence SHA differs: " + name)
        approval = load(root / APPROVALS)
        require(approval["schema"] == "py-elk-e08-component-approvals/v1" and approval["status"] == "approved-for-ADR0007-host-only",
                "E08 host source approvals incomplete")
        require(set(approval["pythonFilesSha256"]) == HOST_PYTHON, "E08 host code approval denominator differs")
        for name, fingerprint in approval["pythonFilesSha256"].items():
            require(sha256(contained(root, name)) == fingerprint, "Approved E08 code bytes differ")
        require(set(approval["reviewEvidence"]) == {"A-execution", "V-api-metadata", "B-reference-and-runtime"},
                "Independent host review denominator differs")
        for lane, row in approval["reviewEvidence"].items():
            require(sha256(contained(root, row["path"])) == row["sha256"], "Independent host review bytes differ")
            review = load(contained(root, row["path"]))
            require(review["accepted"] is True and review["blockers"] == [], "Independent host review rejected or incomplete")
            require(REVIEW_FILES[lane] <= review["filesSha256"].keys(), "Independent review file coverage differs")
            for name, fingerprint in review["filesSha256"].items():
                require(sha256(contained(root, name)) == fingerprint, "Independently reviewed code bytes differ")
        kernel = kernel_sources(root, require_approved=True)
        require(not kernel["errors"] and kernel["wholeSourceApproved"], "Inherited E07 kernel source gate incomplete")
        receipt = load(root / INSTALLED)
        metadata = validate_layout_receipt(receipt, root)
        from validate_e08_api import check as api_check
        api = api_check(root)
        require(api["passed"] is True, "E08 API reference/host facts incomplete: " + str(api.get("errors")))
        return {"schema": "py-elk-e08-runtime-validation/v1", "status": "E08_CURRENT_RUNTIME_EVIDENCE_VALIDATED",
                "errors": [], "currentPackageBytesValidated": True, "currentDistributionMetadataValidated": True,
                "distributionMetadata": metadata, "apiReferenceValidation": api,
                "nativeRuntimeEvidenceValidated": True, "runtimeReexecuted": False,
                "historicalExecutionAuthenticated": False, "pythonAlgorithmsVerified": 0,
                "limitation": "Current bytes and portable genuine-run receipt consistency only. Fresh installed API/lifecycle and layout execution are separate; no historical authentication, full algorithm or release acceptance."}
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError, zipfile.BadZipFile) as error:
        return {"schema": "py-elk-e08-runtime-validation/v1", "status": "FAIL", "errors": [str(error)],
                "currentPackageBytesValidated": False, "runtimeReexecuted": False, "pythonAlgorithmsVerified": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--historical", action="store_true", help="Audit frozen E08 inputs without certifying current E09 code")
    args = parser.parse_args()
    result = check(historical=args.historical)
    if args.out:
        write(args.out, result)
    print(json.dumps(result, indent=2))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
