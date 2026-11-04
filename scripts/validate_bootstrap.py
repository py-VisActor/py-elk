"""Validate project structure, source/metadata denominators and honest scope.

Reads local files only. Does not require Node/JVM/Canvas and never certifies layout.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tomllib
from urllib.parse import unquote, urlsplit

from layout_checks import ABS_TOL, REL_TOL, sha256, validate_suite, verify_capture

ROOT = Path(__file__).resolve().parents[1]


def load(root: Path, path: str):
    return json.loads((root / path).read_text(encoding="utf-8"))


def local_file(root: Path, name: str) -> bool:
    path = (root / name).resolve()
    return not Path(name).is_absolute() and path.is_relative_to(root.resolve()) and path.is_file()


def documentation_origin(root: Path, name: Path) -> Path:
    """Resolve copied evidence documents using their original repository path.

    Archived source/doc bytes keep relative links authored before archival;
    their storage prefix is not a relocated documentation publishing root.
    Links are still required to resolve to a real file or directory.
    """
    parts=name.relative_to(root).parts
    if len(parts)>3 and parts[:2]==('references','next-native-evidence'):
        remainder=parts[3:]
        if remainder[0]in('docs','references','src','tools','examples','tests'):
            return root.joinpath(*remainder)
        if len(remainder)==1:
            return root/remainder[0]
        for index,part in enumerate(remainder[:-1]):
            if part=='snapshot'and remainder[index+1]=='src':
                return root.joinpath(*remainder[index+1:])
    return name


def check(root: Path = ROOT) -> dict:
    errors = []
    required = ["README.md", "README.en.md", "DEVELOPMENT_PLAN.md", "API_COMPATIBILITY.md", "UPSTREAM.json",
                "THIRD_PARTY_NOTICES.md", "docs/NEW_SESSION.md", "docs/IMPLEMENTATION_PLAN.md", "docs/TASKS.md",
                "docs/TEST_AND_RELEASE.md", "docs/RELEASE_STATUS.md", "docs/MERMAID_INTEGRATION.md",
                "docs/FIRST_RELEASE_SCOPE.md", "docs/release-profiles.json",
                "references/README.md", "references/licenses/elkjs-LICENSE.md", "tools/reference/README.md",
                "src/pyelk/__init__.py", "src/pyelk/py.typed", "examples/show_scope.py"]
    required += ["scripts/check.py", "scripts/validate_layout.py", "scripts/layout_checks.py", "scripts/run_pyelk_candidate.py",
                 "tools/reference/capture_layout.cjs", "docs/LAYOUT_VALIDATION.md", "tests/validation/test_layout_checks.py",
                 "tests/fixtures/validation/cases.json", "references/layout/index.json"]
    errors.extend("Missing required file: " + name for name in required if not local_file(root, name))
    lock = load(root, "UPSTREAM.json")
    ledger = load(root, "docs/compatibility.json")
    source = load(root, "references/source-inventory.json")
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    if lock["javascript"]["version"] != "0.12.1" or lock["javascript"]["commit"] != "624ae90aa37110033a8af59c5ccbb292708b4317":
        errors.append("Behavior baseline changed")
    if ledger["upstreamCommit"] != lock["javascript"]["commit"] or source["commit"] != lock["javascript"]["commit"]:
        errors.append("Commit differs between source lock and ledgers")
    if ledger["upstreamVersion"] != lock["javascript"]["version"]:
        errors.append("Version differs between lock and ledger")
    if lock["integrationPolicy"]["legacyElkCompatibilityRequired"] is not False:
        errors.append("An unwanted legacy ELK compatibility profile was added")
    if lock["releasePlan"]["firstReleaseDependsOnMermaid"] is not False or lock["releasePlan"]["mermaidIntegrationSeparate"] is not True:
        errors.append("Basic package release must precede independent Mermaid integration")
    profiles = load(root, "docs/release-profiles.json")
    for profile in profiles["profiles"]:
        if profile["mermaidIntegrationRequired"]:
            errors.append("Basic release profile unexpectedly requires Mermaid")
        if not set(profile["algorithms"]) <= {item["id"] for item in ledger["algorithms"]}:
            errors.append("Release profile names an unknown algorithm")
        if not set(profile["options"]) <= {item["id"] for item in ledger["options"]}:
            errors.append("Release profile names an unknown option")
    if project["dependencies"] or project["requires-python"] != ">=3.11":
        errors.append("Bootstrap dependency or Python contract differs")
    tree = ast.parse((root / "src/pyelk/__init__.py").read_text(encoding="utf-8"))
    versions = [ast.literal_eval(item.value) for item in tree.body if isinstance(item, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "__version__" for target in item.targets)]
    if versions != [project["version"]]:
        errors.append("Scaffold version differs")
    if dict(Counter(item["category"] for item in source["files"])) != source["counts"]:
        errors.append("Source category counts differ")
    if len({item["path"] for item in source["files"]}) != len(source["files"]):
        errors.append("Duplicate source inventory path")
    for name, sha in lock["metadataCapture"]["files"].items():
        if not local_file(root, name) or hashlib.sha256((root / name).read_bytes()).hexdigest() != sha:
            errors.append("Metadata snapshot hash differs: " + name)
    for group in ("algorithms", "options", "categories"):
        snapshot = load(root, "references/metadata/" + group + ".json")
        ids = [item["id"] for item in snapshot]
        actual = [item["id"] for item in ledger[group]]
        if len(ids) != len(set(ids)) or len(actual) != len(set(actual)) or set(ids) != set(actual):
            errors.append("Coverage denominator differs: " + group)
        if len(ids) != lock["metadataCapture"]["counts"][group]:
            errors.append("Metadata count differs: " + group)
    for group in ("api", "algorithms", "options", "categories", "crossCutting"):
        for item in ledger[group]:
            fields = ("status", "api", "semantics", "coordinates")
            if any(field in item and item[field] not in ledger["stages"] for field in fields):
                errors.append("Unknown verification stage: " + item["id"])
            if any(item.get(field, "planned") not in ("planned", "inventoried") for field in fields):
                if not item.get("evidence"):
                    errors.append("Verified stage requires evidence: " + item["id"])
            for evidence in item.get("evidence", []):
                if not isinstance(evidence, dict) or not local_file(root, evidence.get("path", "")):
                    errors.append("Invalid evidence: " + item["id"])
                elif hashlib.sha256((root / evidence["path"]).read_bytes()).hexdigest() != evidence.get("sha256"):
                    errors.append("Evidence hash differs: " + item["id"])
    for case in load(root, "tests/fixtures/cases.json")["cases"]:
        if not local_file(root / "tests/fixtures", case["input"]):
            errors.append("Invalid fixture path: " + case["id"])
    if (ABS_TOL, REL_TOL) != (lock["coordinateComparisonPlanned"]["absoluteTolerance"], lock["coordinateComparisonPlanned"]["relativeTolerance"]):
        errors.append("Coordinate tolerance differs from source lock")
    try:
        reference = lock["referenceFixtures"]
        directory = root / reference["path"]
        if sha256(directory / "index.json") != reference["indexSha256"]:
            errors.append("Layout reference index hash differs")
        capture = verify_capture(directory)
        suite_path = root / "tests/fixtures/validation/cases.json"
        suite = validate_suite(suite_path)
        if sha256(suite_path) != capture["suiteSha256"] or len(capture["cases"]) != reference["caseCount"]:
            errors.append("Layout fixture suite denominator/fingerprint differs")
        for case, saved in zip(suite["cases"], capture["cases"]):
            if sha256(suite_path.parent / case["request"]) != saved["requestSha256"]:
                errors.append("Layout request differs from reference: " + case["id"])
    except (ValueError, KeyError, OSError) as error:
        errors.append("Invalid layout reference: " + str(error))
    markdown = []
    for name in [*root.glob("*.md"), *[p for directory in ("docs", "references", "src", "tests", "tools", "examples", "benchmarks") for p in (root / directory).rglob("*.md")]]:
        markdown.append(name)
        origin=documentation_origin(root,name)
        inside = False
        language = ""
        lines = []
        for line in name.read_text(encoding="utf-8").splitlines():
            fence = re.fullmatch(r"```(\w*)\s*", line)
            if fence:
                if inside and language == "python":
                    try:
                        ast.parse("\n".join(lines))
                    except SyntaxError:
                        errors.append("Invalid Python example: " + str(name.relative_to(root)))
                inside = not inside
                language = fence[1]
                lines = []
                continue
            if inside:
                lines.append(line)
                continue
            for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", line):
                if urlsplit(target).scheme or target.startswith("#"):
                    continue
                path = unquote(target.split("#", 1)[0])
                if path and not (name.parent / path).exists()and not(origin.parent/path).exists():
                    errors.append("Missing documentation link: " + str(name.relative_to(root)) + " -> " + target)
        if inside:
            errors.append("Unclosed code fence: " + str(name.relative_to(root)))
    for directory in ("src", "scripts", "tests", "examples"):
        for name in (root / directory).rglob("*.py"):
            try:
                ast.parse(name.read_text(encoding="utf-8"))
            except SyntaxError:
                errors.append("Invalid Python source: " + str(name.relative_to(root)))
    zh = (root / "README.md").read_text(encoding="utf-8")
    en = (root / "README.en.md").read_text(encoding="utf-8")
    if "中文 | [English](README.en.md)" not in zh or "[中文](README.md) | English" not in en:
        errors.append("Missing reciprocal README language links")
    commands = lambda text: re.findall(r"```(?:shell|powershell|bash)\n(.*?)\n```", text, re.S)
    if commands(zh) != commands(en):
        errors.append("README development commands differ")
    return {"status": "BOOTSTRAP_VALIDATED" if not errors else "INCOMPLETE", "errors": errors,
            "sourceFiles": len(source["files"]), "algorithms": len(ledger["algorithms"]),
            "options": len(ledger["options"]), "categories": len(ledger["categories"]),
            "markdownFiles": len(markdown), "pythonAlgorithmsVerified": 0,
            "limitation": "Structure/provenance denominator checks only; no Python layout or release acceptance."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = check()
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(text)
    print(text, end="")
    raise SystemExit(bool(result["errors"]))


if __name__ == "__main__":
    main()
