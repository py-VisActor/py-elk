"""Recompute current E09 same-wheel evidence; old receipts certify history only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from layout_checks import ROOT, contained, load, sha256, write
from validate_e04_runtime import exact, no_full_acceptance, require
from validate_e08_runtime import validate_layout_receipt, historical_path

AUDIT = "references/e09-runtime-audit.json"
INSTALLED = "references/e09-installed-check.json"
COVERAGE = "references/e09-coverage-installed.json"
BRANCH_MAP = "references/e09-branch-evidence-map.json"
APPROVALS = "references/e09-component-approvals.json"
CONTRACT = "references/e09-host-contract.json"
SCHEMA = "references/e09-metadata-schema.json"
SCOPE_ID = "E09-ADR0008-revision1"
PYTHON_FILES = {
    "src/pyelk/execution/diagnostics.py", "src/pyelk/execution/worker.py",
    "src/pyelk/algorithms/layered/pipeline.py", "src/pyelk/algorithms/layered/phases.py",
    "src/pyelk/algorithms/layered/layering.py", "src/pyelk/algorithms/layered/placement.py",
    "src/pyelk/algorithms/layered/import_export.py",
    "src/pyelk/algorithms/layered/scope.py", "src/pyelk/metadata/_data.py",
}
REVIEW_FILES = {
    "A-diagnostics": PYTHON_FILES | {CONTRACT, SCHEMA},
    "B-coverage": {"scripts/build_e09_suite.py", "scripts/validate_e09_coverage.py",
                   "tools/reference/capture_e09_layout.cjs", "tests/conformance/test_e09_coverage.py",
                   "tests/audit/test_e09_coverage_validation.py"},
    "V-host-audit": {"scripts/validate_e09_runtime.py", "scripts/validate_e08_runtime.py",
                     "scripts/validate_e08_api.py", "tests/conformance/test_e08_api_lifecycle.py",
                     "scripts/check.py", "scripts/validate_completion_state.py",
                     "scripts/validate_e09_branch_evidence.py", BRANCH_MAP,
                     "tools/reference/e09_host_lifecycle_probe.py", "tests/execution/test_e09_lifecycle_probe.py",
                     "scripts/e09_geometry_premise.py", "scripts/layout_checks.py", "tests/validation/test_e09_geometry.py",
                     "references/e09-geometry-premise.json", "references/e09-geometry-regression.json"},
}


def validate_reviews(approval, root):
    require(approval["schema"] == "py-elk-e09-component-approvals/v1" and
            approval["status"] == "approved-for-ADR0008-bounded-diagnostics-only",
            "E09 implementation approvals incomplete")
    exact(set(approval["pythonFilesSha256"]), PYTHON_FILES, "E09 changed production denominator differs")
    for name, fingerprint in approval["pythonFilesSha256"].items():
        require(sha256(contained(root, name)) == fingerprint, "Approved E09 production bytes differ: " + name)
    exact(set(approval["reviewEvidence"]), set(REVIEW_FILES), "E09 independent review denominator differs")
    for lane, row in approval["reviewEvidence"].items():
        require(sha256(contained(root, row["path"])) == row["sha256"], "E09 independent review bytes differ")
        review = load(contained(root, row["path"]))
        require(review["accepted"] is True and review["blockers"] == [], "E09 independent review rejected/incomplete")
        require(REVIEW_FILES[lane] <= review["filesSha256"].keys(), "E09 independent review omits required files: " + lane)
        for name, fingerprint in review["filesSha256"].items():
            require(sha256(contained(root, name)) == fingerprint, "E09 independently reviewed bytes differ: " + name)


def check(root=ROOT):
    root = Path(root)
    try:
        from validate_e09_sources import check as source_check, validate_branch_matrix
        from validate_e09_coverage import validate_candidate_receipt
        from validate_e09_branch_evidence import validate_branch_evidence, check_geometry_source
        sources = source_check(root)
        require(sources["passed"] is True and sources["errors"] == [], "E09 diagnostic source gate failed: " + str(sources))
        geometry_sources = check_geometry_source(root)
        require(geometry_sources["passed"] is True and geometry_sources["errors"] == [],
                "E09 adjacent-rank source proof incomplete: " + str(geometry_sources))
        branches = validate_branch_matrix(load(root / "references/e09-branch-matrix.json"), root)
        require(branches["passed"] is True and branches["errors"] == [], "E09 declaration matrix invalid: " + str(branches))
        from validate_e07_source_bindings import check as kernel_check
        kernel = kernel_check(root, require_approved=True)
        require(kernel["errors"] == [] and kernel["wholeSourceApproved"] is True and
                kernel["approvedEvidence"]["approvedComponents"] == 33,
                "Inherited E07 guarded kernel source approval incomplete")
        inherited = root / "references/e08-component-approvals.json"
        require(sha256(inherited) == "786cf3c1943d70c1186900b8b42a17c07fd1ef224fb9adc46f7f31f8ed886719",
                "Inherited E08 host approval bytes differ")
        for name, fingerprint in load(inherited)["pythonFilesSha256"].items():
            if name not in PYTHON_FILES:
                require(sha256(contained(root, name)) == fingerprint, "Unchanged E08 host source differs: " + name)
        audit = load(root / AUDIT)
        require(audit["schema"] == "py-elk-e09-runtime-audit/v1" and audit["scope"] == SCOPE_ID,
                "E09 current runtime audit identity differs")
        no_full_acceptance(audit)
        required = {INSTALLED, COVERAGE, APPROVALS, CONTRACT, SCHEMA,
                    "references/e09-coverage-validation.json", "references/e09-diagnostics-sources.json",
                    "references/e09-source-approvals.json", "references/e09-branch-matrix.json",
                    "docs/release-profiles.json", BRANCH_MAP,
                    "references/e09-geometry-premise.json", "references/e09-geometry-regression.json"}
        exact(set(audit["filesSha256"]), required, "E09 evidence file denominator differs")
        for name, fingerprint in audit["filesSha256"].items():
            require(sha256(contained(root, name)) == fingerprint, "E09 evidence bytes differ: " + name)
        validate_reviews(load(root / APPROVALS), root)
        host = load(root / CONTRACT)
        require(host["id"] == SCOPE_ID and host["loggingTrueSupported"] is True and
                host["measureExecutionTimeTrueSupported"] is True, "E09 diagnostic declaration differs")
        geometry = load(root / INSTALLED)
        metadata = validate_layout_receipt(geometry, root)
        require("_licenses/NOTICE-E09.md" in geometry["installed"]["packageFilesSha256"], "E09 packaged notice missing")
        coverage = load(root / COVERAGE)
        validation = validate_candidate_receipt(coverage, root)
        require(validation["passed"] is True, "E09 first-release branch evidence failed")
        require(validation.get("hostProbeValidated") is True, "E09 installed host branches were not validated")
        exact(coverage["installed"], geometry["installed"], "E09 branch and geometry/API evidence use different wheels")
        require(historical_path(coverage["candidatePython"]) ==
                historical_path(geometry["contexts"]["candidate"]["identity"]["python"]),
                "E09 branch and geometry/API interpreters differ")
        branch_evidence = validate_branch_evidence(load(root / BRANCH_MAP),
                {"geometry": geometry, "api": geometry["apiRuntime"], "newcoverage": coverage}, root=root)
        require(branch_evidence["passed"] is True and branch_evidence["pending"] == [],
                "E09 required branch evidence incomplete: " + str(branch_evidence))
        lock, ledger = load(root / "UPSTREAM.json"), load(root / "docs/compatibility.json")
        host_declaration = lock["python"]["nativeHost"]
        require(host_declaration["scope"] == SCOPE_ID and lock["python"]["runtimeEvidence"] == AUDIT and
                host_declaration["evidence"] == {"path": AUDIT, "sha256": sha256(root / AUDIT)},
                "E09 current declaration/evidence differs")
        exact(ledger["nativeHost"], host_declaration, "E09 host ledgers disagree")
        exact(host_declaration["defaultRegistryCounts"], {"algorithms": 1, "options": 9, "categories": 1},
              "E09 implemented registry counts differ")
        exact(lock["python"]["implementedAlgorithms"], [], "Whole algorithm acceptance was promoted")
        exact(lock["metadataCapture"]["counts"], {"algorithms": 12, "options": 243, "categories": 8},
              "Full official catalogue denominator differs")
        no_full_acceptance(host_declaration)
        return {"schema": "py-elk-e09-runtime-validation/v1", "status": "E09_CURRENT_RUNTIME_EVIDENCE_VALIDATED",
                "passed": True, "errors": [], "currentPackageBytesValidated": True,
                "currentDistributionMetadataValidated": True, "distributionMetadata": metadata,
                "branchCoverageValidation": validation, "sourceValidation": sources,
                "declarationMatrixValidation": branches,
                "branchEvidenceValidation": branch_evidence,
                "geometrySourceValidation": geometry_sources,
                "runtimeReexecuted": False, "historicalExecutionAuthenticated": False,
                "pythonAlgorithmsVerified": 0, "packagePublished": False}
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError, ImportError) as error:
        return {"schema": "py-elk-e09-runtime-validation/v1", "status": "FAIL", "passed": False,
                "errors": [str(error)], "currentPackageBytesValidated": False, "runtimeReexecuted": False,
                "pythonAlgorithmsVerified": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--historical", action="store_true",
                        help="Purely validate the sealed original E09/E10 audit archive; never certify current source")
    args = parser.parse_args()
    if args.historical:
        from iteration.e11_history import check as check_history
        result = check_history()
    else:
        result = check()
    if args.out:
        write(args.out, result)
    print(json.dumps(result, indent=2))
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
