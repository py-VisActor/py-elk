"""Conservative development-test selection; never a final acceptance certificate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("bootstrap", "validation", "contract", "foundation", "model", "options", "execution",
          "layered", "api", "conformance", "audit")
STEP_GROUP = {"validator-tests": "validation", "option-tests": "options", "context-tests": "execution"}
STEP_GROUP.update({name + "-tests": name for name in GROUPS if name not in ("validation", "options", "execution")})
SOURCE_GROUPS = {
    "src/pyelk/api.py": {"api", "execution", "contract", "conformance", "audit"},
    "src/pyelk/algorithms/": {"layered", "api", "conformance", "audit"},
    "src/pyelk/model/": {"model", "foundation", "execution", "layered", "api", "conformance", "audit"},
    "src/pyelk/options/": {"options", "foundation", "execution", "layered", "api", "conformance", "audit"},
    "src/pyelk/execution/": {"execution", "api", "contract", "conformance", "audit"},
}


def relative_name(name):
    if type(name) is not str or not name or "\\" in name or ":" in name:
        raise ValueError("Expected a repository-relative POSIX path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError("Unsafe changed path")
    return name


def input_hashes(root=ROOT):
    """Read inputs shared by full checks; excludes generated runs and caches."""
    root = Path(root)
    names = set()
    excluded = {".git", ".local", ".venv", "venv", "test-runs", "build", "dist", "node_modules",
                ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    for directory, folders, files in os.walk(root):
        relative = Path(directory).relative_to(root).parts
        if not relative:
            folders[:] = [name for name in folders if name not in excluded]
        if relative == ("src",):
            folders[:] = [name for name in folders if not name.endswith(".egg-info")]
        fixture = relative[:2] == ("tests", "fixtures")
        if not fixture:
            folders[:] = [name for name in folders if name != "__pycache__"]
        for name in files:
            path = Path(directory) / name
            if fixture or path.suffix != ".pyc":
                names.add(path.relative_to(root).as_posix())
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sorted(names)}


def changed_since(baseline, root=ROOT):
    fields = ("inputFilesSha256", "worktreeFilesSha256")
    old = next((baseline[key] for key in fields if key in baseline), None)
    if type(old) is not dict or not old:
        raise ValueError("Baseline lacks complete input-file fingerprints")
    for name, digest in old.items():
        relative_name(name)
        if type(digest) is not str or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Invalid baseline SHA")
    current = input_hashes(root)
    # Worktree snapshots may contain examples and other non-check inputs. Keep
    # their changes visible, so unknown dependencies conservatively choose full.
    for name in set(old) - set(current):
        p = Path(root) / name
        if p.is_file():
            current[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return sorted(name for name in old.keys() | current.keys() if old.get(name) != current.get(name))


def plan_changes(changed):
    changed = sorted({relative_name(name) for name in changed})
    groups, specific, reasons, unknown = set(), {}, [], []
    for name in changed:
        parts = PurePosixPath(name).parts
        if len(parts) >= 3 and parts[0] == "tests" and parts[1] in GROUPS:
            group = parts[1]
            groups.add(group)
            if len(parts) == 3 and parts[2].startswith("test_") and parts[2].endswith(".py"):
                if group not in specific:
                    specific[group] = set()
                if specific[group] is not None:
                    specific[group].add(parts[2])
            else:
                specific[group] = None
            reasons.append({"path": name, "reason": "test-owner-group"})
            continue
        matches = [value for prefix, value in SOURCE_GROUPS.items()
                   if name == prefix or (prefix.endswith("/") and name.startswith(prefix))]
        if matches:
            selected = set().union(*matches)
            groups.update(selected)
            for group in selected:
                specific[group] = None
            reasons.append({"path": name, "reason": "declared-source-dependencies"})
        elif (name in {"AGENTS.md", "API_COMPATIBILITY.md", "DEVELOPMENT_PLAN.md", "THIRD_PARTY_NOTICES.md"}
              or (name.startswith("docs/") and not name.startswith("docs/decisions/") and name.endswith(".md"))):
            groups.add("bootstrap"); specific["bootstrap"] = None
            reasons.append({"path": name, "reason": "documentation-structure; final metadata gate is separate"})
        else:
            unknown.append(name)
    fallback = bool(unknown)
    if fallback:
        groups, specific = set(GROUPS), {}
    return {"schema": "py-elk-change-impact/v1", "changedPaths": changed,
            "groups": [name for name in GROUPS if name in groups],
            "specificTests": {name: sorted(values) if values is not None else None for name, values in specific.items()},
            "unknownPaths": unknown, "fallbackToFull": fallback, "reasons": reasons,
            "finalAcceptance": False, "limitation": "Development selection only; complete final checks remain mandatory."}


def select_steps(steps, plan):
    if plan["fallbackToFull"]:
        return list(steps)
    selected = []
    for name, argv in steps:
        group = STEP_GROUP.get(name)
        if group not in plan["groups"]:
            continue
        files = plan["specificTests"].get(group)
        if files:
            for file in files:
                command = list(argv)
                command[-1:-1] = ["-p", file]
                selected.append((name + "--" + file.removesuffix(".py"), command))
        else:
            selected.append((name, argv))
    # Keep the independent metadata/source-plan consistency check on all runs.
    selected += [step for step in steps if step[0] in ("bootstrap", "source-audit")]
    return selected


def execution_context(*, with_reference=False):
    keys = ("PATH", "PYTHONPATH", "PYTHONHOME", "PYTHONHASHSEED", "PYTHONUTF8", "PYTHONIOENCODING",
            "LANG", "LC_ALL", "TZ", "TEMP", "TMP", "TMPDIR", "SYSTEMROOT", "COMSPEC")
    environment = {name: os.environ.get(name) for name in keys}
    result = {"python": sys.version, "executableSha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
              "platform": platform.platform(), "environmentKeys": list(keys),
              "environmentSha256": hashlib.sha256(json.dumps(environment, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
    if with_reference:
        node = shutil.which("node")
        result["nodeExecutableSha256"] = hashlib.sha256(Path(node).read_bytes()).hexdigest() if node else None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--changed", nargs="*", default=[])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if bool(args.baseline) == bool(args.changed):
        parser.error("Provide a complete --baseline or explicit --changed paths")
    changed = changed_since(json.loads(args.baseline.read_bytes())) if args.baseline else args.changed
    result = plan_changes(changed)
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False); stream.write("\n")
    print(json.dumps({"groups": result["groups"], "fallbackToFull": result["fallbackToFull"]}))


if __name__ == "__main__":
    main()
