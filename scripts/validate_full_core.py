"""Batch formal public API checks against saved, individually captured upstream calls.

Every run owns a new output directory. Raw strict comparisons are retained alongside
the explicit generated-owned-hash adaptation; business/user hashes are never removed.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import math
import subprocess
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import diff
from pyelk import ELK

FIXTURES = ROOT / "tests/fixtures/suites/next-native"
RUNS = ROOT / "test-runs"
SAVED_CASES = [
    ("ordinary-nested", "recursive-ordinary-nested-request.json", "20261104-HOST-11/V/recursive-ordinary-nested-oracle-01/observation.json"),
    ("topdown", "recursive-topdown-request.json", "20261104-HOST-11/V/recursive-topdown-oracle-01/observation.json"),
    ("sharedpool-fixed", "recursive-sharedpool-fixed-request.json", "20261104-HOST-11/V/recursive-sharedpool-fixed-oracle-01/observation.json"),
    ("selected-core", "recursive-selected-core-request.json", "20261104-HOST-12/root/recursive-selected-core-original-01/observation.json"),
    ("selected-layered", "recursive-selected-layered-request.json", "20261104-HOST-12/root/recursive-selected-layered-original-01/observation.json"),
    ("global-box", "recursive-global-box-request.json", "20261104-HOST-13/root/recursive-global-box-original-02/observation.json"),
]
TRANSFER_CASES = [("json-transfer-" + name, "json-transfer/" + name + ".json",
                   "20261104-next-native-01/V/json-transfer-reference-03/" + name + "/observation.json")
                  for name in ("default-inherit", "root-root", "root-parent", "parent-container")]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text("utf-8"))


def write(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)


def projected_reference(original, reference, candidate):
    """Only actual owned original objects can lose generated integer identity hashes."""
    projected = copy.deepcopy(reference)
    adaptations = []
    violations = []
    pending = [(original, projected, candidate, "", "node")]
    while pending:
        source, expected, actual, path, kind = pending.pop()
        if not all(type(value) is dict for value in (source, expected, actual)):
            violations.append({"path": path, "reason": "owned object shape mismatch"})
            continue
        if source.get("id") != expected.get("id") or expected.get("id") != actual.get("id"):
            violations.append({"path": path, "reason": "owned identifier mismatch"})
            continue
        if "$H" in expected and "$H" not in source and "$H" not in actual:
            value = expected["$H"]
            if type(value) is not int:
                violations.append({"path": path + "/$H", "reason": "generated hash is not an integer"})
            else:
                del expected["$H"]
                adaptations.append({"path": path + "/$H", "referenceValue": value})
        groups = ("labels", "ports", "children", "edges") if kind == "node" else ("labels",) if kind in ("port", "edge") else ()
        for group in groups:
            inputs, outputs, natives = source.get(group, []), expected.get(group, []), actual.get(group, [])
            if not all(type(value) is list for value in (inputs, outputs, natives)) or not len(inputs) == len(outputs) == len(natives):
                violations.append({"path": path + "/" + group, "reason": "owned collection shape mismatch"})
                continue
            child_kind = {"children": "node", "ports": "port", "edges": "edge", "labels": "label"}[group]
            for index, child in enumerate(inputs):
                pending.append((child, outputs[index], natives[index], path + "/" + group + "/" + str(index), child_kind))
    return projected, adaptations, violations


async def saved_case(case_id, request_path, oracle_path, out):
    request = load(request_path)
    oracle = load(oracle_path)
    if sha(request_path) != oracle["requestSha256"]:
        raise ValueError("Saved source request hash mismatch: " + case_id)
    graph = request.get("graph", request)
    before = copy.deepcopy(graph)
    stock = oracle.get("schema") == "py-elk-layout-observation/v1"
    if stock:
        assert oracle["outcome"] == "returned"
        assert oracle["engine"]["version"] == "0.12.1"
        assert oracle["engine"]["entrypointSha256"] == "b1032b7cfd2a57c54c6f0e8369d7665e19a579954f7cd20a6dae28f1912ea0d7"
    observation = oracle if stock else oracle["observation"]
    expected = observation["result"]
    constructor = request.get("constructor", {"algorithms": request["algorithms"]} if "algorithms" in request else None)
    elk = ELK(constructor)
    start = time.perf_counter()
    result = {"id": case_id, "request": str(request_path.relative_to(ROOT)), "requestSha256": sha(request_path),
              "oracle": str(oracle_path.relative_to(ROOT)), "oracleSha256": sha(oracle_path),
              "workerSha256": oracle.get("workerSha256"), "publicAPI": True}
    try:
        arguments = request.get("layoutArguments", {"layoutOptions": request["globalOptions"]} if "globalOptions" in request else None)
        actual = await elk.layout(graph, arguments)
        result["actual"] = actual
        result["rawComparison"] = diff(expected, actual, tolerant=False)
        projected, adaptations, violations = projected_reference(before, expected, actual)
        result["ownedHashProjection"] = {"adaptations": adaptations, "violations": violations}
        result["comparison"] = diff(projected, actual, tolerant=False)
        result["inputPreserved"] = diff(before, graph, tolerant=False)
        if "metadata" in observation:
            actual_metadata = {"algorithms": await elk.knownLayoutAlgorithms(), "options": await elk.knownLayoutOptions(),
                               "categories": await elk.knownLayoutCategories()}
            result["actualMetadata"] = actual_metadata
            result["metadataComparison"] = diff(observation["metadata"], actual_metadata, tolerant=False)
        result["trace"] = elk.last_trace
        result["passed"] = all(result[key]["passed"] for key in ("comparison", "inputPreserved")) and not violations
        if "metadataComparison" in result:
            result["passed"] = result["passed"] and result["metadataComparison"]["passed"]
    except Exception as error:
        result.update(passed=False, exception={"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()})
    finally:
        result["elapsedSeconds"] = time.perf_counter() - start
        elk.close()
    write(out / (case_id + ".json"), result)
    print(json.dumps({"case": case_id, "passed": result["passed"], "elapsedSeconds": result["elapsedSeconds"],
                      "diffs": len(result.get("comparison", {}).get("differences", [])), "exception": result.get("exception", {}).get("message")}), flush=True)
    return result


def checker_controls():
    source = {"id": "r", "business": {"$H": 7}, "children": [{"id": "c", "$H": 3}]}
    reference = copy.deepcopy(source)
    reference["$H"] = 11
    candidate = copy.deepcopy(source)
    projected, adaptations, violations = projected_reference(source, reference, candidate)
    assert diff(projected, candidate, tolerant=False)["passed"] and len(adaptations) == 1 and not violations
    candidate["business"]["$H"] = 8
    assert not diff(projected, candidate, tolerant=False)["passed"]
    assert not diff(False, 0, tolerant=False)["passed"]
    candidate = copy.deepcopy(source)
    candidate["children"][0]["id"] = "wrong"
    assert projected_reference(source, reference, candidate)[2]
    return {"booleanNumberDistinct": True, "businessHashRetained": True, "userHashRetained": True, "ownedIdentifiersRequired": True}


def catalogue_validation(out):
    """One complete declaration sweep plus adversarial family inputs, actual source first."""
    from pyelk.options.generic import RUNTIME_PROPERTY_SPECS
    from pyelk.execution.local_properties import _parse_text, _SKIP
    from pyelk.execution.metadata_service import NativeMetadataService
    specs = RUNTIME_PROPERTY_SPECS
    cases = []
    for canonical, spec in specs.items():
        kind = spec.kind
        text = {"string": "test value", "boolean": "TRUE", "integer": "129", "signed_number": "-1.25e2",
                "vector": "(-0,2)", "vector_chain": "(1,2;3,4;5)", "insets": "[top=1,left=-0,bottom=3,right=4]",
                "individual_spacings": "org.eclipse.elk.spacing.nodeNode:7", "opaque": "test value"}.get(kind)
        if kind == "enum_ordinal": text = spec.accepted_values[-1]
        if kind == "enumset": text = ",".join(spec.accepted_values[::2])
        assert text is not None, (canonical, kind)
        cases.append({"id": canonical + ":valid", "option": canonical, "kind": kind, "text": text})
    families = {"boolean": ["false", "True", "1", " false", "null", ""],
                "integer": ["+0", "-2147483648", "2147483647", "2147483648", " 1", "1.0", "-0", "1e2"],
                "signed_number": ["NaN", "Infinity", "-Infinity", "-0", " 1.5D ", "1e999", "0x1p2", "1f", ".5", "+.5"],
                "enum_ordinal": ["0", "-1", "2147483647", " 0", "invalid", "null", ""],
                "enumset": ["", "0,0", "[]", "[0, 1]", "-1", "invalid", "null"],
                "vector": ["(1)", "(1,2,3)", "(NaN,Infinity)", " 1;2 ", "(-0,-0)", "(1,2d)"],
                "vector_chain": ["", "()", "(1,2,invalid)", "(1,2,3)", "(NaN,Infinity)", "1\r2"],
                "insets": ["", "0", "[left=2;right=3]", "[unknown=4,top=1]", "[left=NaN]", "[top=1=2]"],
                "string": ["null", "", "NULL", "  "],
                "individual_spacings": ["", "unknown:7", "org.eclipse.elk.spacing.nodeNode:NaN"]}
    for kind, texts in families.items():
        canonical = next(key for key, spec in specs.items() if spec.kind == kind)
        for index, text in enumerate(texts):
            cases.append({"id": canonical + ":edge:" + str(index), "option": canonical, "kind": kind, "text": text})
    request_path = out / "catalogue-request.json"
    write(request_path, {"cases": cases})
    probe = ROOT / "tests/fixtures/suites/full-native-core/property-catalogue-probe.cjs"
    write(out / "catalogue-input-provenance.json", {"inputOnlyGeneratedFromDeclarations": True,
          "declarationFiles": {str(path.relative_to(ROOT)): sha(path) for path in (ROOT / "src/pyelk/options/_generic_data.py", ROOT / "src/pyelk/options/_object_data.py")},
          "distinctOptions": len(specs), "caseCount": len(cases)})
    (out / "catalogue-probe-executed.cjs").write_bytes(probe.read_bytes())
    source_path = out / "catalogue-original.json"
    command = [r"C:\Program Files\nodejs\node.exe", str(probe), str(ROOT / ".local/npm-elkjs/package"), str(request_path), str(source_path)]
    start = time.perf_counter()
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(timeout=60)
    (out / "catalogue-source-stdout.log").write_bytes(stdout)
    (out / "catalogue-source-stderr.log").write_bytes(stderr)
    write(out / "catalogue-source-command.json", {"argv": command, "pid": process.pid, "exitCode": process.returncode, "elapsedSeconds": time.perf_counter() - start})
    if process.returncode: raise RuntimeError(stderr.decode(errors="replace"))
    oracle = load(source_path)
    assert oracle["requestSha256"] == sha(request_path) and oracle["probeSha256"] == sha(probe)
    metadata = NativeMetadataService()

    def number(value):
        if type(value) is float:
            if math.isnan(value): return {"number": "NaN"}
            if math.isinf(value): return {"number": "Infinity" if value > 0 else "-Infinity"}
            if value == 0 and math.copysign(1, value) < 0: return {"number": "-0"}
        return value

    def normalize(value, kind):
        if value is _SKIP: return None
        if kind == "vector": return {"x": number(value.x), "y": number(value.y)}
        if kind == "vector_chain": return [{"x": number(point.x), "y": number(point.y)} for point in value.points]
        if kind == "insets": return {key: number(getattr(value, key)) for key in ("top", "right", "bottom", "left")}
        if kind == "enumset": return sorted(value)
        if kind == "individual_spacings": return {"nodeNode": number(value.get("org.eclipse.elk.spacing.nodeNode"))}
        return number(value)

    actual = []
    errors = []
    for case in cases:
        try:
            value = _parse_text(specs[case["option"]], case["text"], "/layoutOptions/" + case["option"], metadata)
            row = {"id": case["id"], "option": case["option"], "outcome": "returned", "value": normalize(value, case["kind"])}
        except Exception as error:
            row = {"id": case["id"], "option": case["option"], "outcome": "threw", "error": {"name": type(error).__name__, "message": str(error)}}
        actual.append(row)
    # Preserve exception-class boundary explicitly, rather than silently mapping runtime errors.
    comparison = diff(oracle["observation"], actual, tolerant=False)
    report = {"passed": comparison["passed"], "comparison": comparison, "actual": actual,
              "oracleSha256": sha(source_path), "distinctOptions": len(specs), "caseCount": len(cases),
              "layoutExecuted": False, "publicAPI": False, "scope": "Actual metadata parseValue versus native source-local parser; all243 declarations"}
    write(out / "catalogue-comparison.json", report)
    print(json.dumps({"cataloguePassed": comparison["passed"], "cases": len(cases), "differences": len(comparison["differences"])}), flush=True)
    return report


def catalogue_observer_recheck(previous, out):
    """Correct only the source observer's seven Insets records, no native replay."""
    before = load(previous / "catalogue-comparison.json")
    original = load(previous / "catalogue-original.json")
    request = load(previous / "catalogue-request.json")
    affected = [case for case, row in zip(request["cases"], original["observation"], strict=True)
                if case["kind"] == "insets" and row["outcome"] == "returned" and row["value"] is not None]
    request_path = out / "catalogue-request.json"
    write(request_path, {"cases": affected})
    probe = ROOT / "tests/fixtures/suites/full-native-core/property-catalogue-probe.cjs"
    (out / "catalogue-probe-executed.cjs").write_bytes(probe.read_bytes())
    source_path = out / "catalogue-original.json"
    command = [r"C:\Program Files\nodejs\node.exe", str(probe), str(ROOT / ".local/npm-elkjs/package"), str(request_path), str(source_path)]
    start = time.perf_counter()
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(timeout=60)
    (out / "stdout.log").write_bytes(stdout)
    (out / "stderr.log").write_bytes(stderr)
    write(out / "command.json", {"argv": command, "pid": process.pid, "exitCode": process.returncode, "elapsedSeconds": time.perf_counter() - start})
    if process.returncode: raise RuntimeError(stderr.decode(errors="replace"))
    correction = load(source_path)
    assert correction["requestSha256"] == sha(request_path) and correction["probeSha256"] == sha(probe)
    rows = {row["id"]: row for row in correction["observation"]}
    assert set(rows) == {case["id"] for case in affected}
    expected = [rows.get(row["id"], row) for row in original["observation"]]
    raw = diff(expected, before["actual"], tolerant=False)
    values = diff([row for row in expected if row["outcome"] == "returned"],
                  [row for row in before["actual"] if row["outcome"] == "returned"], tolerant=False)
    error_messages = diff([{key: value for key, value in row.items() if key != "error"} | {"message": row["error"]["message"]}
                           for row in expected if row["outcome"] == "threw"],
                          [{key: value for key, value in row.items() if key != "error"} | {"message": row["error"]["message"]}
                           for row in before["actual"] if row["outcome"] == "threw"], tolerant=False)
    report = {"rawPassed": raw["passed"], "rawComparison": raw, "valueComparison": values,
              "errorOutcomeAndMessageComparison": error_messages,
              "nativeCasesReplayed": 0, "correctedSourceCases": len(affected), "distinctOptions": before["distinctOptions"],
              "caseCount": before["caseCount"], "previousRawDifferencesRetained": len(before["comparison"]["differences"]),
              "originalSha256": sha(previous / "catalogue-original.json"), "firstNativeSha256": sha(previous / "catalogue-comparison.json"),
              "correctionSha256": sha(source_path), "exceptionBoundary": "8 unavailable raw factories: upstream Error vs native RuntimeError; messages exact; raw class differences remain open"}
    write(out / "report.json", report)
    print(json.dumps({"valuesPassed": values["passed"], "errorsOutcomeMessagePassed": error_messages["passed"], "rawDifferences": len(raw["differences"]), "correctedSourceCases": len(affected)}), flush=True)
    return report


