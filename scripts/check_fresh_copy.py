"""Check a new Git-filtered copy without changing the real repository's index.

Copies only versioned/nonignored work files, stages in an isolated temporary Git
repository, exports through checkout-index, and executes the offline entry there.
No existing files are removed. The new output keeps staging, copy and all logs.
"""
import argparse
from pathlib import Path
import shutil
import sys

from layout_checks import ROOT, sha256, write
import validate_layout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    records = []

    def command(name, argv, *, timeout=300):
        directory = out / (name + "-command")
        directory.mkdir()
        result = validate_layout.run(argv, directory, timeout)
        records.append({"name": name, **result})
        if result["exitCode"] != 0:
            raise RuntimeError(name + " failed; see " + str(directory))
        return directory

    listed = command("list", ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"])
    names = sorted(set((listed / "stdout.log").read_bytes().decode("utf-8").strip("\0").split("\0")))
    names = [name for name in names if name and (ROOT / name).is_file()]
    staging, checkout = out / "staging", out / "checkout"
    staging.mkdir()
    checkout.mkdir()
    before = {}
    for name in names:
        target = staging / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
        before[name] = sha256(ROOT / name)
    command("init", ["git", "-C", str(staging), "init", "--quiet"])
    command("stage", ["git", "-C", str(staging), "-c", "core.autocrlf=false", "add", "--all"])
    command("export", ["git", "-C", str(staging), "checkout-index", "--all", "--prefix=" + checkout.as_posix() + "/"])
    if (checkout / ".git").exists() or (checkout / ".local").exists():
        raise RuntimeError("Fresh copy contains a Git repository or local cache")
    changed = [{"path": name, "originalSha256": before[name], "filteredSha256": sha256(checkout / name)}
               for name in names if sha256(checkout / name) != before[name]]
    write(out / "copy.json", {"files": len(names), "checkout": str(checkout), "gitPresent": False,
                              "localCachePresent": False, "filterChangedFiles": changed, "commands": records})
    previous_root = validate_layout.ROOT
    try:
        validate_layout.ROOT = checkout
        command("offline-check", [sys.executable, str(checkout / "scripts/check.py"), "--out", str(out / "evidence")], timeout=1200)
    finally:
        validate_layout.ROOT = previous_root
    print("FRESH_GIT_FILTERED_CHECK_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
