"""Sequential same-interpreter before/after full checks with actual saved logs."""
import argparse
import ast
import datetime
from pathlib import Path
import re
import sys
import time

from layout_checks import load, sha256, write
import validate_layout


def methods(root):
    result = set()
    for path in (Path(root) / "tests").rglob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            for method in cls.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith("test_"):
                    result.add(path.relative_to(root).as_posix() + "::" + cls.name + "." + method.name)
    return result


def run_pair(baseline, candidate, out, python):
    baseline, candidate, out = Path(baseline).resolve(), Path(candidate).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    old_methods, new_methods = methods(baseline), methods(candidate)
    missing = sorted(old_methods - new_methods)
    if missing:
        raise ValueError("Original test methods were removed: " + str(missing))
    records = {}
    previous = validate_layout.ROOT
    try:
        for name, root in (("baseline", baseline), ("candidate", candidate)):
            directory = out / (name + "-command"); directory.mkdir()
            evidence = out / (name + "-check")
            validate_layout.ROOT = root
            command = [str(Path(python).resolve()), str(root / "scripts/check.py"), "--out", str(evidence)]
            print("Benchmark " + name, flush=True)
            record = validate_layout.run(command, directory, 1200)
            write(directory / "report.json", record)
            report = load(evidence / "report.json") if (evidence / "report.json").is_file() else None
            if record["exitCode"] != 0 or not report or report["passed"] is not True:
                raise ValueError("Benchmark " + name + " did not pass; retain actual logs")
            counts = {}
            for row in report["commands"]:
                if row["name"].endswith("-tests"):
                    raw = (evidence / (row["name"] + "-command/stderr.log")).read_text(encoding="utf-8")
                    match = re.search(r"Ran (\d+) tests?", raw)
                    if match is None:
                        raise ValueError("Missing real unittest count")
                    counts[row["name"]] = int(match[1])
            records[name] = {"wallSeconds": record["elapsedSeconds"], "unitCounts": counts,
                             "unitTotal": sum(counts.values()), "commands": len(report["commands"]),
                             "stepsSeconds": {row["name"]: row["elapsedSeconds"] for row in report["commands"]},
                             "reportSha256": sha256(evidence / "report.json"),
                             "sourceSha256": report["sourceSha256"]}
    finally:
        validate_layout.ROOT = previous
    before, after = records["baseline"], records["candidate"]
    if before["unitTotal"] < 688 or after["unitTotal"] < before["unitTotal"]:
        raise ValueError("Original execution test denominator shrank")
    value = {"schema": "py-elk-full-check-benchmark/v1", "status": "FULL_CHECK_BENCHMARK_PASS",
             "createdUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "executionOrder": ["baseline", "candidate"], "sameInterpreter": str(Path(python).resolve()),
             "records": records, "originalMethodsRetained": len(old_methods), "newMethods": len(new_methods - old_methods),
             "wallReductionPercent": 100 * (1 - after["wallSeconds"] / before["wallSeconds"]),
             "speedRatio": before["wallSeconds"] / after["wallSeconds"],
             "auditReductionPercent": 100 * (1 - after["stepsSeconds"]["audit-tests"] / before["stepsSeconds"]["audit-tests"]),
             "pythonAlgorithmsVerified": 0,
             "limitation": "One sequential same-host pair, baseline first; not a universal speed guarantee or proof of equivalent test semantics. Original methods and actual counts are checked; independent negative-control review remains required."}
    write(out / "report.json", value)
    print(value["status"], "wall reduction", round(value["wallReductionPercent"], 2), flush=True)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", type=Path, default=validate_layout.ROOT)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(); run_pair(args.baseline, args.candidate, args.out, args.python)


if __name__ == "__main__":
    main()