def typed_saved_validation(out):
    """Run integrated property/metadata witnesses against formal source, in fresh processes."""
    tasks = [
        ("scalar-parser", "compare_generic_scalars.py", "generic-scalar-request.json", "20261104-SCHEMAS-07/root/scalar-original-02/observation.json", []),
        ("object-parser-clone", "compare_object_properties.py", "object-properties-request.json", "20261104-HOST-08/root/object-original-01/observation.json", []),
        ("typed-snapshot", "compare_property_snapshot.py", "property-snapshot-request.json", "20261104-HOST-08/root/snapshot-original-01/observation.json", []),
        ("snapshot-owner-defaults", "compare_snapshot_default.py", None, "20261104-HOST-09/root/snapshot-default-original-01/observation.json", []),
        ("selected-global-targets", "compare_generic_targets.py", "generic-targets-request.json", "20261104-HOST-08/V/generic-targets-oracle-01/observation.json", []),
        ("integer-provenance", "compare_integer_provenance.py", "integer-provenance-request.json", "20261104-HOST-09/root/integer-original-02/observation.json", []),
        ("metadata-registration", "compare_metadata_registration.py", "metadata-registration-request.json", "20261104-HOST-12/root/metadata-registration-original-01/observation.json", []),
        ("global-json-config", "compare_global_options.py", "global-options-request.json", "20261104-HOST-13/root/global-options-original-01/oracle.json", [str(RUNS / "20261104-HOST-13/root/global-options-original-02/oracle.json")]),
    ]
    results = []
    for name, checker_name, request, oracle, extra in tasks:
        target = out / name
        target.mkdir()
        checker = FIXTURES / checker_name
        (target / "checker-executed.py").write_bytes(checker.read_bytes())
        command = [sys.executable, str(checker), str(ROOT / "src")]
        if request: command.append(str(FIXTURES / request))
        command += [str(RUNS / oracle), str(target / "comparison.json"), *extra]
        start = time.perf_counter()
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=60)
        (target / "stdout.log").write_bytes(stdout)
        (target / "stderr.log").write_bytes(stderr)
        row = {"id": name, "argv": command, "pid": process.pid, "exitCode": process.returncode,
               "elapsedSeconds": time.perf_counter() - start, "passed": process.returncode == 0,
               "checkerSha256": sha(checker), "oracleSha256": sha(RUNS / oracle), "publicAPI": False, "formalSource": True}
        write(target / "command.json", row)
        results.append(row)
        print(json.dumps({"typedWitness": name, "passed": row["passed"], "stderr": stderr.decode(errors="replace")[-1200:]}), flush=True)
    report = {"passed": all(row["passed"] for row in results), "cases": results,
              "scope": "Formal integrated native properties; saved original witnesses; public calls separately captured",
              "referenceProcessesExecuted": 0}
    write(out / "report.json", report)
    return report


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--catalogue", action="store_true")
    parser.add_argument("--catalogue-observer-recheck", type=Path)
    parser.add_argument("--typed", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    files = {str(path.relative_to(ROOT)): sha(path) for path in sorted((ROOT / "src/pyelk").rglob("*.py"))}
    write(args.out / "source-manifest.json", files)
    controls = checker_controls()
    if args.typed:
        report = typed_saved_validation(args.out)
        return 0 if report["passed"] else 1
    if args.catalogue_observer_recheck:
        report = catalogue_observer_recheck(args.catalogue_observer_recheck, args.out)
        return 0 if report["valueComparison"]["passed"] and report["errorOutcomeAndMessageComparison"]["passed"] else 1
    if args.catalogue:
        report = catalogue_validation(args.out)
        return 0 if report["passed"] else 1
    cases = [case for case in SAVED_CASES + TRANSFER_CASES if not args.case or case[0] in args.case]
    if not cases:
        raise ValueError("No selected cases")
    results = []
    for case_id, request, oracle in cases:
        results.append(await saved_case(case_id, FIXTURES / request, RUNS / oracle, args.out))
    report = {"schema": "pyelk-full-core-validation/v1", "pid": os.getpid(), "python": sys.executable,
              "checkerSha256": sha(Path(__file__)), "sourceFiles": len(files), "controls": controls,
              "passed": all(result["passed"] for result in results), "caseCount": len(results),
              "passedCount": sum(result["passed"] for result in results),
              "cases": [{key: result[key] for key in ("id", "passed", "elapsedSeconds")} for result in results],
              "coverage": ["formal ELK public process worker calls", "recursive/topdown/shared registry paths", "selected registry metadata", "global option application", "complete caller input preservation"],
              "notCovered": ["all 243 option value combinations", "all malformed inputs", "deep hierarchy", "full API scheduling and lifecycle"]}
    write(args.out / "report.json", report)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
