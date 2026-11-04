"""Replay E05 exporter guard controls using real, already captured inputs.

This development tool reads a completed installed check and a nonempty E05
three-engine phase trace. It verifies genuine positives, copies their files
into a NEW output directory, and tests isolated wrong metadata/raw captures.
It never runs layout, launches an engine, installs a wheel or changes sources.
Run from any checkout path; no historical test-runs directory is hardcoded.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import load, sha256
import export_e05_installed_evidence as installed_export
import export_e05_phase_observations as phase_export


def describe(path):
    path = Path(path).resolve()
    return {"path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
            "sha256": sha256(path)}


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def replace_copy(path, value):
    """Only call for the private temporary copy inside the new output folder."""
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                          encoding="utf-8", newline="\n")


def rejected(name, action):
    try:
        action()
    except (ValueError, KeyError, TypeError, IndexError, OSError, AssertionError) as error:
        return {"name": name, "rejected": True, "errorType": type(error).__name__, "reason": str(error)}
    raise AssertionError("Exporter accepted the isolated wrong input: " + name)


def check(installed_run, phase_capture, phase_request, out, *, iteration="E05"):
    if iteration not in ("E05", "E06"):
        raise ValueError("Unknown export controls iteration")
    installed = lambda path: installed_export.export(path, iteration=iteration)
    phases = lambda capture, request, stage: phase_export.export(capture, request, stage, iteration=iteration)
    installed_run, phase_capture, phase_request = map(lambda p: Path(p).resolve(),
                                                      (installed_run, phase_capture, phase_request))
    out = Path(out).resolve()
    # The installed exporter stores a repository-relative run identity. Keeping
    # every temporary write under the explicit new output also makes cleanup
    # targets verifiable on Windows.
    if not installed_run.is_relative_to(ROOT) or not out.is_relative_to(ROOT):
        raise ValueError("--installed-run and --out must be inside the current checkout")
    if out.is_relative_to(installed_run) or out.is_relative_to(phase_capture):
        raise ValueError("--out must be outside both original capture directories")
    if out.exists():
        raise ValueError("--out must be a NEW directory")
    installed_files = ("report.json", "comparison.json", "installed-wheel.json",
                       "reference/index.json", "candidate/index.json")
    phase_files = ("summary.json", "bundled.json", "pretty.json", "instrumented.json")
    original_paths = [installed_run / name for name in installed_files]
    original_paths += [phase_capture / name for name in phase_files]
    original_paths += [phase_request]
    source_paths = [Path(__file__), ROOT / "scripts/export_e05_installed_evidence.py",
                    ROOT / "scripts/export_e05_phase_observations.py",
                    ROOT / "scripts/validate_e04_runtime.py", ROOT / "scripts/layout_checks.py"]
    inputs = [describe(path) for path in original_paths]
    sources = [describe(path) for path in source_paths]
    out.mkdir(parents=True, exist_ok=False)
    report = {"schema": "py-elk-" + iteration.lower() + "-export-controls/v1", "status": "RUNNING",
              "inputs": inputs, "sourceFiles": sources,
              "runtimeReexecuted": False, "installationReexecuted": False,
              "engineLaunched": False, "pythonAlgorithmsVerified": 0,
              "fullAlgorithmAccepted": False, "packagePublished": False,
              "limitation": "Offline exporter/receipt self-consistency controls only. They cannot authenticate an entirely forged historical chain or prove mathematical equivalence/layout/API/lifecycle/release acceptance."}
    try:
        with patch("subprocess.Popen", side_effect=AssertionError("Export controls must not run engines or installers")):
            actual = installed(installed_run)
            trace = load(phase_capture / "instrumented.json")
            stage = "LayerSweepCrossingMinimizer"
            first_crossing = next((index for index, phase in enumerate(trace["phases"])
                                   if phase["name"].endswith("." + stage)), None)
            if first_crossing is None:
                raise ValueError("Use a nonempty E05 trace with the two default LayerSweep calls")
            actual_phases = phases(phase_capture, phase_request, stage)
            if len(actual_phases["calls"]) != 2:
                raise ValueError("The actual E05 positive must retain both LayerSweep strategies")
            report["positiveControls"] = {
                "installed": {"passed": True, "cases": actual["caseCount"], "repeat": actual["repeat"],
                              "wheelSha256": actual["wheelSha256"]},
                "phase": {"passed": True, "stage": stage, "calls": len(actual_phases["calls"]),
                          "strategies": [call["strategy"] for call in actual_phases["calls"]]},
                "classification": "Real original captures revalidated offline; no new execution or installation."}
            with tempfile.TemporaryDirectory(prefix="isolated-copies-", dir=out) as directory:
                temporary = Path(directory).resolve()
                if not temporary.is_relative_to(out):
                    raise ValueError("Temporary cleanup target escaped the explicit output directory")
                copied_run, copied_trace = temporary / "installed", temporary / "phase"
                shutil.copytree(installed_run, copied_run)
                shutil.copytree(phase_capture, copied_trace)
                # Normal copied inputs must pass before any negative control.
                installed(copied_run)
                phases(copied_trace, phase_request, stage)
                comparison = load(copied_run / "comparison.json")
                installed_edits = [
                    ("empty-candidate-geometry", lambda d: d["cases"][0].update(geometry=[])),
                    ("empty-reference-geometry", lambda d: d["cases"][0].update(referenceGeometry=[])),
                    ("empty-input-preservation", lambda d: d["cases"][0].update(candidateInputPreservation=[])),
                    ("failed-selected-profile-row", lambda d: d["cases"][0]["comparison"][0].update(passed=False)),
                    ("wrong-selected-profile-row", lambda d: d["cases"][0]["comparison"][0].update(profile="strict")),
                    ("wrong-reference-index-sha", lambda d: d.update(referenceIndexSha256="0" * 64)),
                    ("wrong-candidate-index-sha", lambda d: d.update(candidateIndexSha256="0" * 64)),
                    ("partial-determinism-comparison", lambda d: d["cases"][0]["candidateDeterminism"].update(comparisons=[])),
                ]
                installed_results = []
                for name, edit in installed_edits:
                    value = copy.deepcopy(comparison)
                    edit(value)
                    replace_copy(copied_run / "comparison.json", value)
                    installed_results.append(rejected(name, lambda: installed(copied_run)))
                replace_copy(copied_run / "comparison.json", comparison)
                index = load(copied_run / "candidate/index.json")
                index["role"] = "reference"
                replace_copy(copied_run / "candidate/index.json", index)
                installed_results.append(rejected("wrong-candidate-capture-role", lambda: installed(copied_run)))
                report["installedNegativeControls"] = installed_results

                originals = {name: load(copied_trace / name) for name in phase_files}
                phase_edits = [
                    ("bundle-result", "bundled.json", lambda d: d["result"].update(__export_control_mutant__=1)),
                    ("pretty-input", "pretty.json", lambda d: d["inputAfter"].update(__export_control_mutant__=1)),
                    ("trace-outcome", "instrumented.json", lambda d: d.update(outcome="threw")),
                    ("bundle-schema", "bundled.json", lambda d: d.update(schema="wrong")),
                    ("pretty-kind", "pretty.json", lambda d: d.update(kind="instrumented")),
                    ("trace-worker", "instrumented.json", lambda d: d.update(workerSha256="0" * 64)),
                    ("bundle-tool", "bundled.json", lambda d: d.update(toolSha256="0" * 64)),
                    ("trace-request", "instrumented.json", lambda d: d.update(requestSha256="0" * 64)),
                    ("trace-arguments", "instrumented.json", lambda d: d["actualLayoutArguments"].update(__export_control_mutant__=True)),
                    ("trace-strategy", "instrumented.json", lambda d: d["phases"][first_crossing].update(strategy="MEDIAN")),
                    ("summary-boolean-one", "summary.json", lambda d: d.update(prettyResultExactToBundled=1)),
                ]
                phase_results = []
                for name, filename, edit in phase_edits:
                    for key, value in originals.items():
                        replace_copy(copied_trace / key, value)
                    value = copy.deepcopy(originals[filename])
                    edit(value)
                    replace_copy(copied_trace / filename, value)
                    phase_results.append(rejected(name, lambda: phases(copied_trace, phase_request, stage)))
                report["phaseNegativeControls"] = phase_results
        for path, expected in zip(original_paths + source_paths, inputs + sources):
            if describe(path) != expected:
                raise ValueError("Original input/source bytes changed during controls: " + str(path))
        report["originalInputsAndSourcesUnchanged"] = True
        report["negativeControlsRejected"] = len(report["installedNegativeControls"]) + len(report["phaseNegativeControls"])
        report["status"] = iteration + "_EXPORT_CONTROLS_PASS"
    except Exception as error:
        report["status"] = "FAIL"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    save_new(out / "report.json", report)
    return report


def main(*, iteration="E05"):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-run", required=True, type=Path, help="Real completed E05 check run inside this checkout")
    parser.add_argument("--phase-capture", required=True, type=Path, help="Actual nonempty trace_e05_dag output directory")
    parser.add_argument("--phase-request", required=True, type=Path, help="Original exact request bytes for the phase trace")
    parser.add_argument("--out", required=True, type=Path, help="NEW output directory inside this checkout")
    args = parser.parse_args()
    try:
        report = check(args.installed_run, args.phase_capture, args.phase_request, args.out, iteration=iteration)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({"status": report["status"], "negativeControlsRejected": report.get("negativeControlsRejected", 0),
                      "runtimeReexecuted": False, "installationReexecuted": False}))
    return 0 if report["status"] == iteration + "_EXPORT_CONTROLS_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
