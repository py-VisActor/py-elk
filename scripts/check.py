"""Fresh-session checks with saved commands/logs; optional genuine oracle replay.

This certifies development tooling only. No Python layout implementation exists yet.
"""
import argparse
from pathlib import Path
import sys

from layout_checks import ROOT, sha256, write
from validate_layout import run, source_hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New directory for all evidence")
    parser.add_argument("--with-reference", action="store_true", help="Also check local upstream and recapture all cases with Node")
    args = parser.parse_args()
    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(exist_ok=False)
    python = sys.executable
    steps = [
        ("bootstrap", [python, "scripts/validate_bootstrap.py"]),
        ("bootstrap-tests", [python, "-m", "unittest", "discover", "-s", "tests/bootstrap", "-v"]),
        ("validator-tests", [python, "-m", "unittest", "discover", "-s", "tests/validation", "-v"]),
        ("selftest", [python, "scripts/validate_layout.py", "selftest", "--out", str(out / "controls")]),
    ]
    if args.with_reference:
        steps.extend([
            ("upstream", [python, "scripts/upstream.py", "check"]),
            ("capture", [python, "scripts/validate_layout.py", "reference", "--out", str(out / "reference"), "--repeat", "3"]),
            ("replay", [python, "scripts/validate_layout.py", "replay", "--reference", "references/layout", "--candidate", str(out / "reference"), "--out", str(out / "replay.json")]),
        ])
    records = []
    for name, command in steps:
        # Capture output itself uses a new directory, so command logs stay separate.
        directory = out / (name + "-command")
        directory.mkdir()
        print("Checking " + name, flush=True)
        record = run(command, directory, 300)
        records.append({"name": name, **record})
        if record["exitCode"] != 0:
            print(f"{name} failed (exit {record['exitCode']}); see {directory}", flush=True)
            print((directory / "stderr.log").read_text(encoding="utf-8", errors="replace")[-4000:], flush=True)
    passed = all(r["exitCode"] == 0 for r in records)
    report = {"schema": "py-elk-development-check/v1", "status": "DEVELOPMENT_CHECKS_PASS" if passed else "FAIL",
              "passed": passed, "commands": records, "sourceSha256": source_hashes(),
              "files": {p.relative_to(out).as_posix(): sha256(p) for p in sorted(out.rglob("*")) if p.is_file()},
              "pythonAlgorithmsVerified": 0, "limitation": "Harness/source checks, not Python algorithm or release acceptance."}
    write(out / "report.json", report)
    print(report["status"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
