"""Condense a successful, real check_e05_slice run into a NEW offline receipt.

Original raw observations, strict differences and command logs stay in the run.
This command cannot approve a failed run or substitute a source-tree execution.
"""
import argparse
from pathlib import Path

from layout_checks import ROOT, compare_captures, load, sha256, verify_capture, write
from validate_e04_runtime import exact, require, validate_installed
from validate_e05_runtime import SUITE, requests


def export(run, *, iteration="E05"):
    if iteration not in ("E05", "E06", "E07"):
        raise ValueError("Unknown installed evidence iteration")
    if iteration == "E07":
        from validate_e07_runtime import SUITE as suite, requests as suite_requests
        case_count = 72
    elif iteration == "E06":
        from validate_e06_runtime import SUITE as suite, requests as suite_requests
        case_count = 52
    else:
        suite, suite_requests, case_count = SUITE, requests, 36
    run = Path(run).resolve()
    report, comparison, installed = (load(run / name) for name in
                                     ("report.json", "comparison.json", "installed-wheel.json"))
    require(report["schema"] == "py-elk-" + iteration.lower() + "-installed-slice-check/v1" and report["passed"] is True
            and report["status"] == iteration + "_INSTALLED_SLICE_PASS", "A successful actual " + iteration + " run is required")
    require(comparison["passed"] is True and installed["isolatedInterpreter"] is True,
            "Comparison or installation did not pass")
    require(report["wheelSha256"] == installed["wheelSha256"] and report["suiteSha256"] == sha256(ROOT / suite),
            "Actual wheel or suite identity differs")
    for role in ("reference", "candidate"):
        index = verify_capture(run / role)
        require(index["role"] == role and index["suiteSha256"] == report["suiteSha256"]
                and type(index["repeat"]) is int and index["repeat"] >= 3 and len(index["cases"]) == case_count,
                "Actual capture membership/repeats differ")
    reproduced = compare_captures(run / "reference", run / "candidate", profile="native-basic-layered-v1",
                                  determinism_policy="elkjs-0.12.1-default-seed-v1")
    exact(comparison, reproduced, "Recorded comparison differs from recomputed raw observations")
    for command in report["commands"]:
        directory = run / (command["name"] + "-command")
        for stream in ("stdout", "stderr"):
            require(sha256(directory / (stream + ".log")) == command[stream + "Sha256"], "Actual command log SHA differs")
        exact(load(directory / "command.json"), {k: v for k, v in command.items()
                                                if k not in ("name", "environmentPolicy")}, "Actual command receipt differs")
    rows = []
    for case in comparison["cases"]:
        repeats = len(case["comparison"])
        for name in ("geometry", "referenceGeometry", "candidateInputPreservation", "referenceInputPreservation"):
            require(type(case[name]) is list and len(case[name]) == repeats, "Per-repetition evidence is missing: " + name)
        require(all(row["passed"] is True and row["profile"] == "native-basic-layered-v1" for row in case["comparison"]),
                "Per-repetition public comparison failed or changed profile")
        request_hashes = {row["requestSha256"] for row in case["comparison"]}
        require(len(request_hashes) == 1 and repeats >= 3, "Missing request identity or repetitions")
        rows.append({"id": case["id"], "passed": case["passed"], "requestSha256": request_hashes.pop(),
                     "repetitionsCompared": repeats,
                     "nativePublicExact": all(row["publicContract"]["exact"]["passed"] for row in case["comparison"]),
                     "nativePublicTolerance": all(row["publicContract"]["coordinateTolerance"]["passed"] for row in case["comparison"]),
                     "strictPassed": all(row["rawStrict"]["passed"] for row in case["comparison"]),
                     "candidateGeometry": all(row["passed"] for row in case["geometry"]),
                     "referenceGeometry": all(row["passed"] for row in case["referenceGeometry"]),
                     "candidateInputPreserved": all(row["preserved"] for row in case["candidateInputPreservation"]),
                     **{key: {name: case[key][name] for name in ("passed", "status", "repeats", "seed", "seedSource")}
                        for key in ("referenceDeterminism", "candidateDeterminism")}})
    require(len({row["repetitionsCompared"] for row in rows}) == 1, "Case repetition counts differ")
    original_names = ("report.json", "comparison.json", "installed-wheel.json", "reference/index.json", "candidate/index.json")
    value = {"schema": "py-elk-" + iteration.lower() + "-installed-evidence/v1", "iteration": iteration, "status": report["status"],
             "passed": report["passed"], "historicalEvidenceOnly": True, "runDirectory": run.relative_to(ROOT).as_posix(),
             "wheelSha256": report["wheelSha256"], "wheelVersion": installed["version"],
             "installedInterpreter": installed["python"], "isolatedInterpreter": installed["isolatedInterpreter"],
             "packageFilesSha256": installed["packageFilesSha256"], "suiteSha256": report["suiteSha256"],
             "profile": comparison["profile"], "determinismPolicy": comparison["determinismPolicy"],
             "tolerance": {"absolute": 1e-6, "relative": 1e-9, "appliesTo": "geometry numeric paths only"},
             "caseCount": comparison["caseCount"], "repeat": rows[0]["repetitionsCompared"],
             "commands": report["commands"], "sourceSha256AtExecution": report["sourceSha256"],
             "originalFilesSha256": {name: sha256(run / name) for name in original_names},
             "cases": rows, "pythonAlgorithmsVerified": 0, "fullAlgorithmAccepted": False, "packagePublished": False,
             "limitation": "Condensed actual installed-run receipt. Raw strict differences remain in the original run; this receipt alone does not authenticate historical execution or accept the full algorithm/API/release."}
    if iteration in ("E06", "E07"):
        value["distributionMetadata"] = installed["distributionMetadata"]
        from validate_e06_runtime import validate_metadata
        validate_metadata(value, ROOT)
    validate_installed(value, suite_requests(ROOT), ROOT, iteration=iteration, suite_path=suite,
                       case_count=case_count, builder="scripts/build_" + iteration.lower() + "_suite.py",
                       additional_licenses=("_licenses/NOTICE-E05.md",))
    return value


def main(*, iteration="E05"):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    value = export(args.run, iteration=iteration)
    write(args.out, value)
    print(iteration + "_INSTALLED_EVIDENCE_EXPORTED")


if __name__ == "__main__":
    main()
