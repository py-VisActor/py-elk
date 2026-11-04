"""Recheck completion-only metadata against a real, unchanged full-check input set.

This never executes layout or authenticates historical execution. Changed code,
tests, package inputs, reference data or configuration require a new full run.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys

from change_impact import ROOT, execution_context, input_hashes
from layout_checks import load, sha256, write

CORE_STEPS = ("bootstrap", "bootstrap-tests", "validator-tests", "contract-tests", "foundation-tests",
              "model-tests", "option-tests", "context-tests", "layered-tests", "api-tests", "conformance-tests",
              "audit-tests", "source-audit", "native-contract", "host-foundations", "e04-suite", "e04-source-bindings",
              "e04-runtime-evidence", "e05-suite", "e05-source-bindings", "e05-runtime-evidence", "e06-suite",
              "e06-source-bindings", "e06-runtime-evidence", "e07-suite", "e07-source-bindings", "e07-runtime-evidence",
              "e08-api", "e08-runtime-evidence", "e09-source-bindings", "e09-suite", "e09-coverage",
              "e09-runtime-evidence", "assertion-index", "selftest", "full-native-interfaces", "full-native-host")
REFERENCE_STEPS = ("upstream", "source-audit-upstream", "native-contract-upstream", "host-foundations-upstream",
                   "e04-source-bindings-upstream", "e05-source-bindings-upstream", "e06-source-bindings-upstream",
                   "e07-source-bindings-upstream", "assertion-index-upstream", "capture", "replay", "path-trace",
                   "contract-capture", "contract-replay", "contract-collector-controls", "e04-rng", "e08-api-reference",
                   "e09-source-bindings-upstream", "e09-coverage-reference")
COMPLETION_DOCS = {"docs/iteration-plan.json", "docs/RELEASE_STATUS.md", "docs/NEW_SESSION.md",
                   "docs/PARALLEL_EXECUTION.md", "AGENTS.md"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def completion_path(name):
    return name in COMPLETION_DOCS or (name.endswith((".md", ".json")) and
           name.startswith(("docs/changes/", "docs/retrospectives/", "docs/iterations/")))


def protected_plan(plan):
    result = copy.deepcopy(plan)
    result.pop("nextIteration", None); result.pop("updatedOn", None)
    for row in result["iterations"]:
        for field in ("status", "evidence", "retrospective", "brief"):
            row.pop(field, None)
    return result


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def document_checks(root):
    from validate_bootstrap import check as check_bootstrap
    from validate_e01_audit import check
    bootstrap = check_bootstrap(root)
    require(not bootstrap["errors"], "Completion bootstrap metadata differs: " + str(bootstrap["errors"]))
    source = check(root)
    require(not source["errors"], "Completion progress/evidence differs: " + str(source["errors"]))
    return {"bootstrap": bootstrap["status"], "progress": source["status"]}


def command_roles(directory):
    """Independent command inventory, including exact discover scope and flags."""
    directory = Path(directory).resolve(); python = sys.executable
    roles = {}
    for name, group in (("bootstrap", "bootstrap"), ("validator", "validation"), ("contract", "contract"),
                        ("foundation", "foundation"), ("model", "model"), ("option", "options"),
                        ("context", "execution"), ("layered", "layered"), ("api", "api"),
                        ("conformance", "conformance"), ("audit", "audit")):
        roles[name + "-tests"] = [python, "-m", "unittest", "discover", "-s", "tests/" + group, "-v"]
    for name, script in (("bootstrap", "validate_bootstrap.py"), ("source-audit", "validate_e01_audit.py"),
                         ("native-contract", "validate_e02_contract.py"), ("host-foundations", "validate_e03_foundations.py")):
        roles[name] = [python, "scripts/" + script]
    roles['host-foundations'].append('--historical')
    for iteration in ("e04", "e05", "e06", "e07"):
        builder = "build_slice_suite.py" if iteration == "e04" else "build_" + iteration + "_suite.py"
        roles[iteration + "-suite"] = [python, "scripts/" + builder, "check", "--suite", "tests/fixtures/suites/" + iteration.upper()]
        source = [python, "scripts/validate_" + iteration + "_source_bindings.py"]
        roles[iteration + "-source-bindings"] = source + ([] if iteration == "e04" else ["--require-approved"])
        roles[iteration + "-runtime-evidence"] = [python, "scripts/validate_" + iteration + "_runtime.py", "--historical"]
        roles[iteration + "-source-bindings-upstream"] = source + ["--with-upstream"] + ([] if iteration == "e04" else ["--require-approved"])
    roles["assertion-index"] = [python, "scripts/audit_assertions.py", "check"]
    roles["selftest"] = [python, "scripts/validate_layout.py", "selftest", "--out", str(directory / "controls")]
    roles["upstream"] = [python, "scripts/upstream.py", "check"]
    for name, script in (("source-audit", "validate_e01_audit.py"), ("native-contract", "validate_e02_contract.py"), ("host-foundations", "validate_e03_foundations.py")):
        roles[name + "-upstream"] = [python, "scripts/" + script, "--with-upstream"]
    roles['host-foundations-upstream'].append('--historical')
    roles["assertion-index-upstream"] = [python, "scripts/audit_assertions.py", "check", "--with-upstream"]
    roles["capture"] = [python, "scripts/validate_layout.py", "reference", "--out", str(directory / "reference"), "--repeat", "3"]
    roles["replay"] = [python, "scripts/validate_layout.py", "replay", "--reference", "references/layout", "--candidate", str(directory / "reference"), "--out", str(directory / "replay.json")]
    roles["path-trace"] = ["node", "tools/reference/trace_layered_path.cjs", ".local/npm-elkjs/package", "tests/fixtures/validation/requests/layered-diamond-right.json", str(directory / "path-trace")]
    roles["contract-capture"] = ["node", "tools/reference/capture_contracts.cjs", ".local/npm-elkjs/package", str(directory / "contract-probes")]
    roles["contract-replay"] = [python, "scripts/validate_e02_contract.py", "--replay", str(directory / "contract-probes/index.json")]
    roles["contract-collector-controls"] = [python, "tests/contract/live_collector_failclosed.py", "--out", str(directory / "collector-controls")]
    roles["e04-rng"] = ["node", "tools/reference/probe_e04_rng.cjs", ".local/npm-elkjs/package", str(directory / "e04-rng.json")]
    roles["e08-api"] = [python, "scripts/validate_e08_api.py"]
    roles["e08-runtime-evidence"] = [python, "scripts/validate_e08_runtime.py", "--historical"]
    roles["e09-source-bindings"] = [python, "scripts/validate_e09_sources.py"]
    roles["e09-source-bindings-upstream"] = [python, "scripts/validate_e09_sources.py", "--with-upstream"]
    roles["e09-suite"] = [python, "scripts/build_e09_suite.py", "check", "--suite", "tests/fixtures/suites/E09"]
    roles["e09-coverage"] = [python, "scripts/validate_e09_coverage.py", "--historical"]
    roles["e09-runtime-evidence"] = [python, "scripts/validate_e09_runtime.py", "--historical"]
    roles["full-native-interfaces"] = [python, "scripts/iteration/implementation_interfaces.py", "--source-dir", "src",
                                      "--out", str(directory / "full-native-interfaces.json")]
    roles["full-native-host"] = [python, "scripts/validate_full_host.py", "--out", str(directory / "full-native-host")]
    roles["e09-coverage-reference"] = [python, "scripts/validate_e09_coverage.py", "--with-reference", "--out", str(directory / "e09-coverage-reference")]
    roles["e08-api-reference"] = [python, "scripts/validate_e08_api.py", "--with-reference", "--out", str(directory / "e08-api-reference")]
    return roles


def check(report_path, root=ROOT, *, metadata_validator=document_checks):
    root, report_path = Path(root), Path(report_path)
    errors, changes, documents = [], [], None
    try:
        report = load(report_path)
        require(report["schema"] == "py-elk-development-check/v1" and report["status"] == "DEVELOPMENT_CHECKS_PASS"
                and report["passed"] is True and report["fullValidation"] is True and report["checkMode"] == "full",
                "A successful real full check is required")
        require(report["inputsUnchanged"] is True and report["changedDuringExecution"] == [], "Full-check inputs changed during execution")
        planned = report["plannedSteps"]
        require(planned in (list(CORE_STEPS), list(CORE_STEPS + REFERENCE_STEPS)), "Full command denominator/order differs")
        commands = report["commands"]
        require([row["name"] for row in commands] == planned, "Missing full command receipt")
        roles = command_roles(report_path.parent)
        require(report["projectRoot"] == str(root.resolve()), "Full check belongs to a different checkout")
        for row in commands:
            require(row["exitCode"] == 0 and type(row["exitCode"]) is int and row["timedOut"] is False,
                    "A full-check command failed")
            require(row["argv"] == roles[row["name"]] and row["cwd"] == str(root.resolve()),
                    "Full command role/discover scope differs")
            directory = report_path.parent / (row["name"] + "-command")
            require(load(directory / "command.json") == {key: value for key, value in row.items() if key != "name"},
                    "Original command receipt differs")
            for stream in ("stdout", "stderr"):
                require(sha256(directory / (stream + ".log")) == row[stream + "Sha256"], "Original full-check log differs")
        context = execution_context(with_reference=planned == list(CORE_STEPS + REFERENCE_STEPS))
        require(report["executionContext"] == context, "Interpreter/platform changed; full validation required")
        old = report["inputFilesSha256"]
        require(type(old) is dict and bool(old), "Missing full input fingerprints")
        current = input_hashes(root)
        changes = sorted(name for name in old.keys() | current.keys() if old.get(name) != current.get(name))
        require(all(completion_path(name) for name in changes), "Non-completion inputs changed; full validation required")
        plan_path = root / "docs/iteration-plan.json"
        raw_plan = base64.b64decode(report["completionPlanBytesBase64"], validate=True)
        require(hashlib.sha256(raw_plan).hexdigest() == old["docs/iteration-plan.json"] and
                canonical(json.loads(raw_plan)) == canonical(report["completionPlanAtExecution"]),
                "Original plan snapshot differs from full input bytes")
        require(canonical(protected_plan(report["completionPlanAtExecution"])) == canonical(protected_plan(load(plan_path))),
                "Protected progress/gate definitions changed; full validation required")
        for name in changes:
            require((root / name).is_file(), "Completion input was removed")
            if name.endswith(".json"):
                value = load(root / name)
                if name.startswith("docs/changes/"):
                    from validate_e04_runtime import no_full_acceptance
                    no_full_acceptance(value)
        documents = metadata_validator(root)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        errors.append(str(error))
    return {"schema": "py-elk-completion-validation/v1", "status": "FULL_CHECK_REQUIRED" if errors else "COMPLETION_METADATA_VALIDATED",
            "errors": errors, "changedCompletionPaths": changes, "completionValidated": not errors,
            "fullCheckReport": {"path": str(report_path), "sha256": sha256(report_path)} if report_path.is_file() else None,
            "documentChecks": documents, "runtimeReexecuted": False, "pythonAlgorithmsVerified": 0,
            "limitation": "Unchanged-input proof plus current completion metadata and original full-check log consistency only; not a new runtime run or historical execution authentication."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(); result = check(args.report); write(args.out, result)
    print(result["status"]); return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
