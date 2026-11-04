"""Validate explicitly selected E06 bytes without executing a historical package.

E04/E05 historical archives cannot certify the current E06 package. This audit
checks the bounded source approvals, all52 requests, current Python/license
bytes and the recorded distribution METADATA. Fresh execution is a separate
installed-candidate check; these receipts do not prove mathematical equivalence.
The explicit --historical branch pins E06's own archive and declarations and
cannot certify newer current sources or metadata.
"""
from __future__ import annotations

import argparse
import base64
from email.parser import BytesParser
from email.policy import default as email_policy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tomllib
import zipfile

from layout_checks import ROOT, contained, load, sha256, write
from validate_e04_runtime import (
    BASELINE, CLAIMS, digest, exact, no_full_acceptance, require, suite_requests,
    validate_claims, validate_installed, validate_numeric, validate_seed_policy,
    historical_material as _historical_material,
)
from validate_e06_source_bindings import check as check_sources

AUDIT = "references/e06-runtime-audit.json"
INSTALLED = "references/e06-installed-check.json"
SCOPE = "docs/decisions/0005-e06-multigraph.md"
SCOPE_ID = "E06-ADR0005-revision1"
SUITE = "tests/fixtures/suites/E06/cases.json"
SELECTION = "tests/fixtures/suites/E06/selection.json"
APPROVALS = "references/e06-component-approvals.json"
DENOMINATORS = {"algorithms": 12, "options": 243, "categories": 8, "masterCases": 25,
                "selectedMasterCases": 15, "excludedMasterCases": 10,
                "projectVariants": 37, "sliceCases": 52}
SCOPE_VALUE = {"id": SCOPE_ID, "document": SCOPE,
               "topology": "flat-connected-directed-multigraph",
               "minimumNodes": 0, "maximumNodes": 8, "maximumEdges": 28,
               "maximumInternalNodes": 176, "maximumInternalSegments": 196,
               "maximumInternalPorts": 392, "maximumRoutingSegmentsPerBoundary": 56,
               "directions": ["RIGHT", "UNDEFINED"], "edgeRouting": "ORTHOGONAL",
               "numericMaximum": 1_000_000, "nonzeroSigned32Seed": True,
               "explicitPaddingType": "string", "renewSourceApprovalBeforeExpansion": True}
REQUIRED_FILES = {INSTALLED, SCOPE, SUITE, SELECTION, APPROVALS,
                  "references/e04-determinism-policy.json", "references/e04-numeric-regressions.json"}
HISTORICAL_WHEEL = "references/history/E06/py_elk-0.0.1a0-py3-none-any.whl"
HISTORICAL_WHEEL_SHA = "83861c32ededc634e511a2ff9c0b197208ead612df1782697c3d96dee7e4eff1"
HISTORICAL_DECLARATIONS = {
    "UPSTREAM.json": "1854d270b537c343b787d44f3fe14cb2f552a095e995ed0e1e353da2aa42ec5c",
    "docs/compatibility.json": "4c4bc05852a0606db8fc6350bb4b2f7a42dbe254d16aab45dc0d36617d01c976",
}
HISTORICAL_METADATA = {
    "pyproject.toml": "37dc8e7ede705a877855dae15152620cfd9a8506103be87f32f3a38a4eb2fe34",
    "README.md": "099f8bd80fbf029b4773420e13240ea52fc6042a5aaf62dc011fe1d6992151c8",
}


def historical_material(root):
    return _historical_material(Path(root), iteration="E06",
                                material_path="references/history/E06/material.json",
                                wheel_path=HISTORICAL_WHEEL, wheel_sha=HISTORICAL_WHEEL_SHA,
                                declarations_sha=HISTORICAL_DECLARATIONS)


