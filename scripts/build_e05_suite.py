"""Build/check E05 input suites; never computes coordinates or accepts a layout.

Master requests are copied byte-for-byte. New project inputs are generated
separately, with no reference coordinates. Build always requires a NEW directory.
Capture genuine oracles separately with validate_layout.py reference --cases.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

from layout_checks import ROOT, contained, diff, load, pointer, sha256, validate_json, write

sys.path.insert(0, str(ROOT / "src"))
from pyelk._errors import ValidationError
from pyelk.model import Graph
from pyelk.options import resolve_options

MASTER = ROOT / "tests/fixtures/validation/cases.json"
SUITE = ROOT / "tests/fixtures/suites/E05"
P = "org.eclipse.elk."
MAX_CHILDREN = 8
MAX_GEOMETRY_VALUE = 1_000_000


def classify_request(request, *, expected_outcome="returned"):
    """Conservative suite-selection policy, independent of future algorithm code.

    One connected directed simple DAG (or zero/one node) is explored.
    Excluded inputs are not counted as successful layout/error conformance.
    """
    reasons = []

    def reject(code, path="", detail=""):
        reasons.append({"code": code, "path": path, "detail": detail})

    if expected_outcome != "returned":
        reject("master-error-case", "", "E05 positive layout suite does not count master errors")
    if type(request) is not dict or request.get("schema") != "py-elk-layout-request/v1":
        reject("invalid-request", "", "Expected a layout request envelope")
        return {"included": False, "reasons": reasons}
    if not {"constructor", "layoutArguments", "graph"} <= request.keys():
        reject("missing-request-field")
        return {"included": False, "reasons": reasons}
    try:
        validate_json(request)
        if type(request["constructor"]) is not dict or type(request["layoutArguments"]) is not dict:
            raise ValueError("Constructor and arguments must be JSON objects")
        model = Graph.from_json(request["graph"])
        resolved = resolve_options(constructor=request["constructor"], layout_arguments=request["layoutArguments"],
                                   local=request["graph"].get("layoutOptions"))
    except (ValueError, TypeError, OverflowError) as error:
        reject("invalid-host-input", getattr(error, "path", ""), str(error))
        return {"included": False, "reasons": reasons}
    graph, constructor, arguments = request["graph"], request["constructor"], request["layoutArguments"]
    children, edges = graph.get("children", []), graph.get("edges", [])
    values = resolved.values
    # E03 accepts Mapping padding as a host convenience, but the fixed JS
    # importer rejects that same effective JSON value. Replaced/overridden
    # values are deliberately absent from raw_values and remain irrelevant.
    if P + "padding" in resolved.raw_values and type(resolved.raw_values[P + "padding"]) is not str:
        reject("padding-syntax-outside-slice", "", "Only the effective reference-compatible four-side padding string is admitted")
    for key in constructor:
        if key not in {"defaultLayoutOptions", "algorithms", "workerUrl", "workerFactory"}:
            reject("unknown-constructor-parameter", pointer("/constructor", key))
    for key in arguments:
        if key not in {"layoutOptions", "logging", "measureExecutionTime"}:
            reject("unknown-execution-parameter", pointer("/layoutArguments", key))
    for path, element in [("/graph", graph), *[("/graph/children/" + str(i), item) for i, item in enumerate(children)],
                          *[("/graph/edges/" + str(i), item) for i, item in enumerate(edges)]]:
        if "properties" in element:
            reject("legacy-properties-container", path + "/properties")
    if len(children) > MAX_CHILDREN:
        reject("node-count-outside-slice", "/graph/children", "At most eight children in the prepared E05 source scope")
    for key in ("spacing.nodeNode", "layered.spacing.nodeNodeBetweenLayers", "spacing.componentComponent"):
        if values[P + key] > MAX_GEOMETRY_VALUE:
            reject("spacing-magnitude-outside-slice", "", key)
    for side in ("top", "right", "bottom", "left"):
        if getattr(values[P + "padding"], side) > MAX_GEOMETRY_VALUE:
            reject("padding-magnitude-outside-slice", "", side)
    for element in [model.root, *model.nodes[1:], *model.ports, *model.edges]:
        if type(element.id) is not str or not element.id:
            reject("non-string-identity", element.path + "/id", "E05/E02 success identity is a nonempty string")
    for key in ("workerUrl", "workerFactory"):
        if key in constructor:
            reject("worker-parameter", "/constructor/" + key)
    if "algorithms" in constructor:
        algorithms = constructor["algorithms"]
        if type(algorithms) is not list or algorithms != ["layered"]:
            reject("registration-outside-slice", "/constructor/algorithms", "Only the explicit singleton layered registration is admitted")
    for key in ("logging", "measureExecutionTime"):
        if key in arguments and arguments[key] is not False:
            reject("diagnostic-option", "/layoutArguments/" + key, "Only absent/false diagnostics in deterministic E05 positives")
    if values[P + "direction"] not in ("RIGHT", "UNDEFINED"):
        reject("direction-outside-slice", "/graph/layoutOptions", values[P + "direction"])
    if values[P + "randomSeed"] == 0:
        reject("unseeded-random-path", "", "Seed zero is not a fixed reproducibility claim")
    if values[P + "separateConnectedComponents"] is not True:
        reject("component-mode-outside-slice")
    if "logging" in graph:
        reject("existing-root-logging", "/graph/logging", "Reference logging cleanup is outside this prototype")
    for index, element in enumerate([graph, *children]):
        if "$H" in element:
            where = "/graph" if index == 0 else "/graph/children/" + str(index - 1)
            reject("existing-shape-identity-cache", where + "/$H", "Reference identity cache/collision path is outside this prototype")
        if element.get("ports") or element.get("labels"):
            reject("ports-or-labels")
    for index, node in enumerate(children):
        where = "/graph/children/" + str(index)
        if node.get("children") or node.get("edges"):
            reject("nested-graph", where)
        if node.get("layoutOptions"):
            reject("element-options-outside-slice", where + "/layoutOptions")
        for dimension in ("width", "height"):
            if dimension not in node:
                reject("missing-node-dimension", where + "/" + dimension)
            elif node[dimension] > MAX_GEOMETRY_VALUE:
                reject("dimension-magnitude-outside-slice", where + "/" + dimension)
        if any(key in node for key in ("x", "y")):
            reject("existing-node-position", where)
    if any(key in graph for key in ("x", "y", "width", "height")):
        reject("existing-root-geometry", "/graph")
    pairs = []
    node_ids = {node["id"] for node in children}
    for index, edge in enumerate(edges):
        where = "/graph/edges/" + str(index)
        if edge.get("labels") or edge.get("layoutOptions"):
            reject("edge-options-or-labels", where)
        if any(key in edge for key in ("sections", "container", "startPoint", "endPoint", "bendPoints", "junctionPoints", "sourcePoint", "targetPoint")):
            reject("existing-edge-geometry", where)
        sources, targets = edge["sources"], edge["targets"]
        if len(sources) != 1 or len(targets) != 1:
            reject("hyperedge", where)
        elif sources[0] not in node_ids or targets[0] not in node_ids:
            reject("non-child-endpoint", where)
        else:
            pairs.append((sources[0], targets[0]))
    count = len(children)
    if len(set(pairs)) != len(pairs) or any(a == b for a, b in pairs):
        reject("parallel-or-self-edge", "/graph/edges")
    incoming = {identity: 0 for identity in node_ids}
    outgoing = {identity: [] for identity in node_ids}
    adjacent = {identity: set() for identity in node_ids}
    for source, target in pairs:
        incoming[target] += 1
        outgoing[source].append(target)
        adjacent[source].add(target)
        adjacent[target].add(source)
    ready = [identity for identity in node_ids if incoming[identity] == 0]
    visited = set()
    while ready:
        current = ready.pop()
        visited.add(current)
        for target in outgoing[current]:
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
    if len(visited) != count:
        reject("cyclic-topology", "/graph/edges")
    if count:
        pending, connected = [children[0]["id"]], set()
        while pending:
            current = pending.pop()
            if current not in connected:
                connected.add(current)
                pending.extend(adjacent[current] - connected)
        if len(connected) != count:
            reject("disconnected-topology", "/graph")
    padding = values[P + "padding"]
    policy = {"profile": "basic-flat-orthogonal", "direction": "RIGHT",
              "padding": {key: getattr(padding, key) for key in ("top", "left", "bottom", "right")},
              "nodeNode": values[P + "spacing.nodeNode"], "betweenLayers": values[P + "layered.spacing.nodeNodeBetweenLayers"],
              "forwardEdges": True}
    return {"included": not reasons, "reasons": reasons,
            "directionOption": values[P + "direction"], "geometry": policy,
            "directionEvidence": "Explicit RIGHT or default UNDEFINED with fixed aspectRatio default >=1; oracle must confirm actual RIGHT geometry"}


def project_variants():
    """Independent DAG inputs without reference coordinates; source scope proposed."""
    variants = []

    def add(identity, sizes, links, *, options=None, constructor=None, arguments=None, node_order=None, edge_order=None):
        nodes = [{"id": "dag-node-" + str(i), "width": width, "height": height,
                  "business": {"$H": 0, "null": None}} for i, (width, height) in enumerate(sizes)]
        edges = [{"id": "dag-edge-" + str(i), "sources": [nodes[a]["id"]], "targets": [nodes[b]["id"]],
                  "business": {"error": {"stack": "edge-business-stack"}, "false": False}}
                 for i, (a, b) in enumerate(links)]
        if node_order is not None:
            nodes = [nodes[i] for i in node_order]
        if edge_order is not None:
            edges = [edges[i] for i in edge_order]
        graph = {"id": "e05-root", "business": {"$H": False, "error": {"stack": "root-business-stack"}}, "children": nodes, "edges": edges}
        if options is not None:
            graph["layoutOptions"] = copy.deepcopy(options)
        request = {"schema": "py-elk-layout-request/v1", "constructor": copy.deepcopy(constructor or {}),
                   "layoutArguments": copy.deepcopy(arguments or {}), "graph": graph}
        selected = classify_request(request)
        if not selected["included"]:
            raise ValueError("Project variant violates proposed E05 scope: " + identity + " " + str(selected["reasons"]))
        variants.append((identity, request, selected["geometry"]))

    equal = lambda count: [(30, 20)] * count
    chain = lambda count: [(i, i + 1) for i in range(count - 1)]
    fork, join = [(0, 1), (0, 2)], [(0, 2), (1, 2)]
    diamond = [(0, 1), (0, 2), (1, 3), (2, 3)]
    add("e05-fork-default", equal(3), fork)
    add("e05-join-default", equal(3), join)
    add("e05-diamond-default", equal(4), diamond)
    add("e05-skip-one-dummy", equal(3), chain(3) + [(0, 2)])
    add("e05-skip-two-dummies", equal(4), chain(4) + [(0, 3)])
    add("e05-skip-four-dummies", equal(6), chain(6) + [(0, 5)])
    add("e05-multiple-skip-six", equal(6), chain(6) + [(0, 3), (1, 5), (0, 5)])
    add("e05-fanout-four", equal(4), [(0, 1), (0, 2), (0, 3)])
    add("e05-fanin-four", equal(4), [(0, 3), (1, 3), (2, 3)])
    add("e05-two-source-five", equal(5), [(0, 2), (1, 2), (2, 3), (2, 4)])
    add("e05-two-sink-five", equal(5), [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4)])
    add("e05-crossing-six", equal(6), [(0, 2), (0, 3), (1, 2), (1, 3), (2, 4), (3, 5)])
    add("e05-diamond-unequal", [(17, 5), (31, 13), (7, 29), (19, 11)], diamond)
    add("e05-fork-zero", [(0, 0)] * 3, fork)
    add("e05-join-mixed-zero", [(0, 0), (17, 3), (0, 0)], join)
    add("e05-diamond-decimal", [(.1, .3), (17.25, 5.5), (.25, 11.125), (31.5, .125)], diamond)
    add("e05-long-edge-decimal", [(.1, .3), (17.25, 5.5), (.25, 11.125), (31.5, .125)], chain(4) + [(0, 3)],
        options={"elk.spacing.nodeNode": 0, "elk.layered.spacing.nodeNodeBetweenLayers": 0, "elk.padding": "[top=0,right=0,bottom=0,left=0]"})
    add("e05-diamond-node-order", equal(4), diamond, node_order=[3, 1, 0, 2])
    add("e05-diamond-edge-order", equal(4), diamond, edge_order=[3, 2, 1, 0])
    add("e05-multiskip-permuted-eight", equal(8), chain(8) + [(0, 4), (1, 6), (0, 7)],
        node_order=[3, 7, 1, 5, 0, 6, 2, 4], edge_order=list(range(9, -1, -1)), options={"elk.randomSeed": 17})
    add("e05-diamond-seed17", equal(4), diamond, options={"elk.randomSeed": 17})
    add("e05-diamond-seed-negative17", equal(4), diamond, options={"elk.randomSeed": -17})
    add("e05-fork-custom-spacing", [(17, 5), (31, 13), (7, 29)], fork,
        options={"elk.direction": "RIGHT", "elk.randomSeed": 7, "elk.spacing.nodeNode": 37,
                 "elk.layered.spacing.nodeNodeBetweenLayers": 53, "elk.padding": "[top=11,right=17,bottom=23,left=31]"})
    add("e05-diamond-option-precedence", equal(4), diamond,
        constructor={"defaultLayoutOptions": {"elk.direction": "LEFT"}},
        arguments={"layoutOptions": {"elk.direction": "DOWN", "elk.randomSeed": 7}},
        options={"org.eclipse.elk.direction": "RIGHT", "org.eclipse.elk.padding": "[top=2,right=3,bottom=5,left=7]"})
    return variants


def plan_suite(master=MASTER):
    master = Path(master).resolve()
    document = load(master)
    if document.get("schema") != "py-elk-validation-cases/v1" or type(document.get("cases")) is not list or not document["cases"]:
        raise ValueError("Invalid or empty master suite")
    master_ids = [case["id"] for case in document["cases"]]
    if len(set(master_ids)) != len(master_ids) or not all(type(identity) is str and re.fullmatch(r"[a-z0-9][a-z0-9-]*", identity) for identity in master_ids):
        raise ValueError("Invalid master identity set")
    requests, cases, decisions = {}, [], []
    for case in document["cases"]:
        original = contained(master.parent, case["request"])
        request = load(original)
        selected = classify_request(request, expected_outcome=case["expectedOutcome"])
        decision = {"id": case["id"], "originalRequest": case["request"], "originalRequestSha256": sha256(original),
                    "expectedOutcome": case["expectedOutcome"], "included": selected["included"], "reasons": selected["reasons"]}
        if selected["included"]:
            relative = "requests/master/" + case["id"] + ".json"
            requests[relative] = original.read_bytes()
            copied = copy.deepcopy(case)
            copied["request"] = relative
            cases.append(copied)
            decision["suiteRequest"] = relative
        decisions.append(decision)
    generated = []
    for identity, request, geometry in project_variants():
        if identity in master_ids:
            raise ValueError("Variant ID conflicts with master")
        relative = "requests/project/" + identity + ".json"
        raw = (json.dumps(request, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
        requests[relative] = raw
        cases.append({"id": identity, "request": relative, "origin": "project-authored-e05-variant", "expectedOutcome": "returned", "geometry": geometry})
        generated.append({"id": identity, "request": relative, "requestSha256": hashlib.sha256(raw).hexdigest(),
                          "origin": "independent-project-input", "expectedCoordinatesEmbedded": False})
    lock = load(ROOT / "UPSTREAM.json")
    selected_count = sum(item["included"] for item in decisions)
    portable_master = master.relative_to(ROOT).as_posix() if master.is_relative_to(ROOT) else master.as_posix()
    selection = {"schema": "py-elk-slice-selection/v1", "iteration": "E05", "policy": "flat-right-connected-dag-inputs/proposed-v1",
                 "limits": {"maxChildren": MAX_CHILDREN, "maxGeometryValue": MAX_GEOMETRY_VALUE},
                 "status": "INPUTS_PREPARED", "supportStatus": "PROPOSED_SOURCE_GUARDS_PENDING",
                 "algorithmSourceGate": "unverified-for-E05-expansion", "master": {"path": portable_master, "sha256": sha256(master), "caseCount": len(decisions)},
                 "baseline": {"version": lock["javascript"]["version"], "commit": lock["javascript"]["commit"],
                              "entrypointSha256": lock["distribution"]["sha256Files"]["lib/elk.bundled.js"]},
                 "masterCases": decisions, "selectedMasterCases": selected_count,
                 "excludedMasterCases": len(decisions) - selected_count, "projectVariants": generated,
                 "projectVariantCount": len(generated), "suiteCaseCount": len(cases), "pythonAlgorithmsVerified": 0,
                 "oracleStatus": "CAPTURE_SEPARATELY", "limitation": "Proposed input membership and bytes only; source guards are not frozen and no candidate, algorithm or geometry acceptance is established."}
    return {"schema": "py-elk-validation-cases/v1", "cases": cases}, selection, requests


def build_suite(out, *, master=MASTER):
    cases, selection, requests = plan_suite(master)
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    for relative, raw in requests.items():
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
    write(out / "cases.json", cases)
    write(out / "selection.json", selection)
    return selection


def check_suite(suite=SUITE, *, master=MASTER):
    suite = Path(suite).resolve()
    expected_cases, expected_selection, requests = plan_suite(master)
    if not diff(load(suite / "cases.json"), expected_cases)["passed"]:
        raise ValueError("Slice cases/geometry/source membership differs from independently regenerated plan")
    if not diff(load(suite / "selection.json"), expected_selection)["passed"]:
        raise ValueError("Slice source denominator, reasons or preparation claims drifted")
    actual = {p.relative_to(suite).as_posix() for p in (suite / "requests").rglob("*") if p.is_file()}
    if actual != set(requests):
        raise ValueError("Slice request file denominator differs")
    for relative, raw in requests.items():
        if contained(suite, relative).read_bytes() != raw:
            raise ValueError("Slice original/project request bytes differ: " + relative)
    return expected_selection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    build = sub.add_parser("build", help="Write NEW input suite; no oracle or candidate execution")
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--master", type=Path, default=MASTER)
    check = sub.add_parser("check", help="Offline exact source/membership/request drift check")
    check.add_argument("--suite", type=Path, default=SUITE)
    check.add_argument("--master", type=Path, default=MASTER)
    args = parser.parse_args()
    try:
        result = build_suite(args.out, master=args.master) if args.action == "build" else check_suite(args.suite, master=args.master)
        print(json.dumps({"status": "SLICE_SUITE_INPUTS_BUILT" if args.action == "build" else "SLICE_SUITE_INPUTS_VERIFIED",
                          "selectedMasterCases": result["selectedMasterCases"], "masterCaseCount": result["master"]["caseCount"],
                          "projectVariantCount": result["projectVariantCount"], "suiteCaseCount": result["suiteCaseCount"],
                          "oracleChecked": False, "pythonAlgorithmsVerified": 0}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({"status": "HARNESS_ERROR", "error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
