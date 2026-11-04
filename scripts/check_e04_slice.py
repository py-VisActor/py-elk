"""Reproduce E04 with a real installed wheel, same-suite JS/Python and no backend PATH."""
import argparse
import os
from pathlib import Path
import sys

from layout_checks import ROOT, load, sha256, write
from validate_layout import run, source_hashes


def main(*, iteration="E04", builder="scripts/build_slice_suite.py", source_approval=None):
    if iteration not in ("E04", "E05", "E06", "E07"):
        raise ValueError("Unknown experimental iteration")
    parser = argparse.ArgumentParser(description="Verify a real installed " + iteration + " wheel against the same official suite")
    parser.add_argument("--candidate-python", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--package", type=Path, default=ROOT / ".local/npm-elkjs/package")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    minimum_repeat = 2 if iteration == "E04" else 3
    if args.repeat < minimum_repeat or not args.candidate_python.is_file() or not args.wheel.is_file():
        parser.error("Provide a real installed Python/wheel and at least " + str(minimum_repeat) + " repetitions")
    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(exist_ok=False)
    python = sys.executable
    candidate_python, wheel = str(args.candidate_python.resolve()), str(args.wheel.resolve())
    suite = ROOT / ("tests/fixtures/suites/" + iteration + "/cases.json")
    clean_environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME"):
        clean_environment.pop(name, None)
    clean_environment["PATH"] = ""
    steps = [
        ("suite", [python, builder, "check", "--suite", str(suite.parent)], False),
        ("installed-wheel", [candidate_python, "-I", str(ROOT / "scripts/verify_installed_wheel.py"), wheel,
                             "--out", str(out / "installed-wheel.json")], True),
        ("candidate-command", [python, "scripts/validate_layout.py", "candidate-command", "--python", candidate_python,
                               "--out", str(out / "candidate-command.json")], False),
        ("reference", [python, "scripts/validate_layout.py", "reference", "--cases", str(suite), "--package", str(args.package.resolve()),
                       "--repeat", str(args.repeat), "--out", str(out / "reference")], False),
        ("candidate", [python, "scripts/validate_layout.py", "candidate", "--cases", str(suite),
                       "--command-json", str(out / "candidate-command.json"), "--repeat", str(args.repeat),
                       "--out", str(out / "candidate")], True),
        ("compare", [python, "scripts/validate_layout.py", "compare", "--profile", "native-basic-layered-v1",
                     "--determinism-policy", "elkjs-0.12.1-default-seed-v1",
                     "--reference", str(out / "reference"), "--candidate", str(out / "candidate"),
                     "--out", str(out / "comparison.json")], False),
    ]
    if source_approval is not None:
        steps.insert(1, ("source-approval", [python, source_approval, "--require-approved"], False))
    records = []
    for name, command, no_backends in steps:
        directory = out / (name + "-command")
        directory.mkdir()
        print("Checking " + iteration + " " + name, flush=True)
        record = run(command, directory, 300, env=clean_environment if no_backends else None)
        records.append({"name": name, "environmentPolicy": "EMPTY_PATH_NO_PYTHON_OVERRIDES" if no_backends else "inherited", **record})
        if record["exitCode"] != 0:
            print((directory / "stderr.log").read_text(encoding="utf-8", errors="replace")[-4000:], flush=True)
            break
    passed = len(records) == len(steps) and all(record["exitCode"] == 0 for record in records)
    comparison = load(out / "comparison.json") if (out / "comparison.json").is_file() else None
    installed = load(out / "installed-wheel.json") if (out / "installed-wheel.json").is_file() else None
    if installed and (Path(installed["modulePath"]).resolve().is_relative_to(ROOT / "src") or not installed["isolatedInterpreter"]):
        passed = False
    if installed:
        # A passing old wheel must not certify newly edited repository code.
        source_package = ROOT / "src/pyelk"
        expected_python = {path.relative_to(source_package).as_posix() for path in source_package.rglob("*.py")
                           if "__pycache__" not in path.parts}
        installed_python = {name for name in installed["packageFilesSha256"] if name.endswith(".py")}
        if expected_python != installed_python:
            passed = False
        source_licenses = {path.relative_to(source_package).as_posix() for path in (source_package / "_licenses").rglob("*")
                           if path.is_file() and "__pycache__" not in path.parts}
        if source_licenses != {name for name in installed["packageFilesSha256"] if name.startswith("_licenses/")}:
            passed = False
        for name, digest in installed["packageFilesSha256"].items():
            if name.endswith(".py") or name.startswith("_licenses/"):
                source_file = source_package / name
                if not source_file.is_file() or sha256(source_file) != digest:
                    passed = False
    if comparison and not comparison["passed"]:
        passed = False
    result = {"schema": "py-elk-" + iteration.lower() + "-installed-slice-check/v1",
              "status": iteration + "_INSTALLED_SLICE_PASS" if passed else "FAIL",
              "passed": passed, "commands": records, "sourceSha256": source_hashes(), "wheelSha256": sha256(args.wheel),
              "suiteSha256": sha256(suite), "sliceCasesVerified": comparison["caseCount"] if passed else 0,
              "pythonAlgorithmsVerified": 0, "fullAlgorithmAccepted": False, "packagePublished": False,
              "limitation": "Only the explicit " + iteration + " experimental slice; no full algorithm, public API/lifecycle or release acceptance."}
    write(out / "report.json", result)
    print(result["status"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
