"""Inventory assertions for human migration review, then run real smoke tests."""
import argparse
import ast
import json
from pathlib import Path
import sys

from change_impact import ROOT, changed_since, plan_changes
from layout_checks import sha256, write
from validate_layout import run


def assertion_inventory(root=ROOT):
    rows = []
    for folder in ("api", "layered", "conformance"):
        for path in sorted((Path(root) / "tests" / folder).glob("test_*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for method in ast.walk(tree):
                if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) or not method.name.startswith("test_"):
                    continue
                assertions = [node for node in ast.walk(method) if isinstance(node, ast.Call)
                              and isinstance(node.func, ast.Attribute) and node.func.attr.startswith("assertRaises")]
                if "unsupported" in method.name.lower() or assertions:
                    rows.append({"path": path.relative_to(root).as_posix(), "test": method.name,
                                 "line": method.lineno, "sha256": sha256(path),
                                 "assertionLines": sorted(node.lineno for node in assertions),
                                 "disposition": "human-review-required; no automatic support inference"})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--inventory-only", action="store_true")
    args = parser.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    plan = plan_changes(changed_since(json.loads(args.baseline.read_bytes())))
    inventory = assertion_inventory()
    write(out / "impact.json", plan); write(out / "assertion-inventory.json", {"rows": inventory})
    commands = []
    if not args.inventory_only:
        for name, folder, pattern in (("api-smoke", "api", "test_e04_api.py"),
                                      ("layout-smoke", "conformance", "test_e07_native.py")):
            directory = out / name; directory.mkdir()
            result = run([sys.executable, "-m", "unittest", "discover", "-s", "tests/" + folder, "-p", pattern, "-v"], directory, 180)
            commands.append({"name": name, **result})
    passed = all(row["exitCode"] == 0 for row in commands) if commands else None
    status = "INVENTORY_ONLY" if args.inventory_only else "PREFLIGHT_PASS" if passed else "FAIL"
    write(out / "report.json", {"schema": "py-elk-preflight/v1", "status": status,
          "passed": passed, "smokeExecuted": bool(commands), "smokePassed": passed,
          "commands": commands, "inventoryRows": len(inventory), "impact": plan,
          "fullValidation": False, "migrationReviewCompleted": False,
          "limitation": "Smoke execution plus an inventory for human review; never automatically approves migrated assertions or final acceptance."})
    print(status); return int(passed is False)


if __name__ == "__main__":
    raise SystemExit(main())
