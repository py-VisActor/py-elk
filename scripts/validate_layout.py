"""Capture, compare and independently validate layout observations; never implements layout."""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from layout_checks import (ROOT, PROFILES, DETERMINISM_POLICIES, compare_captures, compare_observations, contained, contract,
                           diff, load, negative_controls, sha256, validate_suite, verify_capture, write)


def source_hashes():
    paths = [*ROOT.glob("scripts/*.py"), *ROOT.glob("tools/reference/*.cjs"),
             *ROOT.glob("tools/reference/*.py"), *ROOT.glob("src/**/*.py")]
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(paths)}


def run(command, directory, timeout, *, env=None):
    """No shell. Preserve stdout, stderr, argv, cwd, elapsed time and failed exits."""
    start = time.monotonic()
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        stdout, stderr, code, timed_out = result.stdout, result.stderr, result.returncode, False
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code, timed_out = error.stdout or b"", error.stderr or b"", None, True
    except OSError as error:
        stdout, stderr, code, timed_out = b"", str(error).encode("utf-8"), None, False
    (directory / "stdout.log").write_bytes(stdout)
    (directory / "stderr.log").write_bytes(stderr)
    record = {"argv": command, "cwd": str(ROOT), "exitCode": code, "timedOut": timed_out,
              "elapsedSeconds": round(time.monotonic() - start, 6), "stdoutSha256": sha256(directory / "stdout.log"),
              "stderrSha256": sha256(directory / "stderr.log")}
    write(directory / "command.json", record)
    return record