def historical_metadata(root, summary):
    material = load(Path(root) / "references/history/E06/metadata-material.json")
    require(material["schema"] == "py-elk-e06-historical-metadata-material/v1", "Historical metadata schema differs")
    require(set(material["files"]) == set(HISTORICAL_METADATA), "Historical metadata denominator differs")
    files = {}
    for name, fingerprint in HISTORICAL_METADATA.items():
        row = material["files"][name]
        raw = base64.b64decode(row["bytesBase64"], validate=True)
        require(row["sha256"] == fingerprint == hashlib.sha256(raw).hexdigest(),
                "Historical metadata material differs: " + name)
        files[name] = raw
    # A historical receipt must describe the actual pinned archive member.
    # Parsing a self-consistent, unrelated METADATA receipt is insufficient.
    with zipfile.ZipFile(Path(root) / HISTORICAL_WHEEL) as archive:
        names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        require(len(names) == 1, "Historical METADATA member denominator differs")
        receipt = summary["distributionMetadata"]
        raw = archive.read(names[0])
        require(receipt == {"archivePath": names[0], "sha256": hashlib.sha256(raw).hexdigest(),
                            "bytesBase64": base64.b64encode(raw).decode("ascii")},
                "Historical METADATA receipt differs from pinned archive")
    return files


def requests(root):
    return suite_requests(root, suite_path=SUITE, selection_path=SELECTION,
                          selected_count=15, excluded_count=10, variant_count=37, case_count=52)


def _no_static_proof_promotion(value):
    if type(value) is dict:
        for key, child in value.items():
            if key in {"mathematicalEquivalenceAutomaticallyProved", "runtimeReexecuted",
                       "historicalWheelAuthenticated", "historicalExecutionAuthenticated"}:
                exact(child, False, "Static audit cannot authenticate or prove: " + key)
            _no_static_proof_promotion(child)
    elif type(value) is list:
        for child in value:
            _no_static_proof_promotion(child)


def _normalized_name(value):
    require(type(value) is str and bool(value), "Missing distribution name")
    return re.sub(r"[-_.]+", "-", value).lower()


def _requirement_key(value):
    """Normalize the declared E06 simple dependency/extra form, not evaluate it."""
    require(type(value) is str and bool(value), "Invalid distribution requirement")
    match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9_.-]*)(.*)", value.strip())
    require(match is not None, "Unsupported distribution requirement")
    suffix = re.sub(r"\s+", "", match[2]).replace("'", '"')
    # Core metadata may surround a version-specifier list with parentheses.
    if suffix.startswith("("):
        closing = suffix.find(")")
        require(closing > 0, "Invalid distribution version specifier")
        suffix = suffix[1:closing] + suffix[closing + 1:]
    return _normalized_name(match[1]) + suffix


