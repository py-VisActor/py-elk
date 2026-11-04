"""Run with the candidate Python -I; bind actual installed package to a wheel."""
import argparse
import base64
from email.parser import BytesParser
import hashlib
import importlib.metadata
import json
import re
from pathlib import Path, PurePosixPath
import sys
import zipfile


def verify(wheel):
    import pyelk

    package = Path(pyelk.__file__).resolve().parent
    distribution = importlib.metadata.distribution("py-elk")
    if Path(distribution.locate_file("pyelk/__init__.py")).resolve() != Path(pyelk.__file__).resolve():
        raise ValueError("Imported package does not belong to the selected distribution")
    expected = {}
    with zipfile.ZipFile(wheel) as archive:
        metadata_paths = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA") and len(PurePosixPath(name).parts) == 2]
        if len(metadata_paths) != 1:
            raise ValueError("Wheel must contain one distribution METADATA record")
        raw_metadata = archive.read(metadata_paths[0])
        metadata = BytesParser().parsebytes(raw_metadata)
        normalized = lambda value: re.sub(r"[-_.]+", "-", value or "").lower()
        if (normalized(metadata["Name"]) != "py-elk" or normalized(distribution.metadata["Name"]) != "py-elk"
                or metadata["Version"] != distribution.version or pyelk.__version__ != distribution.version
                or Path(distribution.locate_file(metadata_paths[0])).read_bytes() != raw_metadata):
            raise ValueError("Wheel/installed/imported distribution name or version differs")
        for name in archive.namelist():
            if not name.startswith("pyelk/") or name.endswith("/"):
                continue
            relative = PurePosixPath(name).relative_to("pyelk")
            target = (package / str(relative)).resolve()
            if not target.is_relative_to(package):
                raise ValueError("Wheel package entry escapes its package directory")
            if target.suffix.lower() in {".js", ".cjs", ".mjs", ".jar", ".wasm"}:
                raise ValueError("Backend artifact found inside native package")
            raw = archive.read(name)
            if not target.is_file() or target.read_bytes() != raw:
                raise ValueError("Installed package differs from wheel: " + name)
            expected[relative.as_posix()] = hashlib.sha256(raw).hexdigest()
    actual = {path.relative_to(package).as_posix() for path in package.rglob("*")
              if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}
    if actual != set(expected):
        raise ValueError("Installed package file denominator differs from wheel")
    if not {"_licenses/elkjs-LICENSE.md", "_licenses/NOTICE.md"} <= actual:
        raise ValueError("Wheel omits source license notices")
    return {"status": "INSTALLED_WHEEL_BYTES_MATCH", "wheelSha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "version": distribution.version, "modulePath": str(package), "python": sys.version,
            "distributionMetadata": {"archivePath": metadata_paths[0], "sha256": hashlib.sha256(raw_metadata).hexdigest(),
                                     "bytesBase64": base64.b64encode(raw_metadata).decode("ascii")},
            "isolatedInterpreter": bool(sys.flags.isolated), "packageFilesSha256": expected,
            "limitation": "Installation/content check only; layout is verified separately."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not sys.flags.isolated:
        raise SystemExit("Use the installed candidate Python with -I")
    result = verify(args.wheel.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(result["status"])