def capture(args):
    suite_path = args.cases.resolve()
    suite = validate_suite(suite_path)
    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(exist_ok=False)
    shutil.copyfile(suite_path, out / "suite.json")
    shutil.copyfile(ROOT / "UPSTREAM.json", out / "upstream-lock.json")
    lock = load(ROOT / "UPSTREAM.json")
    role = "reference" if args.action == "reference" else "candidate"
    command = ([args.node, str(ROOT / "tools/reference/capture_layout.cjs"), str(args.package.resolve())]
               if role == "reference" else load(args.command_json))
    if not isinstance(command, list) or not command or not all(isinstance(s, str) and s for s in command):
        raise ValueError("--command-json must contain a nonempty JSON argv array")
    report = {"schema": "py-elk-layout-capture/v1", "role": role, "status": "CAPTURED", "repeat": args.repeat,
              "suiteSha256": sha256(suite_path), "createdUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "host": {"python": sys.version, "platform": platform.platform()}, "commandPrefix": command,
              "sourceSha256": source_hashes(), "upstreamLockSha256": sha256(ROOT / "UPSTREAM.json"),
              "upstreamCommit": lock["javascript"]["commit"],
              "entrypointSha256": lock["distribution"]["sha256Files"]["lib/elk.bundled.js"] if role == "reference" else None,
              "cases": [], "failures": []}
    # Independent deserialization in every engine process; never feed JS-mutated input to Python.
    for case in suite["cases"]:
        directory = out / case["id"]
        directory.mkdir()
        request_path = directory / "request.json"
        shutil.copyfile(contained(suite_path.parent, case["request"]), request_path)
        captured = {"id": case["id"], "definition": case, "request": request_path.relative_to(out).as_posix(),
                    "requestSha256": sha256(request_path), "observations": []}
        for repetition in range(args.repeat):
            attempt = directory / f"run-{repetition + 1:02d}"
            attempt.mkdir()
            observation_path = attempt / "observation.json"
            record = run([*command, str(request_path), str(observation_path)], attempt, args.timeout)
            try:
                if record["exitCode"] != 0:
                    raise ValueError("Engine process failed; inspect stderr.log and command.json")
                observation = load(observation_path)
                contract(observation)
                if observation["requestSha256"] != captured["requestSha256"]:
                    raise ValueError("Engine returned a different input fingerprint")
                if role == "reference" and (observation.get("engine", {}).get("name") != "elkjs" or observation["engine"].get("entrypointSha256") != report["entrypointSha256"]):
                    raise ValueError("Reference engine identity differs")
                if role == "candidate" and observation.get("engine", {}).get("name") != "pyelk":
                    raise ValueError("Candidate must identify the real pyelk engine")
                captured["observations"].append(observation_path.relative_to(out).as_posix())
            except (ValueError, OSError) as error:
                report["status"] = "INCOMPLETE"
                report["failures"].append({"case": case["id"], "repetition": repetition + 1, "message": str(error)})
                break
        report["cases"].append(captured)
        # A missing interpreter/API would otherwise fail identically for every case.
        if report["failures"]:
            break
    report["files"] = {p.relative_to(out).as_posix(): sha256(p) for p in sorted(out.rglob("*")) if p.is_file()}
    write(out / "index.json", report)
    return {"status": report["status"], "role": role, "caseCount": len(report["cases"]), "repeat": args.repeat,
            "failures": report["failures"], "index": str(out / "index.json"), "passed": not report["failures"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("reference", "candidate"):
        p = commands.add_parser(name, help="Capture fresh-process observations (new directory only)")
        p.add_argument("--cases", type=Path, default=ROOT / "tests/fixtures/validation/cases.json")
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--repeat", type=int, default=3)
        p.add_argument("--timeout", type=float, default=30)
        if name == "reference":
            p.add_argument("--package", type=Path, default=ROOT / ".local/npm-elkjs/package")
            p.add_argument("--node", default="node")
        else:
            p.add_argument("--command-json", type=Path, required=True,
                           help='JSON argv prefix; adapter receives REQUEST_JSON NEW_OBSERVATION_JSON')
    for name in ("compare", "replay"):
        p = commands.add_parser(name, help="Compare whole captures" if name == "compare" else "Reproduce an official capture; no Python acceptance")
        p.add_argument("--reference", type=Path, required=True)
        p.add_argument("--candidate", type=Path, required=True, help="New official capture for replay; Python capture for compare")
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--determinism-policy", choices=DETERMINISM_POLICIES, default="explicit-nonzero-seed")
        if name == "compare":
            p.add_argument("--profile", choices=PROFILES, default="strict")
    p = commands.add_parser("selftest", help="Official positives and deliberately broken negative controls; no Python layout claim")
    p.add_argument("--reference", type=Path, default=ROOT / "references/layout")
    p.add_argument("--out", type=Path, required=True)
    p = commands.add_parser("pair", help="Full JSON diff for two observation envelopes")
    p.add_argument("--expected", type=Path, required=True)
    p.add_argument("--actual", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--profile", choices=PROFILES, default="strict")
    p.add_argument("--request", type=Path, help="Original request bytes; mandatory for the native profile")
    p = commands.add_parser("verify", help="Verify capture artifact hashes and case denominators")
    p.add_argument("directory", type=Path)
    p = commands.add_parser("json", help="Diff raw JSON/metadata or raw layout graphs")
    p.add_argument("--expected", type=Path, required=True)
    p.add_argument("--actual", type=Path, required=True)
    p.add_argument("--kind", choices=("json", "graph"), default="json", help="graph wraps geometry paths for coordinate tolerance")
    p.add_argument("--out", type=Path, required=True)
    p = commands.add_parser("candidate-command", help="Write the argv JSON for the real installed pyelk adapter")
    p.add_argument("--python", default=sys.executable, help="Python executable from the candidate environment")
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.action in ("reference", "candidate") and (args.repeat < 1 or not 0 < args.timeout <= 300):
        parser.error("repeat must be >=1; timeout must be in (0,300] seconds")
    # Reserve no success result when a capture is absent, partial, or malformed.
    try:
        if args.action in ("reference", "candidate"):
            result = capture(args)
        elif args.action in ("compare", "replay"):
            result = compare_captures(args.reference.resolve(), args.candidate.resolve(), replay=args.action == "replay",
                                      profile=args.profile if args.action == "compare" else "strict",
                                      determinism_policy=args.determinism_policy)
            write(args.out, result)
        elif args.action == "selftest":
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.mkdir(exist_ok=False)
            result = negative_controls(args.reference.resolve(), args.out)
            write(args.out / "report.json", result)
        elif args.action == "pair":
            result = compare_observations(load(args.expected), load(args.actual), profile=args.profile, request=args.request)
            result.update(status="PAIR_CHECKED",
                          limitation="JSON comparison only; no suite, geometry, determinism or provenance acceptance.")
            write(args.out, result)
        elif args.action == "json":
            a, b = load(args.expected), load(args.actual)
            if args.kind == "graph":
                a, b = {"result": a}, {"result": b}
            result = {"status": "RAW_JSON_CHECKED", "kind": args.kind, "exact": diff(a, b),
                      "coordinateTolerance": diff(a, b, tolerant=True),
                      "expectedSha256": sha256(args.expected), "actualSha256": sha256(args.actual),
                      "limitation": "Raw JSON diff only; not input provenance, geometry or engine acceptance."}
            result["passed"] = result["coordinateTolerance"]["passed"]
            write(args.out, result)
        elif args.action == "candidate-command":
            write(args.out, [args.python, "-I", str(ROOT / "scripts/run_pyelk_candidate.py")])
            result = {"status": "CANDIDATE_COMMAND_WRITTEN", "passed": True}
        else:
            index = verify_capture(args.directory.resolve())
            result = {"status": "CAPTURE_INTEGRITY_VERIFIED", "passed": True, "caseCount": len(index["cases"]),
                      "limitation": "File integrity only, not behavior acceptance or cryptographic attestation."}
        print(json.dumps({key: result[key] for key in ("status", "passed", "caseCount", "failures", "index") if key in result}, indent=2))
        return 2 if result["status"] == "INCOMPLETE" else (0 if result["passed"] else 1)
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({"status": "HARNESS_ERROR", "passed": False, "error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