def validate_metadata(summary, root=ROOT, *, metadata_files=None):
    """Check embedded actual METADATA against current pyproject/README.

    This pure filesystem/read-only function is also usable by the actual-run
    exporter before audit/UPSTREAM receipts exist. It returns a diagnostic dict
    and raises ValueError for an invalid or unrelated metadata receipt.
    """
    root = Path(root)
    receipt = summary["distributionMetadata"]
    require(type(receipt) is dict and set(receipt) == {"archivePath", "sha256", "bytesBase64"},
            "Distribution METADATA receipt fields differ")
    archive_path = receipt["archivePath"]
    require(type(archive_path) is str and "\\" not in archive_path, "Invalid METADATA archive path")
    parts = PurePosixPath(archive_path).parts
    require(len(parts) == 2 and parts[1] == "METADATA" and parts[0].endswith(".dist-info")
            and not any(part in ("", ".", "..") for part in archive_path.split("/")),
            "Invalid METADATA archive member")
    digest(receipt["sha256"])
    require(type(receipt["bytesBase64"]) is str, "Invalid METADATA byte encoding")
    raw = base64.b64decode(receipt["bytesBase64"], validate=True)
    require(hashlib.sha256(raw).hexdigest() == receipt["sha256"], "Distribution METADATA bytes differ")
    metadata = BytesParser(policy=email_policy).parsebytes(raw)
    require(not metadata.defects, "Malformed distribution METADATA")
    project_raw = ((root / "pyproject.toml").read_bytes() if metadata_files is None else metadata_files["pyproject.toml"])
    project = tomllib.loads(project_raw.decode("utf-8"))["project"]
    for name in ("Metadata-Version", "Name", "Version", "Requires-Python", "Summary"):
        require(len(metadata.get_all(name, [])) == 1, "Missing or duplicate METADATA field: " + name)
    require(_normalized_name(str(metadata["Name"])) == _normalized_name(project["name"]) == "py-elk",
            "Distribution METADATA name differs")
    require(metadata["Version"] == project["version"] == summary["wheelVersion"],
            "Distribution METADATA version differs")
    require(parts[0] == "py_elk-" + project["version"] + ".dist-info", "METADATA distribution directory differs")
    require(metadata["Requires-Python"] == project["requires-python"], "Distribution Requires-Python differs")
    require(metadata["Summary"] == project["description"], "Distribution summary differs")
    dependencies = project.get("dependencies", [])
    optional = project.get("optional-dependencies", {})
    require(type(dependencies) is list and type(optional) is dict, "Invalid declared distribution dependencies")
    expected = [_requirement_key(value) for value in dependencies]
    for extra, values in optional.items():
        require(type(extra) is str and type(values) is list, "Invalid declared distribution extra")
        for value in values:
            # The pinned E06 dev requirements contain simple exact pins. Do
            # not silently invent a general PEP508 marker transformation.
            require(type(value) is str and ";" not in value, "Unsupported optional dependency marker")
            expected.append(_requirement_key(value + '; extra == "' + _normalized_name(extra) + '"'))
    actual = [_requirement_key(str(value)) for value in metadata.get_all("Requires-Dist", [])]
    require(len(actual) == len(set(actual)) and sorted(actual) == sorted(expected),
            "Distribution Requires-Dist differs")
    extras = [_normalized_name(str(value)) for value in metadata.get_all("Provides-Extra", [])]
    require(len(extras) == len(set(extras)) and set(extras) == {_normalized_name(value) for value in optional},
            "Distribution optional extras differ")
    require(sorted(str(value) for value in metadata.get_all("Classifier", [])) == sorted(project.get("classifiers", [])),
            "Distribution development classifiers differ")
    readme = project["readme"]
    require(type(readme) is str, "E06 package requires its declared README file")
    readme_path = contained(root, readme)
    readme_raw = readme_path.read_bytes() if metadata_files is None else metadata_files[readme]
    require(metadata["Description-Content-Type"] == "text/markdown", "Distribution description type differs")
    payload = metadata.get_payload(decode=True)
    # Email transport serializes lines with CRLF. Keep the raw receipt SHA and
    # original README SHA; only this explicit transport normalization applies.
    # Content, lone CR, whitespace and terminal newlines are never stripped.
    require(payload.replace(b"\r\n", b"\n") == readme_raw.replace(b"\r\n", b"\n"),
            "Distribution README bytes differ")
    return {"status": "E06_DISTRIBUTION_METADATA_VALIDATED", "archivePath": archive_path,
            "sha256": receipt["sha256"], "name": "py-elk", "version": project["version"],
            "readmeSha256": hashlib.sha256(readme_raw).hexdigest(), "normalization": "email CRLF to LF only",
            "historicalExecutionAuthenticated": False}


