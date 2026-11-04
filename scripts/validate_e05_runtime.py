"""Validate E05's installed receipts against current package bytes, without execution.

The fresh execution command is check_e05_slice.py. This offline audit checks
bounded claims and semantic receipt consistency; it does not authenticate old
logs, rerun Python/JS, or prove mathematical equivalence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from layout_checks import ROOT, contained, load, sha256, write
from validate_e04_runtime import (
    BASELINE, CLAIMS, exact, no_full_acceptance, require, suite_requests,
    validate_claims, validate_installed, validate_numeric, validate_seed_policy,
    historical_material as _historical_material,
)
from validate_e05_source_bindings import check as check_sources

AUDIT = "references/e05-runtime-audit.json"
INSTALLED = "references/e05-installed-check.json"
SCOPE = "docs/decisions/0004-e05-dag-long-edge.md"
SCOPE_ID = "E05-ADR0004-revision1"
SUITE = "tests/fixtures/suites/E05/cases.json"
SELECTION = "tests/fixtures/suites/E05/selection.json"
APPROVALS = "references/e05-component-approvals.json"
DENOMINATORS = {"algorithms": 12, "options": 243, "categories": 8, "masterCases": 25,
                "selectedMasterCases": 12, "excludedMasterCases": 13,
                "projectVariants": 24, "sliceCases": 36}
SCOPE_VALUE = {"id": SCOPE_ID, "document": SCOPE,
               "topology": "flat-connected-directed-simple-acyclic-graph",
               "minimumNodes": 0, "maximumNodes": 8, "maximumInternalNodes": 64,
               "directions": ["RIGHT", "UNDEFINED"], "edgeRouting": "ORTHOGONAL",
               "numericMaximum": 1_000_000, "nonzeroSigned32Seed": True,
               "explicitPaddingType": "string", "renewSourceApprovalBeforeExpansion": True}
REQUIRED_FILES = {INSTALLED, SCOPE, SUITE, SELECTION, APPROVALS,
                  "references/e04-determinism-policy.json", "references/e04-numeric-regressions.json"}
HISTORICAL_MATERIAL = "references/history/E05/material.json"
HISTORICAL_WHEEL = "references/history/E05/py_elk-0.0.1a0-py3-none-any.whl"
HISTORICAL_WHEEL_SHA = "13d677684eabe65fdc9c9f003178c775a16b2e26f08372fd76043f3d5e810b03"
HISTORICAL_DECLARATIONS = {
    "UPSTREAM.json": "1a746a5d83058b7d954ebf0bf889b837ee75688eae8a96948308bd43d51174b5",
    "docs/compatibility.json": "7c130ad3d30256af19823e657dcbf92ac778e081cfa04cc163123ce73d51e621",
}


def historical_material(root):
    return _historical_material(Path(root), iteration="E05", material_path=HISTORICAL_MATERIAL,
                                wheel_path=HISTORICAL_WHEEL, wheel_sha=HISTORICAL_WHEEL_SHA,
                                declarations_sha=HISTORICAL_DECLARATIONS)


def requests(root):
    return suite_requests(root, suite_path=SUITE, selection_path=SELECTION,
                          selected_count=12, excluded_count=13, variant_count=24, case_count=36)


def check(root=ROOT, *, historical=False):
    root = Path(root)
    errors = []
    sources = None
    try:
        audit = load(root / AUDIT)
        require(audit["schema"] == "py-elk-e05-runtime-audit/v1" and audit["iteration"] == "E05"
                and audit["status"] == "E05_EXPERIMENTAL_SLICE_VERIFIED", "E05 audit identity/status differs")
        exact(audit["baseline"], BASELINE, "E05 baseline differs")
        exact(audit["scope"], SCOPE_VALUE, "E05 bounded scope differs")
        exact(audit["runtimeClaims"], CLAIMS, "E05 runtime claims differ")
        exact(audit["coverageDenominators"], DENOMINATORS, "E05 denominator differs")
        exact(audit["pythonAlgorithmsVerified"], 0, "Full algorithm count must remain zero")
        exact(audit["availableExperimentalAlgorithms"], ["org.eclipse.elk.layered"], "Experimental algorithm differs")
        require(audit["installedEvidence"] == INSTALLED and audit["algorithmSourceGate"] ==
                "verified-for-guarded-generated-source-slice-only", "E05 evidence category differs")
        require(set(audit["filesSha256"]) == REQUIRED_FILES, "E05 evidence file denominator differs")
        for path, fingerprint in audit["filesSha256"].items():
            require(sha256(contained(root, path)) == fingerprint, "Versioned E05 evidence SHA differs: " + path)
        no_full_acceptance(audit)
        sources = check_sources(root, require_approved=True)
        require(not sources["errors"] and sources["wholeSourceApproved"], "E05 source gate is incomplete: " + str(sources["errors"]))
        package_bytes = None
        if historical:
            declarations, package_bytes = historical_material(root)
            lock, ledger = declarations["UPSTREAM.json"], declarations["docs/compatibility.json"]
        else:
            lock, ledger = load(root / "UPSTREAM.json"), load(root / "docs/compatibility.json")
        validate_claims(lock, ledger, sha256(root / AUDIT), root,
                        audit_path=AUDIT, scope_id=SCOPE_ID, case_count=36)
        installed = load(root / INSTALLED)
        if historical:
            require(installed["wheelSha256"] == HISTORICAL_WHEEL_SHA, "Historical installed wheel receipt differs")
        require(installed["wheelVersion"] == lock["python"]["scaffoldVersion"], "Installed wheel/declaration version differs")
        validate_installed(installed, requests(root), root, package_bytes=package_bytes, iteration="E05", suite_path=SUITE,
                           case_count=36, builder="scripts/build_e05_suite.py",
                           additional_licenses=("_licenses/NOTICE-E05.md",))
        validate_seed_policy(root)
        validate_numeric(load(root / "references/e04-numeric-regressions.json"))
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError, zipfile.BadZipFile) as error:
        errors.append(str(error))
    return {"schema": "py-elk-e05-runtime-validation/v1",
            "status": "FAIL" if errors else "E05_RUNTIME_EVIDENCE_VALIDATED", "errors": errors,
            "currentPackageBytesValidated": not errors and not historical,
            "historicalPackageBytesValidated": not errors and historical,
            "installedEvidenceValidated": not errors, "runtimeReexecuted": False,
            "historicalWheelAuthenticated": False, "mathematicalEquivalenceAutomaticallyProved": False,
            "pythonAlgorithmsVerified": 0,
            "limitation": "Offline validation of recorded claims and explicitly selected package bytes. Historical mode checks the frozen E05 archive and declarations and cannot certify new current sources. Fresh E05 execution uses check_e05_slice.py; newer scopes require their own installed evidence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--historical", action="store_true", help="Check frozen E05 material, never certify newer current code")
    args = parser.parse_args()
    report = check(historical=args.historical)
    if args.out:
        write(args.out, report)
    print(json.dumps(report, indent=2))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
