"""Validate E03 host foundations and provenance, never layout coordinates."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys

from layout_checks import ROOT, contained, diff, load, sha256, write
from validate_e01_audit import check_plan

sys.path.insert(0, str(ROOT / "src"))

COMPONENTS = {
    "json-copy": ("pyelk._json", "clone_json"),
    "host-errors": ("pyelk._errors", "ValidationError"),
    "typed-id": ("pyelk.model", "TypedId"),
    "ordered-graph": ("pyelk.model", "Graph"),
    "node": ("pyelk.model", "Node"),
    "port": ("pyelk.model", "Port"),
    "edge": ("pyelk.model", "Edge"),
    "anchor": ("pyelk.model", "Anchor"),
    "margin": ("pyelk.model", "Margin"),
    "option-schema": ("pyelk.options", "OPTION_SPECS"),
    "option-resolution": ("pyelk.options", "resolve_options"),
    "per-call-context": ("pyelk.execution", "ExecutionContext"),
}
RUNTIME_CLAIMS = {"internalModelAvailable": True, "optionResolverAvailable": True,
                  "perCallContextAvailable": True, "nativeLayoutImplemented": False,
                  "publicLayoutApiAccepted": False, "lifecycleAccepted": False,
                  "concurrencyAccepted": False, "cancellationAccepted": False,
                  "randomSequenceAccepted": False}
MODEL_SOURCES = {
    "elkjs-json-adapter": ("src/java-additional/org/eclipse/elk/graph/json/JsonAdapter.xtend", "locked-git-source"),
    "elkjs-generated-json-importer": ("lib/elk-worker.js", "locked-git-source"),
}
OPTION_SOURCES = {"elk-worker": ("lib/elk-worker.js", "locked-npm-generated-code"),
                  "elk-api": ("src/js/elk-api.js", "locked-git-source"),
                  "official-option-catalogue": ("references/metadata/options.json", "captured-official-metadata")}
MODEL_CLAIMS = {"M-SOURCE-01": ("fixed-source-behavior", ["elkjs-json-adapter", "elkjs-generated-json-importer"]),
                "M-SOURCE-02": ("fixed-source-behavior", ["elkjs-generated-json-importer"]),
                **{f"M-HOST-{index:02}": ("host-design", []) for index in range(1, 8)}}
OPTION_CLAIMS = {
    "defaults-nine": ("fixed-source-behavior", ["elk-worker", "official-option-catalogue"]),
    "call-replaces-constructor": ("fixed-source-behavior", ["elk-api"]),
    "local-over-selected-global": ("fixed-source-behavior", ["elk-worker"]),
    "algorithm-default-vs-fallback": ("fixed-source-behavior", ["elk-worker"]),
    "direction-not-right-default": ("fixed-source-behavior", ["elk-worker"]),
    "reference-parser-is-wider": ("fixed-source-behavior", ["elk-worker"]),
    "strict-host-subset": ("host-design", ["elk-api", "elk-worker"]),
    "catalogue-not-registry": ("host-design", ["official-option-catalogue"]),
    "per-call-ownership": ("host-design", ["elk-api"]),
}
DECLARED_DEFAULTS = {
    "org.eclipse.elk.algorithm": None, "org.eclipse.elk.direction": "UNDEFINED",
    "org.eclipse.elk.padding": {"top": 12, "right": 12, "bottom": 12, "left": 12},
    "org.eclipse.elk.spacing.nodeNode": 20, "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": 20,
    "org.eclipse.elk.separateConnectedComponents": True, "org.eclipse.elk.spacing.componentComponent": 20,
    "org.eclipse.elk.edgeRouting": "ORTHOGONAL", "org.eclipse.elk.randomSeed": 1,
}
PARSING_POLICY = {"spacing": "finite nonnegative int/float or decimal string, bool rejected",
    "seed": "signed 32-bit int or integer string, bool/float rejected; zero retained without determinism claim",
    "boolean": "bool or case-insensitive true/false string",
    "padding": "all four top/right/bottom/left sides, mapping or bracketed comma key=value string; no missing/duplicate/unknown side",
    "enum": "explicit supported names only, no ordinal or case coercion",
    "algorithm": "layered or org.eclipse.elk.layered parsed selection only", "routing": "ORTHOGONAL only"}


def validate_option_receipts(document):
    options = document["options"]
    indexed = {item["id"]: item for item in options}
    if len(indexed) != len(options) or set(indexed) != set(DECLARED_DEFAULTS):
        raise ValueError("E03 nine option receipts cannot disappear or duplicate")
    metadata = {item["id"]: item for item in load(ROOT / "references/metadata/options.json")}
    for identity, default in DECLARED_DEFAULTS.items():
        expected = {"id": identity, "alias": identity.replace("org.eclipse.elk.", "elk.", 1),
                    "declaredDefault": default, "metadataType": metadata[identity]["type"],
                    "targets": metadata[identity]["targets"], "sourceIds": ["elk-worker", "official-option-catalogue"],
                    "status": "host-parser-schema-only", "layoutImplemented": False}
        if not diff(indexed[identity], expected)["passed"]:
            raise ValueError("E03 option receipt/default/type/scope claim differs: " + identity)
    design = {"path": "docs/decisions/0002-model-options-context.md", "revision": 1, "status": "frozen-design",
              "algorithmFallbackOrigin": "layout-fallback", "directionRemains": "UNDEFINED", "parsing": PARSING_POLICY}
    if type(document["design"]["revision"]) is not int or not diff(document["design"], design)["passed"]:
        raise ValueError("E03 host parsing design differs from frozen decision")


def validate_sources(document, lock, schema):
    if document["schema"] != schema or document["baseline"] != {"version": lock["javascript"]["version"], "commit": lock["javascript"]["commit"]}:
        raise ValueError("E03 source schema/baseline differs")
    if (type(document["pythonAlgorithmsVerified"]) is not int or document["pythonAlgorithmsVerified"] != 0
            or document["nativeLayoutImplemented"] is not False or document["algorithmSourceGate"] != "unverified"):
        raise ValueError("Host source evidence cannot certify layout or algorithm provenance")
    is_options = schema == "py-elk-e03-option-sources/v1"
    expected_sources = OPTION_SOURCES if is_options else MODEL_SOURCES
    expected_claims = OPTION_CLAIMS if is_options else MODEL_CLAIMS
    sources = document["sources"]
    if len({item["sourceId"] for item in sources}) != len(sources) or {item["sourceId"] for item in sources} != set(expected_sources):
        raise ValueError("E03 source evidence must be nonempty and unique")
    captured = lock["metadataCapture"]["files"]
    known = {**lock["sourceSha256"], **lock["distribution"]["sha256Files"], **captured}
    for source in sources:
        path, kind = expected_sources[source["sourceId"]]
        if source["path"] != path or source.get("kind", "locked-git-source") != kind:
            raise ValueError("E03 source role/path/kind differs: " + source["sourceId"])
        if source["commit"] != lock["javascript"]["commit"] or known.get(source["path"]) != source["sha256"]:
            raise ValueError("E03 canonical source identity differs: " + source["sourceId"])
        if (source["path"] in captured) != (source.get("kind") == "captured-official-metadata"):
            raise ValueError("E03 captured metadata must not masquerade as a canonical Git source")
        if not source["lineRanges"]:
            raise ValueError("E03 source requires line ranges")
        for span in source["lineRanges"]:
            if (type(span["startLine"]) is not int or type(span["endLine"]) is not int
                    or not 1 <= span["startLine"] <= span["endLine"]):
                raise ValueError("E03 source range is invalid")
    claims = document["claims"]
    if len({item["id"] for item in claims}) != len(claims) or {item["id"] for item in claims} != set(expected_claims):
        raise ValueError("E03 claim evidence must be nonempty and unique")
    source_ids = {item["sourceId"] for item in sources}
    kinds = set()
    for claim in claims:
        if set(claim) != {"id", "kind", "sourceIds", "description"}:
            raise ValueError("E03 claims must use the explicit source/host schema")
        kinds.add(claim["kind"])
        if claim["kind"] not in ("host-design", "fixed-source-behavior") or type(claim["description"]) is not str or not claim["description"].strip():
            raise ValueError("E03 must distinguish host design from fixed-source behavior")
        if (type(claim["sourceIds"]) is not list or not all(type(identity) is str for identity in claim["sourceIds"])
                or not set(claim["sourceIds"]) <= source_ids
                or len(set(claim["sourceIds"])) != len(claim["sourceIds"])
                or (claim["kind"] == "fixed-source-behavior" and not claim["sourceIds"])):
            raise ValueError("E03 source claim references are invalid")
        kind, identities = expected_claims[claim["id"]]
        if claim["kind"] != kind or claim["sourceIds"] != identities:
            raise ValueError("E03 claim role or exact source binding differs")
    if kinds != {"host-design", "fixed-source-behavior"}:
        raise ValueError("E03 host decisions and source facts must both remain explicit")
    if is_options:
        validate_option_receipts(document)
    elif (document["status"] != "sealed-source-and-host-design"
          or document["designDocument"] != "docs/decisions/0002-model-options-context.md"):
        raise ValueError("E03 model evidence seal or decision binding differs")


def validate_manifest(manifest, lock):
    if manifest["schema"] != "py-elk-e03-audit/v1" or manifest["status"] != "FOUNDATIONS_VALIDATED":
        raise ValueError("E03 foundations audit is incomplete")
    if manifest["baseline"] != {"version": lock["javascript"]["version"], "commit": lock["javascript"]["commit"]}:
        raise ValueError("E03 audit baseline differs")
    if (not diff(manifest["runtimeClaims"], RUNTIME_CLAIMS)["passed"]
            or type(manifest["pythonAlgorithmsVerified"]) is not int or manifest["pythonAlgorithmsVerified"] != 0
            or manifest["algorithmSourceGate"] != "unverified"):
        raise ValueError("E03 host acceptance cannot promote algorithm/API/lifecycle acceptance")
    components = manifest["components"]
    indexed = {item["id"]: item for item in components}
    if len(indexed) != len(components) or set(indexed) != set(COMPONENTS):
        raise ValueError("E03 component denominator differs")
    for identity, (module, symbol) in COMPONENTS.items():
        item = indexed[identity]
        if (item["module"] != module or item["symbol"] != symbol
                or item["kind"] != "host-data-foundation" or item["implemented"] is not True
                or item["layoutAlgorithm"] is not False):
            raise ValueError("E03 component kind/symbol differs: " + identity)
    policy = {"typedStringAndIntegerIds": True, "booleanOrFloatIds": False, "nodesIncludeRoot": True,
              "inputAndExportCopies": "deep-exact", "coreOptionCount": 9, "diagnosticOptionCount": 243,
              "optionReplacement": "call presence replaces constructor; local overrides selected global",
              "directionDefault": "UNDEFINED", "runtimeReadsReferences": False,
              "geometryAndLayoutAccepted": False, "rawStrictContractPreserved": True}
    if not diff(manifest["policy"], policy)["passed"]:
        raise ValueError("E03 audit hides model/options/runtime boundaries")


def runtime_controls():
    """Run real Python model/resolver/context code; no layout is requested."""
    from pyelk._errors import ValidationError
    from pyelk.execution import create_context
    from pyelk.model import Graph
    from pyelk.options import KNOWN_OPTION_IDS, OPTION_SPECS, resolve_options

    expected_options = set(load(ROOT / "docs/release-profiles.json")["profiles"][0]["options"])
    if set(OPTION_SPECS) != expected_options or set(KNOWN_OPTION_IDS) != {item["id"] for item in load(ROOT / "references/metadata/options.json")}:
        raise ValueError("Runtime parsing schema/diagnostic catalogue differs from its explicit denominator")
    original = {"id": "root", "business": {"$H": False, "error": {"stack": "caller"}, "null": None},
                "children": [{"id": 1, "width": 20, "height": 10}, {"id": "1", "width": 30, "height": 10}],
                "edges": [{"id": "e", "sources": [1], "targets": ["1"]}]}
    graph = Graph.from_json(original)
    if not diff(graph.to_json(), original)["passed"] or graph.node(1) is graph.node("1"):
        raise ValueError("Typed identity or lossless round-trip failed")
    constructor = {"defaultLayoutOptions": {"elk.direction": "LEFT"}}
    arguments = {"layoutOptions": {}, "logging": False}
    first = create_context(original, constructor=constructor, layout_arguments=arguments)
    second = create_context(original, constructor=constructor, layout_arguments=arguments)
    first.working_graph.node(1).set_property("x", 37)
    first.state["scratch"] = [1]
    snapshot = first.original_graph
    snapshot["business"]["error"]["stack"] = "edited export"
    if (not diff(first.original_graph, original)["passed"] or not diff(second.working_graph.to_json(), original)["passed"]
            or second.state or not diff(first.original_constructor, constructor)["passed"]
            or not diff(first.original_arguments, arguments)["passed"]):
        raise ValueError("Cross-call ownership or snapshot preservation failed")
    defaults = resolve_options()
    if defaults.values["org.eclipse.elk.direction"] != "UNDEFINED" or defaults.values["org.eclipse.elk.randomSeed"] != 1:
        raise ValueError("Declared defaults were replaced by fixture values or inferred direction")
    if first.resolved_options.values["org.eclipse.elk.direction"] != "UNDEFINED":
        raise ValueError("Explicit empty call options did not replace constructor defaults")
    cases = load(ROOT / "tests/fixtures/validation/cases.json")
    records = []
    for case in cases["cases"]:
        request = load(contained(ROOT / "tests/fixtures/validation", case["request"]))
        try:
            context = create_context(request["graph"], constructor=request["constructor"], layout_arguments=request["layoutArguments"])
            if not diff(context.working_graph.to_json(), request["graph"])["passed"]:
                raise ValueError("Model altered request fields: " + case["id"])
            accepted, category = True, None
        except ValidationError as error:
            accepted, category = False, error.code
        if accepted != (case["expectedOutcome"] == "returned"):
            raise ValueError("Host input classification differs for saved request: " + case["id"])
        records.append({"id": case["id"], "hostInputAccepted": accepted, "hostErrorCode": category, "layoutExecuted": False})
    return {"status": "HOST_FOUNDATION_CONTROLS_PASS", "fixtureRequestsChecked": len(records), "cases": records,
            "pythonAlgorithmsVerified": 0, "layoutExecuted": False, "randomSequenceAccepted": False}


def historical_controls():
    """Authenticate original implementation bytes without executing old code.

    The E03 nine-schema proof is a historical boundary. It must not be applied
    to the later expanded runtime registry or rebound to its implementation.
    """
    from iteration.e11_history import material
    original = material(ROOT)
    package = {name: raw for name, raw in original.items() if name.startswith("src/pyelk/")}
    python = {name: raw for name, raw in package.items() if name.endswith(".py")}
    if len(package) != 43 or len(python) != 35:
        raise ValueError("Historical foundation product denominator differs")
    symbols = []
    for module, symbol in COMPONENTS.values():
        stem = "src/" + module.replace(".", "/")
        name = stem + ".py" if stem + ".py" in python else stem + "/__init__.py"
        tree = ast.parse(python[name], filename=name)
        defined = {node.name for node in ast.walk(tree)
                   if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                defined.update(alias.asname or alias.name for alias in node.names)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                defined.add(node.id)
        if symbol not in defined:
            raise ValueError("Historical foundation symbol missing: " + module + "." + symbol)
        symbols.append(module + "." + symbol)
    return {"status": "HISTORICAL_FOUNDATION_BYTES_VALIDATED", "historicalPackageFiles": len(package),
            "historicalPythonModules": len(python), "historicalSymbols": symbols,
            "currentPackageBytesValidated": False, "runtimeReexecuted": False,
            "layoutExecuted": False, "pythonAlgorithmsVerified": 0}


def check(*, with_upstream=False, historical=False):
    errors, controls = [], None
    try:
        errors.extend(check_plan(ROOT))
        lock = load(ROOT / "UPSTREAM.json")
        files = {"references/e03-model-sources.json": "py-elk-e03-model-sources/v1",
                 "references/e03-option-sources.json": "py-elk-e03-option-sources/v1"}
        documents = []
        for path, schema in files.items():
            document = load(ROOT / path)
            validate_sources(document, lock, schema)
            documents.append(document)
            for source in document["sources"]:
                if source.get("kind") == "captured-official-metadata" and sha256(contained(ROOT, source["path"])) != source["sha256"]:
                    raise ValueError("E03 captured metadata bytes differ from fixed receipt")
        manifest = load(ROOT / "references/e03-audit.json")
        validate_manifest(manifest, lock)
        required = {*files, "docs/decisions/0002-model-options-context.md"}
        if set(manifest["filesSha256"]) != required:
            raise ValueError("E03 frozen evidence denominator differs")
        for path, digest in manifest["filesSha256"].items():
            if sha256(contained(ROOT, path)) != digest:
                raise ValueError("E03 frozen evidence SHA differs: " + path)
        if historical:
            controls = historical_controls()
        else:
            for module_name, symbol in COMPONENTS.values():
                value = getattr(importlib.import_module(module_name), symbol)
                if symbol != "OPTION_SPECS":
                    source = inspect.getsourcefile(value)
                    if not source or not Path(source).resolve().is_relative_to(ROOT / "src/pyelk"):
                        raise ValueError("E03 component is not implemented in the local Python package")
            controls = runtime_controls()
        if with_upstream:
            import upstream
            checkout = ROOT / ".local/upstream-elkjs"
            upstream.verify_source(checkout, lock)
            upstream.verify_package(ROOT / ".local/npm-elkjs/package", lock)
            for document in documents:
                for source in document["sources"]:
                    raw = (contained(ROOT, source["path"]).read_bytes() if source.get("kind") == "captured-official-metadata"
                           else upstream.git(checkout, "show", source["commit"] + ":" + source["path"]))
                    if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                        raise ValueError("E03 canonical Git source bytes differ")
                    lines = raw.decode("utf-8").splitlines()
                    for span in source["lineRanges"]:
                        if span["endLine"] > len(lines):
                            raise ValueError("E03 source range exceeds canonical file")
                        if "spanSha256" in span:
                            block = ("\n".join(lines[span["startLine"] - 1:span["endLine"]]) + "\n").encode("utf-8")
                            if hashlib.sha256(block).hexdigest() != span["spanSha256"]:
                                raise ValueError("E03 canonical source span SHA differs")
    except (ValueError, KeyError, TypeError, OSError, ImportError, AttributeError) as error:
        errors.append(str(error))
    return {"schema": "py-elk-e03-validation/v1", "status": ("E03_HISTORICAL_FOUNDATIONS_VALIDATED" if historical else "E03_FOUNDATIONS_VALIDATED") if not errors else "FAIL",
            "errors": errors, "controls": controls, "runtimeClaims": RUNTIME_CLAIMS, "pythonAlgorithmsVerified": 0,
            "historical": historical, "currentPackageBytesValidated": False if historical else not errors,
            "limitation": "Internal graph/option/call-data acceptance only; no layout, public API, random stream or lifecycle acceptance."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-upstream", action="store_true")
    parser.add_argument("--historical", action="store_true", help="Validate original declarations and sealed product bytes without running old code or certifying the current registry")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = check(with_upstream=args.with_upstream, historical=args.historical)
    if args.out:
        write(args.out, report)
    print(json.dumps({key: report[key] for key in ("status", "errors", "pythonAlgorithmsVerified")}, indent=2))
    raise SystemExit(bool(report["errors"]))
