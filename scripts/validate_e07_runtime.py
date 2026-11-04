"""Check E07 recorded evidence against current package, licenses and metadata.

This offline audit binds all33 guarded source components and the same72 input
requests. It does not rerun layouts, authenticate execution or prove algorithm
equivalence. Frozen earlier archives cannot certify the current E07 package.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import zipfile

from layout_checks import ROOT, contained, load, sha256, write
from validate_e04_runtime import (
    BASELINE, CLAIMS, digest, exact, no_full_acceptance, require, suite_requests,
    validate_claims, validate_installed, validate_numeric, validate_seed_policy,
    historical_material as _historical_material,
)
from validate_e06_runtime import _no_static_proof_promotion, validate_metadata as _validate_metadata
from validate_e07_source_bindings import check as check_sources

AUDIT = "references/e07-runtime-audit.json"
INSTALLED = "references/e07-installed-check.json"
SCOPE = "docs/decisions/0006-e07-directions-components.md"
SCOPE_ID = "E07-ADR0006-revision1"
SUITE = "tests/fixtures/suites/E07/cases.json"
SELECTION = "tests/fixtures/suites/E07/selection.json"
APPROVALS = "references/e07-component-approvals.json"
DENOMINATORS = {"algorithms": 12, "options": 243, "categories": 8, "masterCases": 25,
                "selectedMasterCases": 22, "excludedMasterCases": 3,
                "projectVariants": 50, "sliceCases": 72}
SCOPE_VALUE = {"id": SCOPE_ID, "document": SCOPE,
               "topology": "flat-directed-multigraph-with-weak-components",
               "minimumNodes": 0, "maximumNodes": 8, "maximumEdges": 28,
               "maximumInternalNodes": 176, "maximumInternalSegments": 196,
               "maximumInternalPorts": 392, "maximumRoutingSegmentsPerBoundary": 56,
               "directions": ["RIGHT", "LEFT", "DOWN", "UP", "UNDEFINED"],
               "separateConnectedComponents": [True, False], "edgeRouting": "ORTHOGONAL",
               "numericMaximum": 1_000_000, "nonzeroSigned32Seed": True,
               "explicitPaddingType": "string", "renewSourceApprovalBeforeExpansion": True}
REQUIRED_FILES = {INSTALLED, SCOPE, SUITE, SELECTION, APPROVALS,
                  "references/e04-determinism-policy.json", "references/e04-numeric-regressions.json"}
HISTORICAL_WHEEL = "references/history/E07/py_elk-0.0.1a0-py3-none-any.whl"
HISTORICAL_WHEEL_SHA = "5d5666944e628088615be6d7ff9f434757d9ae6787286fd621b8dd170bebbf55"
HISTORICAL_DECLARATIONS = {
    "UPSTREAM.json": "3a4ee90eb1d7eea4c4c1a57a3bbb09507ee02c433378f7a670a346069436d5a6",
    "docs/compatibility.json": "b058c6842e5dd9a9344cd3e48fbb0a663d54fd6d31093ea088eb87644bfdba6a",
}
HISTORICAL_METADATA = {
    "pyproject.toml": "6e397c8d1575a2409a7768f7a3e6f55e14fa483e71110f1415d9491bf51ed2ff",
    "README.md": "b19532c069d82f97a86bf2738a3864fe989175f3a32aaa7f9124c534d969b359",
}


def historical_material(root):
    return _historical_material(Path(root), iteration="E07",
                                material_path="references/history/E07/material.json",
                                wheel_path=HISTORICAL_WHEEL, wheel_sha=HISTORICAL_WHEEL_SHA,
                                declarations_sha=HISTORICAL_DECLARATIONS)


def historical_metadata(root, summary):
    material = load(Path(root) / "references/history/E07/metadata-material.json")
    require(material["schema"] == "py-elk-e07-historical-metadata-material/v1", "Historical metadata schema differs")
    require(set(material["files"]) == set(HISTORICAL_METADATA), "Historical metadata denominator differs")
    files = {}
    for name, fingerprint in HISTORICAL_METADATA.items():
        row = material["files"][name]
        raw = base64.b64decode(row["bytesBase64"], validate=True)
        require(row["sha256"] == fingerprint == hashlib.sha256(raw).hexdigest(),
                "Historical metadata material differs: " + name)
        files[name] = raw
    with zipfile.ZipFile(Path(root) / HISTORICAL_WHEEL) as archive:
        names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        require(len(names) == 1, "Historical METADATA member denominator differs")
        raw = archive.read(names[0])
        exact(summary["distributionMetadata"], {"archivePath": names[0],
              "sha256": hashlib.sha256(raw).hexdigest(), "bytesBase64": base64.b64encode(raw).decode("ascii")},
              "Historical METADATA receipt differs from pinned archive")
    return files


def requests(root):
    return suite_requests(root, suite_path=SUITE, selection_path=SELECTION,
                          selected_count=22, excluded_count=3, variant_count=50, case_count=72)


def validate_metadata(summary, root=ROOT, *, metadata_files=None):
    """Reuse the exact current pyproject/README and raw METADATA byte checks."""
    result = _validate_metadata(summary, root, metadata_files=metadata_files)
    result["status"] = "E07_DISTRIBUTION_METADATA_VALIDATED"
    return result


def check(root=ROOT, *, historical=False):
    root = Path(root)
    errors, sources, metadata = [], None, None
    try:
        audit = load(root / AUDIT)
        require(audit["schema"] == "py-elk-e07-runtime-audit/v1" and audit["iteration"] == "E07"
                and audit["status"] == "E07_EXPERIMENTAL_SLICE_VERIFIED", "E07 audit identity/status differs")
        exact(audit["baseline"], BASELINE, "E07 baseline differs")
        exact(audit["scope"], SCOPE_VALUE, "E07 bounded scope differs")
        exact(audit["runtimeClaims"], CLAIMS, "E07 runtime claims differ")
        exact(audit["coverageDenominators"], DENOMINATORS, "E07 denominator differs")
        exact(audit["pythonAlgorithmsVerified"], 0, "Full algorithm count must remain zero")
        exact(audit["availableExperimentalAlgorithms"], ["org.eclipse.elk.layered"], "Experimental algorithm differs")
        require(audit["installedEvidence"] == INSTALLED and audit["algorithmSourceGate"] ==
                "verified-for-guarded-generated-source-slice-only", "E07 source/evidence category differs")
        require(set(audit["filesSha256"]) == REQUIRED_FILES, "E07 evidence file denominator differs")
        for path, fingerprint in audit["filesSha256"].items():
            digest(fingerprint)
            require(sha256(contained(root, path)) == fingerprint, "Versioned E07 evidence SHA differs: " + path)
        no_full_acceptance(audit)
        _no_static_proof_promotion(audit)
        sources = check_sources(root, require_approved=True)
        require(not sources["errors"] and sources["wholeSourceApproved"],
                "E07 source gate is incomplete: " + str(sources["errors"]))
        exact(sources["componentCounts"], {"A": 4, "B": 3, "R": 26}, "E07 source component denominator differs")
        exact(sources["approvedEvidence"]["approvedComponents"], 33, "E07 source approval denominator differs")
        package_bytes, metadata_files = None, None
        if historical:
            declarations, package_bytes = historical_material(root)
            lock, ledger = declarations["UPSTREAM.json"], declarations["docs/compatibility.json"]
        else:
            lock, ledger = load(root / "UPSTREAM.json"), load(root / "docs/compatibility.json")
        validate_claims(lock, ledger, sha256(root / AUDIT), root,
                        audit_path=AUDIT, scope_id=SCOPE_ID, case_count=72)
        installed = load(root / INSTALLED)
        if historical:
            require(installed["wheelSha256"] == HISTORICAL_WHEEL_SHA, "Historical installed wheel receipt differs")
            metadata_files = historical_metadata(root, installed)
        _no_static_proof_promotion(installed)
        require(installed["wheelVersion"] == lock["python"]["scaffoldVersion"], "Installed wheel/declaration version differs")
        validate_installed(installed, requests(root), root, package_bytes=package_bytes, iteration="E07", suite_path=SUITE,
                           case_count=72, builder="scripts/build_e07_suite.py",
                           additional_licenses=("_licenses/NOTICE-E05.md", "_licenses/NOTICE-E06.md",
                                                "_licenses/NOTICE-E07.md"))
        metadata = validate_metadata(installed, root, metadata_files=metadata_files)
        validate_seed_policy(root)
        numeric = load(root / "references/e04-numeric-regressions.json")
        no_full_acceptance(numeric)
        validate_numeric(numeric)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError, zipfile.BadZipFile) as error:
        errors.append(str(error))
    return {"schema": "py-elk-e07-runtime-validation/v1", "status": "FAIL" if errors else "E07_RUNTIME_EVIDENCE_VALIDATED",
            "errors": errors, "currentPackageBytesValidated": not errors and not historical,
            "currentDistributionMetadataValidated": not errors and not historical,
            "historicalPackageBytesValidated": not errors and historical,
            "historicalDistributionMetadataValidated": not errors and historical,
            "installedEvidenceValidated": not errors, "runtimeReexecuted": False,
            "historicalWheelAuthenticated": False, "mathematicalEquivalenceAutomaticallyProved": False,
            "pythonAlgorithmsVerified": 0, "sourceValidation": sources, "distributionMetadata": metadata,
            "limitation": "Offline consistency of E07 recorded execution claims and current Python/license/metadata bytes. Receipts do not authenticate execution or wheel hashes, rerun installed layout, or prove equivalence. Earlier archives cannot certify current code. Fresh E07 installed verification is a separate command."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--historical", action="store_true", help="Audit pinned E07 bytes without certifying current E08 sources")
    args = parser.parse_args()
    result = check(historical=args.historical)
    if args.out:
        write(args.out, result)
    print(json.dumps(result, indent=2))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
