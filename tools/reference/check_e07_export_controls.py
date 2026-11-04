"""Offline controls of a real E07 installed receipt, using private copies only.

No engine, phase protocol, installation or historical wheel is executed. The
genuine original and copied run must pass before any isolated negative control.
These checks reject inconsistent receipts; they cannot authenticate an entirely
forged execution chain or prove layout/API/lifecycle/release equivalence.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import load, sha256
from export_e05_installed_evidence import export


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf8")


def save_new(path, value):
    Path(path).open("xb").write(encoded(value))


def inventory(directory):
    return {p.relative_to(directory).as_posix(): sha256(p) for p in sorted(directory.rglob("*")) if p.is_file()}


def check(installed_run, out):
    installed_run, out = Path(installed_run).resolve(), Path(out).resolve()
    if not installed_run.is_relative_to(ROOT) or not out.is_relative_to(ROOT):
        raise ValueError("Original run and NEW output must be inside the current checkout")
    if out.is_relative_to(installed_run) or installed_run.is_relative_to(out) or out.exists():
        raise ValueError("Output must be NEW and outside the original capture")
    sources = {p.relative_to(ROOT).as_posix(): sha256(p) for p in (
        Path(__file__), ROOT / "scripts/export_e05_installed_evidence.py",
        ROOT / "scripts/export_e07_installed_evidence.py", ROOT / "scripts/layout_checks.py",
        ROOT / "scripts/e07_geometry_premise.py", ROOT / "scripts/validate_e04_runtime.py",
        ROOT / "scripts/validate_e06_runtime.py", ROOT / "scripts/validate_e07_runtime.py",
        ROOT / "pyproject.toml", ROOT / "README.md")}
    package = ROOT / "src/pyelk"
    sources.update({p.relative_to(ROOT).as_posix(): sha256(p) for p in package.rglob("*")
                    if p.is_file() and (p.suffix == ".py" or "_licenses" in p.parts) and "__pycache__" not in p.parts})
    original = inventory(installed_run)
    out.mkdir(parents=True, exist_ok=False)
    report = {"schema": "py-elk-e07-export-controls/v1", "status": "RUNNING",
              "installedRun": installed_run.relative_to(ROOT).as_posix(), "inputFilesSha256": original,
              "sourceFilesSha256": sources, "runtimeReexecuted": False, "installationReexecuted": False,
              "engineLaunched": False, "phaseProtocolAssessed": False, "pythonAlgorithmsVerified": 0,
              "fullAlgorithmAccepted": False, "packagePublished": False,
              "limitation": "Offline self-consistency and current package/METADATA binding only. Entirely forged historical execution cannot be authenticated; no engine/API/lifecycle/release acceptance."}
    installed = lambda path: export(path, iteration="E07")
    try:
        with patch("subprocess.Popen", side_effect=AssertionError("Export controls cannot launch engines or installers")):
            actual = installed(installed_run)
            with tempfile.TemporaryDirectory(prefix="isolated-copies-", dir=out) as temporary:
                temporary = Path(temporary).resolve()
                if not temporary.is_relative_to(out):
                    raise ValueError("Temporary cleanup target escaped explicit output")
                copied = temporary / "installed"
                shutil.copytree(installed_run, copied)
                duplicate = installed(copied)
                if (actual["wheelSha256"], actual["caseCount"], actual["repeat"], actual["packageFilesSha256"], actual["distributionMetadata"]) != (
                        duplicate["wheelSha256"], duplicate["caseCount"], duplicate["repeat"], duplicate["packageFilesSha256"], duplicate["distributionMetadata"]):
                    raise ValueError("Copied positive changed actual wheel/case/repeat/package/METADATA identity")
                report["positiveControls"] = {"original": True, "copied": True, "caseCount": actual["caseCount"],
                                               "repeat": actual["repeat"], "wheelSha256": actual["wheelSha256"],
                                               "packageFiles": len(actual["packageFilesSha256"]),
                                               "metadataSha256": actual["distributionMetadata"]["sha256"]}
                baseline = {name: (copied / name).read_bytes() for name in original}
                changed = set()

                def replace(name, value):
                    (copied / name).write_bytes(encoded(value)); changed.add(name)

                def edit_json(name, mutate):
                    value = json.loads(baseline[name]); mutate(value); replace(name, value)

                def restore():
                    for name in changed: (copied / name).write_bytes(baseline[name])
                    changed.clear()

                def negative(name, mutate, *, category):
                    restore(); mutate()
                    artifacts = {p: sha256(copied / p) for p in sorted(changed)}
                    try:
                        installed(copied)
                    except (ValueError, KeyError, TypeError, IndexError, OSError, AssertionError) as error:
                        return {"name": name, "category": category, "rejected": True,
                                "errorType": type(error).__name__, "reason": str(error), "mutatedFilesSha256": artifacts}
                    failed = out / ("unexpected-acceptance-" + name); failed.mkdir(exist_ok=False)
                    for relative in changed:
                        path = failed / relative; path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes((copied / relative).read_bytes())
                    raise AssertionError("Exporter accepted isolated wrong input: " + name)

                controls = []
                edits = [
                    ("empty-candidate-geometry", lambda d: d["cases"][0].update(geometry=[])),
                    ("empty-reference-geometry", lambda d: d["cases"][0].update(referenceGeometry=[])),
                    ("empty-input-preservation", lambda d: d["cases"][0].update(candidateInputPreservation=[])),
                    ("failed-selected-profile-row", lambda d: d["cases"][0]["comparison"][0].update(passed=False)),
                    ("wrong-selected-profile-row", lambda d: d["cases"][0]["comparison"][0].update(profile="strict")),
                    ("wrong-reference-index-sha", lambda d: d.update(referenceIndexSha256="0" * 64)),
                    ("wrong-candidate-index-sha", lambda d: d.update(candidateIndexSha256="0" * 64)),
                    ("partial-determinism-comparison", lambda d: d["cases"][0]["candidateDeterminism"].update(comparisons=[])),
                ]
                for name, edit in edits:
                    controls.append(negative(name, lambda edit=edit: edit_json("comparison.json", edit), category="recomputed-comparison"))
                for name, role, edit in (
                    ("wrong-candidate-capture-role", "candidate", lambda d: d.update(role="reference")),
                    ("wrong-reference-capture-role", "reference", lambda d: d.update(role="candidate")),
                    ("boolean-repeat", "candidate", lambda d: d.update(repeat=True)),
                    ("partial-raw-membership", "reference", lambda d: d["cases"].pop()),
                ):
                    controls.append(negative(name, lambda role=role, edit=edit: edit_json(role + "/index.json", edit), category="capture-role-denominator"))

                def command(role, mutate):
                    value = json.loads(baseline["report.json"])
                    row = next(row for row in value["commands"] if row["name"] == role); mutate(row)
                    replace("report.json", value)
                    replace(role + "-command/command.json", {k: v for k, v in row.items() if k not in ("name", "environmentPolicy")})

                command_edits = (
                    ("wrong-source-approval-role", "source-approval", lambda row: row["argv"].__setitem__(1, "scripts/validate_e06_source_bindings.py")),
                    ("wrong-source-approval-interpreter", "source-approval", lambda row: row["argv"].__setitem__(0, "C:/other/python.exe")),
                    ("candidate-environment-not-isolated", "candidate", lambda row: row.update(environmentPolicy="inherited")),
                    ("installed-interpreter-without-I", "installed-wheel", lambda row: row["argv"].remove("-I")),
                    ("candidate-wrong-repeat", "candidate", lambda row: row["argv"].__setitem__(row["argv"].index("--repeat") + 1, "2")),
                    ("candidate-wrong-adapter", "candidate", lambda row: row["argv"].__setitem__(row["argv"].index("--command-json") + 1, "other-candidate-command.json")),
                    ("compare-wrong-profile", "compare", lambda row: row["argv"].__setitem__(row["argv"].index("--profile") + 1, "strict")),
                )
                for name, role, edit in command_edits:
                    controls.append(negative(name, lambda role=role, edit=edit: command(role, edit), category="rebound-command-role"))

                def log_change():
                    path = "candidate-command/stdout.log"
                    (copied / path).write_bytes(baseline[path] + b"\ncontrol mutation\n"); changed.add(path)

                controls.append(negative("command-log-byte-mismatch", log_change, category="raw-command-log"))

                def metadata(edit, *, path=None, missing=False):
                    value = json.loads(baseline["installed-wheel.json"])
                    if missing:
                        value.pop("distributionMetadata")
                    else:
                        receipt = value["distributionMetadata"]
                        if path is not None: receipt["archivePath"] = path
                        raw = base64.b64decode(receipt["bytesBase64"], validate=True); raw = edit(raw)
                        receipt.update(bytesBase64=base64.b64encode(raw).decode("ascii"), sha256=hashlib.sha256(raw).hexdigest())
                    replace("installed-wheel.json", value)

                for name, edit, kwargs in (
                    ("metadata-name-rebound-sha", lambda raw: raw.replace(b"Name: py-elk", b"Name: wrong-distribution", 1), {}),
                    ("metadata-readme-rebound-sha", lambda raw: raw + b"modified README content\r\n", {}),
                    ("metadata-unsafe-archive-member", lambda raw: raw, {"path": "../METADATA"}),
                    ("metadata-missing-receipt", lambda raw: raw, {"missing": True}),
                ):
                    controls.append(negative(name, lambda edit=edit, kwargs=kwargs: metadata(edit, **kwargs), category="actual-current-METADATA"))
                for name, edit in (
                    ("missing-direction-module-identity", lambda d: d["packageFilesSha256"].pop("algorithms/layered/directions.py")),
                    ("wrong-current-module-identity", lambda d: d["packageFilesSha256"].__setitem__("algorithms/layered/components.py", "0" * 64)),
                    ("missing-e07-notice-identity", lambda d: d["packageFilesSha256"].pop("_licenses/NOTICE-E07.md")),
                    ("invented-package-file-identity", lambda d: d["packageFilesSha256"].__setitem__("invented.py", "0" * 64)),
                ):
                    controls.append(negative(name, lambda edit=edit: edit_json("installed-wheel.json", edit), category="complete-current-package-identities"))

                def raw_observation(role, edit):
                    index_name = role + "/index.json"; index = json.loads(baseline[index_name])
                    case = next(row for row in index["cases"] if load(copied / role / row["request"])["graph"].get("edges"))
                    relative = case["observations"][0]; name = role + "/" + relative
                    observed = json.loads(baseline[name]); edit(observed); replace(name, observed)
                    index["files"][relative] = sha256(copied / name); replace(index_name, index)

                for name, role, edit in (
                    ("raw-candidate-wrong-engine", "candidate", lambda d: d["engine"].update(name="elkjs")),
                    ("raw-reference-wrong-entrypoint", "reference", lambda d: d["engine"].update(entrypointSha256="0" * 64)),
                    ("raw-candidate-wrong-request", "candidate", lambda d: d.update(requestSha256="0" * 64)),
                    ("raw-candidate-mutated-input", "candidate", lambda d: d["inputAfter"].update(__control_mutation__=True)),
                    ("raw-candidate-mutated-result", "candidate", lambda d: d["result"].update(width=-1)),
                ):
                    controls.append(negative(name, lambda role=role, edit=edit: raw_observation(role, edit), category="rebound-raw-observation-sha"))
                restore()
                installed(copied)
                report["copiedPositiveAfterControls"] = True
                report["installedNegativeControls"] = controls
                report["negativeControlsRejected"] = len(controls)
        if inventory(installed_run) != original or any(sha256(ROOT / path) != fingerprint for path, fingerprint in sources.items()):
            raise ValueError("Original capture/source bytes changed during controls")
        report["originalInputsAndSourcesUnchanged"] = True
        report["status"] = "E07_EXPORT_CONTROLS_PASS"
    except Exception as error:
        report["status"] = "FAIL"; report["error"] = {"type": type(error).__name__, "message": str(error)}
    save_new(out / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-run", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = check(args.installed_run, args.out)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({"status": result["status"], "negativeControlsRejected": result.get("negativeControlsRejected", 0),
                      "runtimeReexecuted": False, "engineLaunched": False}))
    return int(result["status"] != "E07_EXPORT_CONTROLS_PASS")


if __name__ == "__main__":
    raise SystemExit(main())
