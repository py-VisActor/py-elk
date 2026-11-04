"""Fresh-session checks with saved commands/logs; optional genuine oracle replay.

Includes the full native API, legacy-kernel regressions and explicit historical
receipt audits. Whole-algorithm/platform/release acceptance remains separate.
"""
import argparse
import base64
from pathlib import Path
import sys

from layout_checks import ROOT, sha256, write
from validate_layout import run, source_hashes
from change_impact import changed_since, execution_context, input_hashes, plan_changes, select_steps
from layout_checks import load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New directory for all evidence")
    parser.add_argument("--with-reference", action="store_true", help="Also check local upstream and recapture all cases with Node")
    parser.add_argument("--affected", action="store_true", help="Development-only selection; never final acceptance")
    parser.add_argument("--baseline", type=Path, help="Complete input fingerprint manifest for --affected")
    parser.add_argument("--changed", nargs="+", help="Explicit changed paths for --affected")
    args = parser.parse_args()
    if args.affected and (bool(args.baseline) == bool(args.changed) or args.with_reference):
        parser.error("--affected requires exactly one of --baseline/--changed and excludes --with-reference")
    if not args.affected and (args.baseline or args.changed):
        parser.error("--baseline/--changed require --affected")
    inputs_before = input_hashes()
    out = args.out.resolve()
    if out.is_relative_to(ROOT) and out.relative_to(ROOT).parts[0] != "test-runs":
        parser.error("Keep generated evidence under test-runs, or outside the checkout")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(exist_ok=False)
    python = sys.executable
    steps = [
        ("bootstrap", [python, "scripts/validate_bootstrap.py"]),
        ("bootstrap-tests", [python, "-m", "unittest", "discover", "-s", "tests/bootstrap", "-v"]),
        ("validator-tests", [python, "-m", "unittest", "discover", "-s", "tests/validation", "-v"]),
        ("contract-tests", [python, "-m", "unittest", "discover", "-s", "tests/contract", "-v"]),
        ("foundation-tests", [python, "-m", "unittest", "discover", "-s", "tests/foundation", "-v"]),
        ("model-tests", [python, "-m", "unittest", "discover", "-s", "tests/model", "-v"]),
        ("option-tests", [python, "-m", "unittest", "discover", "-s", "tests/options", "-v"]),
        ("context-tests", [python, "-m", "unittest", "discover", "-s", "tests/execution", "-v"]),
        ("layered-tests", [python, "-m", "unittest", "discover", "-s", "tests/layered", "-v"]),
        ("api-tests", [python, "-m", "unittest", "discover", "-s", "tests/api", "-v"]),
        ("conformance-tests", [python, "-m", "unittest", "discover", "-s", "tests/conformance", "-v"]),
        ("audit-tests", [python, "-m", "unittest", "discover", "-s", "tests/audit", "-v"]),
        ("source-audit", [python, "scripts/validate_e01_audit.py"]),
        ("native-contract", [python, "scripts/validate_e02_contract.py"]),
        ("host-foundations", [python, "scripts/validate_e03_foundations.py", "--historical"]),
        ("e04-suite", [python, "scripts/build_slice_suite.py", "check", "--suite", "tests/fixtures/suites/E04"]),
        ("e04-source-bindings", [python, "scripts/validate_e04_source_bindings.py"]),
        ("e04-runtime-evidence", [python, "scripts/validate_e04_runtime.py", "--historical"]),
        ("e05-suite", [python, "scripts/build_e05_suite.py", "check", "--suite", "tests/fixtures/suites/E05"]),
        ("e05-source-bindings", [python, "scripts/validate_e05_source_bindings.py", "--require-approved"]),
        ("e05-runtime-evidence", [python, "scripts/validate_e05_runtime.py", "--historical"]),
        ("e06-suite", [python, "scripts/build_e06_suite.py", "check", "--suite", "tests/fixtures/suites/E06"]),
        ("e06-source-bindings", [python, "scripts/validate_e06_source_bindings.py", "--require-approved"]),
        ("e06-runtime-evidence", [python, "scripts/validate_e06_runtime.py", "--historical"]),
        ("e07-suite", [python, "scripts/build_e07_suite.py", "check", "--suite", "tests/fixtures/suites/E07"]),
        ("e07-source-bindings", [python, "scripts/validate_e07_source_bindings.py", "--require-approved"]),
        ("e07-runtime-evidence", [python, "scripts/validate_e07_runtime.py", "--historical"]),
        ("e08-api", [python, "scripts/validate_e08_api.py"]),
        ("e08-runtime-evidence", [python, "scripts/validate_e08_runtime.py", "--historical"]),
        ("e09-source-bindings", [python, "scripts/validate_e09_sources.py"]),
        ("e09-suite", [python, "scripts/build_e09_suite.py", "check", "--suite", "tests/fixtures/suites/E09"]),
        ("e09-coverage", [python, "scripts/validate_e09_coverage.py", "--historical"]),
        ("e09-runtime-evidence", [python, "scripts/validate_e09_runtime.py", "--historical"]),
        ("assertion-index", [python, "scripts/audit_assertions.py", "check"]),
        ("selftest", [python, "scripts/validate_layout.py", "selftest", "--out", str(out / "controls")]),
        ("full-native-interfaces", [python, "scripts/iteration/implementation_interfaces.py",
                                    "--source-dir", "src", "--out", str(out / "full-native-interfaces.json")]),
        ("full-native-host", [python, "scripts/validate_full_host.py", "--out", str(out / "full-native-host")]),
    ]
    if args.with_reference:
        steps.extend([
            ("upstream", [python, "scripts/upstream.py", "check"]),
            ("source-audit-upstream", [python, "scripts/validate_e01_audit.py", "--with-upstream"]),
            ("native-contract-upstream", [python, "scripts/validate_e02_contract.py", "--with-upstream"]),
            ("host-foundations-upstream", [python, "scripts/validate_e03_foundations.py", "--with-upstream", "--historical"]),
            ("e04-source-bindings-upstream", [python, "scripts/validate_e04_source_bindings.py", "--with-upstream"]),
            ("e05-source-bindings-upstream", [python, "scripts/validate_e05_source_bindings.py", "--with-upstream", "--require-approved"]),
            ("e06-source-bindings-upstream", [python, "scripts/validate_e06_source_bindings.py", "--with-upstream", "--require-approved"]),
            ("e07-source-bindings-upstream", [python, "scripts/validate_e07_source_bindings.py", "--with-upstream", "--require-approved"]),
            ("assertion-index-upstream", [python, "scripts/audit_assertions.py", "check", "--with-upstream"]),
            ("capture", [python, "scripts/validate_layout.py", "reference", "--out", str(out / "reference"), "--repeat", "3"]),
            ("replay", [python, "scripts/validate_layout.py", "replay", "--reference", "references/layout", "--candidate", str(out / "reference"), "--out", str(out / "replay.json")]),
            ("path-trace", ["node", "tools/reference/trace_layered_path.cjs", ".local/npm-elkjs/package",
                            "tests/fixtures/validation/requests/layered-diamond-right.json", str(out / "path-trace")]),
            ("contract-capture", ["node", "tools/reference/capture_contracts.cjs", ".local/npm-elkjs/package", str(out / "contract-probes")]),
            ("contract-replay", [python, "scripts/validate_e02_contract.py", "--replay", str(out / "contract-probes/index.json")]),
            ("contract-collector-controls", [python, "tests/contract/live_collector_failclosed.py", "--out", str(out / "collector-controls")]),
            ("e04-rng", ["node", "tools/reference/probe_e04_rng.cjs", ".local/npm-elkjs/package", str(out / "e04-rng.json")]),
            ("e08-api-reference", [python, "scripts/validate_e08_api.py", "--with-reference", "--out", str(out / "e08-api-reference")]),
            ("e09-source-bindings-upstream", [python, "scripts/validate_e09_sources.py", "--with-upstream"]),
            ("e09-coverage-reference", [python, "scripts/validate_e09_coverage.py", "--with-reference", "--out", str(out / "e09-coverage-reference")]),
        ])
    impact = None
    if args.affected:
        impact = plan_changes(changed_since(load(args.baseline)) if args.baseline else args.changed)
        steps = select_steps(steps, impact)
        write(out / "impact.json", impact)
    planned_steps = [name for name, _ in steps]
    records = []
    for name, command in steps:
        # Capture output itself uses a new directory, so command logs stay separate.
        directory = out / (name + "-command")
        directory.mkdir()
        print("Checking " + name, flush=True)
        # The audit group includes positive copies before semantic mutations.
        # E07 adds an actually measured95s runtime-receipt test file; retain
        # every check while allowing the enlarged group its execution time.
        record = run(command, directory, 600 if name.startswith("audit-tests") else 300)
        records.append({"name": name, **record})
        if record["exitCode"] != 0:
            print(f"{name} failed (exit {record['exitCode']}); see {directory}", flush=True)
            print((directory / "stderr.log").read_text(encoding="utf-8", errors="replace")[-4000:], flush=True)
    inputs_after = input_hashes()
    passed = bool(records) and all(r["exitCode"] == 0 for r in records) and inputs_before == inputs_after
    status = "AFFECTED_CHECKS_PASS" if args.affected else "DEVELOPMENT_CHECKS_PASS"
    report = {"schema": "py-elk-development-check/v1", "status": status if passed else "FAIL",
              "passed": passed, "commands": records, "sourceSha256": source_hashes(),
              "checkMode": "affected" if args.affected else "full", "fullValidation": passed and not args.affected,
              "plannedSteps": planned_steps, "inputFilesSha256": inputs_before,
              "executionContext": execution_context(with_reference=args.with_reference),
              "projectRoot": str(ROOT.resolve()),
              "completionPlanAtExecution": load(ROOT / "docs/iteration-plan.json"),
              "completionPlanBytesBase64": base64.b64encode((ROOT / "docs/iteration-plan.json").read_bytes()).decode("ascii"),
              "inputsUnchanged": inputs_before == inputs_after,
              "changedDuringExecution": [name for name in inputs_before.keys() | inputs_after.keys()
                                         if inputs_before.get(name) != inputs_after.get(name)],
              "files": {p.relative_to(out).as_posix(): sha256(p) for p in sorted(out.rglob("*")) if p.is_file()},
              "pythonAlgorithmsVerified": 0, "nativeAlgorithmsImplemented": 12,
              "legacyKernelRegressionScope": "E07-ADR0006-revision1",
              "nativeHostScope": "full-native-persistent-runtime",
              "limitation": "Development checks execute the full native public API and retained kernel regressions. E04-E09 runtime receipts are explicit frozen historical audits and do not certify current package bytes. Full algorithm differential suites and same-wheel installation are separate receipts. Declaration inventory does not prove exhaustive paths or publication acceptance."}
    write(out / "report.json", report)
    print(report["status"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
