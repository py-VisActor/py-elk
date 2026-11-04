"""Verify explicitly selected change checks; never launches a full test suite.

This post-execution audit is separate from immutable layout capture tools.
It retains original command/log bytes and reports fullValidation=False.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from change_impact import input_hashes
from layout_checks import load, sha256, write


def require(value, message):
    if not value:
        raise ValueError(message)


def verify_check(definition, root=ROOT):
    folder = Path(root) / definition["directory"]
    raw = (folder / "command.json").read_bytes()
    command = load(folder / "command.json")
    require(type(command["exitCode"]) is int and command["exitCode"] == 0,
            "Selected check failed: " + definition["id"])
    if "timedOut" in command:
        require(command["timedOut"] is False, "Selected check timed out: " + definition["id"])
    else:
        require(type(command.get("startedTimeNs")) is int and type(command.get("endedTimeNs")) is int and
                0 < command["startedTimeNs"] <= command["endedTimeNs"],
                "Completed check interval missing: " + definition["id"])
    require(command["argv"] == definition["argv"] and command["cwd"] == definition["cwd"],
            "Selected command identity differs: " + definition["id"])
    material = {"command": {"sha256": hashlib.sha256(raw).hexdigest(),
                            "bytesBase64": base64.b64encode(raw).decode()}}
    for stream in ("stdout", "stderr"):
        data = (folder / (stream + ".log")).read_bytes()
        require(hashlib.sha256(data).hexdigest() == command[stream + "Sha256"],
                "Original check log bytes differ: " + definition["id"])
        material[stream] = {"sha256": command[stream + "Sha256"], "bytesBase64": base64.b64encode(data).decode()}
    stderr = base64.b64decode(material["stderr"]["bytesBase64"]).decode("utf-8", errors="replace").replace("\r\n", "\n")
    matches = re.findall(r"^Ran (\d+) tests? in [\d.]+s$", stderr, re.MULTILINE)
    expected = definition["tests"]
    require(type(expected) is int and expected > 0 and len(matches) == 1 and int(matches[0]) == expected,
            "Actual targeted test denominator differs: " + definition["id"])
    require(re.search(r"^OK$", stderr, re.MULTILINE) is not None and "... skipped" not in stderr,
            "Targeted check did not finish without skips: " + definition["id"])
    return {"id": definition["id"], "tests": expected, "actualCommand": command,
            "timeoutFieldRecorded": "timedOut" in command,
            "originalMaterial": material}


def check(manifest_path, baseline_path, root=ROOT):
    root = Path(root); before = input_hashes(root)
    manifest, baseline = load(Path(manifest_path)), load(Path(baseline_path))
    old = baseline.get("worktreeFilesSha256", baseline.get("inputFilesSha256"))
    require(type(old) is dict and bool(old), "Complete starting input snapshot is required")
    definitions = manifest["checks"]
    require(type(definitions) is list and bool(definitions) and
            len({row["id"] for row in definitions}) == len(definitions), "Missing or duplicate change-check roles")
    receipts = [verify_check(row, root) for row in definitions]
    require(input_hashes(root) == before, "Inputs changed during change-check audit")
    return {"schema": "py-elk-iteration-change-validation/v1", "status": "CHANGE_CHECKS_VALIDATED",
            "iteration": manifest["iteration"], "passed": True, "fullValidation": False,
            "runtimeReexecuted": False, "historicalExecutionAuthenticated": False,
            "policy": "Change-related checks only; final full validation deferred until all migration features are implemented",
            "manifestSha256": sha256(Path(manifest_path)), "validatorSha256": sha256(Path(__file__)),
            "baselineSha256": sha256(Path(baseline_path)), "inputFilesSha256": before,
            "changedPaths": sorted(name for name in old.keys() | before.keys() if old.get(name) != before.get(name)),
            "checks": receipts, "targetedTests": sum(row["tests"] for row in receipts),
            "inputsUnchanged": True, "pythonAlgorithmsVerified": 0,
            "limitation": "Consistency of named actual change checks and their original logs; not an automatic proof of exhaustive impact coverage or historical execution authenticity."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = check(args.manifest, args.baseline)
        write(args.out, result)
        print(json.dumps({k: result[k] for k in ("status", "iteration", "fullValidation", "targetedTests")}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
