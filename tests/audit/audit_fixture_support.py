"""Dependency-complete mutable audit copies, without unused capture trees.

Only fixture construction lives here. Validators still inspect the copied
bytes, and every semantic mutation keeps its existing positive/target-error
assertions. Files are independent byte copies, never links to the originals.
"""
from contextlib import contextmanager
import builtins
import importlib
import io
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from functools import lru_cache
from unittest.mock import patch


_HISTORICAL_DIRECTORIES = []


@lru_cache(maxsize=1)
def frozen_e09_root():
    """Original audit universe, never a substitute for current package checks.

    Authenticate every archived byte using the immutable E11 history seals.
    The existing semantic negative controls then mutate independent copies of
    that original product, source approvals and same-wheel receipts. Promoted
    full-algorithm source must not be rebound to a bounded E09 execution.
    """
    from iteration.e11_history import material
    repository = Path(__file__).resolve().parents[2]
    files = material(repository)
    temporary = tempfile.TemporaryDirectory(prefix="pyelk-frozen-e09-audit-")
    _HISTORICAL_DIRECTORIES.append(temporary)
    root = Path(temporary.name)
    for name, raw in files.items():
        target = root / _relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return root


def _relative(name):
    if not isinstance(name, str) or "\\" in name:
        raise ValueError("Fixture dependency must be a relative POSIX path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError("Fixture dependency escapes its root")
    return path


def copy_files(source, destination, paths):
    """Copy exactly the declared files; missing dependencies fail immediately."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError("Fixture source and destination must differ")
    copied, size = [], 0
    for name in sorted(set(paths)):
        relative = _relative(name)
        original, target = source / relative, destination / relative
        if not original.resolve().is_relative_to(source) or not target.resolve().is_relative_to(destination):
            raise ValueError("Fixture dependency escapes its root")
        if not original.is_file():
            raise FileNotFoundError(original)
        if target.exists() or target.is_symlink():
            raise FileExistsError("Fixture destination must not contain the copied file: " + str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        size += original.stat().st_size
        copied.append(name)
    return {"copiedFiles": len(copied), "copiedBytes": size, "paths": copied}


def _load(root, name):
    # Use the same strict duplicate-key/finite-value loader as the validators.
    from layout_checks import load
    return load(Path(root) / name)


def source_paths(root, iteration):
    audit = importlib.import_module("validate_" + iteration.lower() + "_source_bindings")
    if hasattr(audit, "evidence_paths"):
        return set(audit.evidence_paths(root))
    manifest = _load(root, audit.MANIFEST)
    paths = {audit.MANIFEST, audit.SCOPE, *audit.DOCUMENTS.values(), *audit.INHERITED, *audit.LICENSES}
    paths |= {p for p in audit.AUXILIARY if (Path(root) / p).is_file()}
    paths |= audit.versioned_review_paths(manifest)
    return paths


def runtime_paths(root, iteration):
    """The actual runtime audit read set plus mutable package-denominator input."""
    root = Path(root)
    audit = importlib.import_module("validate_" + iteration.lower() + "_runtime")
    paths = source_paths(root, iteration) | {audit.AUDIT, *audit.REQUIRED_FILES,
            "UPSTREAM.json", "docs/compatibility.json", "tests/fixtures/validation/cases.json",
            "references/e03-option-sources.json"}
    paths |= {"references/metadata/" + kind + ".json" for kind in ("algorithms", "options", "categories")}
    suite_parent = PurePosixPath(audit.SUITE).parent
    paths |= {(suite_parent / row["request"]).as_posix() for row in _load(root, audit.SUITE)["cases"]}
    if iteration in ("E05", "E06", "E07"):
        paths |= {"references/history/" + iteration + "/material.json", audit.HISTORICAL_WHEEL}
    if iteration in ("E06", "E07"):
        paths.add("references/history/" + iteration + "/metadata-material.json")
    if iteration in ("E06", "E07"):
        paths |= {"pyproject.toml", "README.md"}
    if iteration == "E07":
        # validate_installed deliberately scans the complete current package:
        # keep all real files so an added license/Python file cannot disappear.
        paths |= {p.relative_to(root).as_posix() for p in (root / "src/pyelk").rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    return paths


def e01_paths(root):
    """E01 mapping, current plan evidence and original master-request closure."""
    root = Path(root)
    manifest = _load(root, "references/e01-audit.json")
    paths = {"UPSTREAM.json", "references/e01-audit.json", *manifest["filesSha256"],
             "references/source-inventory.json", "docs/iteration-plan.json", "docs/TASKS.md",
             "docs/PARALLEL_EXECUTION.md", "docs/release-profiles.json", "tests/fixtures/validation/cases.json"}
    plan = _load(root, "docs/iteration-plan.json")
    for row in [*plan["gates"], *plan["iterations"], *plan["integration"]]:
        if row.get("status") in ("verified", "complete"):
            paths |= {evidence["path"] for evidence in row.get("evidence", [])}
        if row.get("status") == "complete" and row.get("retrospective"):
            paths.add((PurePosixPath("docs") / row["retrospective"]).as_posix())
    index = _load(root, "references/assertion-inventory.json")
    paths |= {row["request"] for row in index["projectCases"]}
    return paths


@contextmanager
def record_reads(root):
    """Observe actual read opens, including zipfile's io.open archive reads."""
    root, reads = Path(root).resolve(), set()
    original_builtin, original_io = builtins.open, io.open

    def observer(original):
        def opened(file, mode="r", *args, **kwargs):
            if isinstance(file, (str, bytes, Path)) and ("r" in mode or "+" in mode):
                path = Path(os.fsdecode(file)).resolve()
                if path.is_relative_to(root):
                    reads.add(path.relative_to(root).as_posix())
            return original(file, mode, *args, **kwargs)
        return opened

    with patch("builtins.open", observer(original_builtin)), patch("io.open", observer(original_io)):
        yield reads
