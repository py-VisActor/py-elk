"""Fetch and verify the locked development-only elkjs source and npm artifact.

Does not build Java/GWT, alter a dirty checkout, regenerate existing inventories,
or implement Python layout. Python 3.11+; runtime pyelk never imports this module.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = ROOT / ".local/upstream-elkjs"
PACKAGE = ROOT / ".local/npm-elkjs/package"


def git(checkout: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(checkout), *args])


def verify_source(checkout: Path, lock: dict) -> None:
    """Check commit/clean state and canonical blob SHA; never repair drift."""
    if git(checkout, "rev-parse", "HEAD").decode().strip() != lock["javascript"]["commit"]:
        raise ValueError("Source commit differs from lock")
    if git(checkout, "status", "--porcelain"):
        raise ValueError("Source checkout is dirty")
    for name, sha in lock["sourceSha256"].items():
        if hashlib.sha256(git(checkout, "show", "HEAD:" + name)).hexdigest() != sha:
            raise ValueError("Source hash differs: " + name)


def inventory(checkout: Path, lock: dict) -> dict:
    verify_source(checkout, lock)
    files = []
    for line in git(checkout, "ls-tree", "-r", "HEAD").decode().splitlines():
        info, path = line.split("\t", 1)
        _, kind, blob = info.split()
        if kind != "blob":
            continue
        category = ("test_source" if path.startswith("test/mocha/") else
                    "test_example" if path.startswith("test/examples/") else
                    "type_declaration" if path.endswith(".d.ts") else
                    "javascript_source" if path.startswith("src/js/") else
                    "java_adapter" if path.endswith((".java", ".xtend")) else "support")
        files.append({"path": path, "gitBlob": blob, "category": category})
    return {"schema": "py-elk-source-inventory/v1", "commit": lock["javascript"]["commit"],
            "files": files, "counts": dict(Counter(item["category"] for item in files)),
            "limitation": "All 64 elkjs Git-tree files indexed. Fourteen Mocha files are not an assertion count or a complete ELK Java algorithm test inventory."}


def verify_package(package: Path, lock: dict) -> None:
    expected = lock["distribution"]["sha256Files"]
    actual = {path.relative_to(package).as_posix() for path in package.rglob("*") if path.is_file()}
    if actual != set(expected):
        raise ValueError("npm package file inventory differs")
    for name, sha in expected.items():
        if hashlib.sha256((package / name).read_bytes()).hexdigest() != sha:
            raise ValueError("npm package hash differs: " + name)


def safe_member(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or any(":" in part for part in path.parts) or not path.parts or path.parts[0] != "package":
        raise ValueError("Unsafe npm archive path: " + name)
    return path


def fetch_package(lock: dict) -> None:
    archive = ROOT / ".local/elkjs-0.12.1.tgz"
    if archive.exists():
        data = archive.read_bytes()
    else:
        with urllib.request.urlopen(lock["distribution"]["tarball"], timeout=60) as response:
            data = response.read(64 * 1024 * 1024 + 1)
        if len(data) > 64 * 1024 * 1024:
            raise ValueError("npm archive exceeds download limit")
        with archive.open("xb") as stream:
            stream.write(data)
    digest = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()
    if digest != lock["distribution"]["integrity"] or hashlib.sha256(data).hexdigest() != lock["distribution"]["sha256"]:
        raise ValueError("npm archive integrity differs; keep failed artifact for inspection")
    parent = PACKAGE.parent
    if parent.exists():
        raise FileExistsError("Partial npm extraction exists; investigate instead of overwriting")
    parent.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive_file:
        for member in archive_file:
            relative = safe_member(member.name)
            target = parent.joinpath(*relative.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                content = archive_file.extractfile(member)
                if content is None:
                    raise ValueError("Missing archive content: " + member.name)
                with target.open("xb") as stream:
                    stream.write(content.read())
            else:
                raise ValueError("Links and special npm archive entries are not allowed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["fetch", "check"])
    args = parser.parse_args()
    lock = json.loads((ROOT / "UPSTREAM.json").read_text(encoding="utf-8"))
    if args.action == "fetch":
        if not CHECKOUT.exists():
            CHECKOUT.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "--depth", "1", "--single-branch", "--branch",
                            lock["javascript"]["tag"], lock["javascript"]["repository"] + ".git", str(CHECKOUT)], check=True)
        verify_source(CHECKOUT, lock)
        if not PACKAGE.exists():
            fetch_package(lock)
    actual = inventory(CHECKOUT, lock)
    expected = json.loads((ROOT / "references/source-inventory.json").read_text(encoding="utf-8"))
    if actual != expected:
        raise ValueError("Saved source inventory differs; do not regenerate to hide drift")
    verify_package(PACKAGE, lock)
    print(json.dumps({"status": "UPSTREAM_PROVENANCE_VERIFIED", "version": lock["javascript"]["version"],
                      "sourceFiles": len(actual["files"]), "pythonAlgorithmsVerified": 0,
                      "javaImplementationSource": lock["javaImplementationSource"]["status"]}))


if __name__ == "__main__":
    main()