def check(root=ROOT, *, historical=False):
    root = Path(root)
    errors, sources, metadata = [], None, None
    try:
        audit = load(root / AUDIT)
        require(audit["schema"] == "py-elk-e06-runtime-audit/v1" and audit["iteration"] == "E06"
                and audit["status"] == "E06_EXPERIMENTAL_SLICE_VERIFIED", "E06 audit identity/status differs")
        exact(audit["baseline"], BASELINE, "E06 baseline differs")
        exact(audit["scope"], SCOPE_VALUE, "E06 bounded scope differs")
        exact(audit["runtimeClaims"], CLAIMS, "E06 runtime claims differ")
        exact(audit["coverageDenominators"], DENOMINATORS, "E06 denominator differs")
        exact(audit["pythonAlgorithmsVerified"], 0, "Full algorithm count must remain zero")
        exact(audit["availableExperimentalAlgorithms"], ["org.eclipse.elk.layered"], "Experimental algorithm differs")
        require(audit["installedEvidence"] == INSTALLED and audit["algorithmSourceGate"] ==
                "verified-for-guarded-generated-source-slice-only", "E06 source/evidence category differs")
        require(set(audit["filesSha256"]) == REQUIRED_FILES, "E06 evidence file denominator differs")
        for path, fingerprint in audit["filesSha256"].items():
            digest(fingerprint)
            require(sha256(contained(root, path)) == fingerprint, "Versioned E06 evidence SHA differs: " + path)
        no_full_acceptance(audit)
        _no_static_proof_promotion(audit)
        sources = check_sources(root, require_approved=True)
        require(not sources["errors"] and sources["wholeSourceApproved"],
                "E06 source gate is incomplete: " + str(sources["errors"]))
        exact(sources["componentCounts"], {"A": 8, "B": 4, "R": 15}, "E06 source component denominator differs")
        exact(sources["approvedEvidence"]["approvedComponents"], 27, "E06 source approval denominator differs")
        package_bytes, metadata_files = None, None
        if historical:
            declarations, package_bytes = historical_material(root)
            lock, ledger = declarations["UPSTREAM.json"], declarations["docs/compatibility.json"]
        else:
            lock, ledger = load(root / "UPSTREAM.json"), load(root / "docs/compatibility.json")
        validate_claims(lock, ledger, sha256(root / AUDIT), root,
                        audit_path=AUDIT, scope_id=SCOPE_ID, case_count=52)
        installed = load(root / INSTALLED)
        if historical:
            require(installed["wheelSha256"] == HISTORICAL_WHEEL_SHA, "Historical installed wheel receipt differs")
            metadata_files = historical_metadata(root, installed)
        _no_static_proof_promotion(installed)
        require(installed["wheelVersion"] == lock["python"]["scaffoldVersion"], "Installed wheel/declaration version differs")
        validate_installed(installed, requests(root), root, package_bytes=package_bytes, iteration="E06", suite_path=SUITE,
                           case_count=52, builder="scripts/build_e06_suite.py",
                           additional_licenses=("_licenses/NOTICE-E05.md", "_licenses/NOTICE-E06.md"))
        metadata = validate_metadata(installed, root, metadata_files=metadata_files)
        validate_seed_policy(root)
        numeric = load(root / "references/e04-numeric-regressions.json")
        no_full_acceptance(numeric)
        validate_numeric(numeric)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, IndexError, UnicodeError, zipfile.BadZipFile) as error:
        errors.append(str(error))
    return {"schema": "py-elk-e06-runtime-validation/v1", "status": "FAIL" if errors else "E06_RUNTIME_EVIDENCE_VALIDATED",
            "errors": errors, "currentPackageBytesValidated": not errors and not historical,
            "currentDistributionMetadataValidated": not errors and not historical,
            "historicalPackageBytesValidated": not errors and historical,
            "historicalDistributionMetadataValidated": not errors and historical,
            "installedEvidenceValidated": not errors, "runtimeReexecuted": False,
            "historicalWheelAuthenticated": False, "mathematicalEquivalenceAutomaticallyProved": False,
            "pythonAlgorithmsVerified": 0, "sourceValidation": sources, "distributionMetadata": metadata,
            "limitation": "Offline consistency of E06 recorded claims and explicitly selected package/metadata bytes. Historical mode checks the pinned E06 archive and frozen declarations, never certifies newer current code and never executes the old package. Receipts do not authenticate execution, rerun layout or prove equivalence; fresh installed verification is separate."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--historical", action="store_true", help="Audit frozen E06 bytes; never certify current sources")
    args = parser.parse_args()
    result = check(historical=args.historical)
    if args.out:
        write(args.out, result)
    print(json.dumps(result, indent=2))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
