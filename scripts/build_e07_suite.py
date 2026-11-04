"""Build/check E07 input suites; never computes coordinates or accepts a layout.

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
SUITE = ROOT / "tests/fixtures/suites/E07"
P = "org.eclipse.elk."
MAX_CHILDREN = 8
MAX_GEOMETRY_VALUE = 1_000_000
MAX_EDGES = 28


def classify_request(request, *, expected_outcome="returned"):
    """Conservative suite-selection policy, independent of future algorithm code.

    Flat directed multigraphs, isolates and disconnected weak components are explored.
    Cycles, self-loops and parallel edges are proposals, not runtime acceptance.
    Excluded inputs are not counted as successful layout/error conformance.
    """
    reasons = []

    def reject(code, path="", detail=""):
        reasons.append({"code": code, "path": path, "detail": detail})

    if expected_outcome != "returned":
        reject("master-error-case", "", "E07 positive layout suite does not count master errors")
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
        reject("node-count-outside-slice", "/graph/children", "At most eight children in the prepared E07 source scope")
    if len(edges) > MAX_EDGES:
        reject("edge-count-outside-proposal", "/graph/edges", "At most28 total original edges including self-loops")
    for key in ("spacing.nodeNode", "layered.spacing.nodeNodeBetweenLayers", "spacing.componentComponent"):
        if values[P + key] > MAX_GEOMETRY_VALUE:
            reject("spacing-magnitude-outside-slice", "", key)
    for side in ("top", "right", "bottom", "left"):
        if getattr(values[P + "padding"], side) > MAX_GEOMETRY_VALUE:
            reject("padding-magnitude-outside-slice", "", side)
    for element in [model.root, *model.nodes[1:], *model.ports, *model.edges]:
        if type(element.id) is not str or not element.id:
            reject("non-string-identity", element.path + "/id", "E07/E02 success identity is a nonempty string")
    for key in ("workerUrl", "workerFactory"):
        if key in constructor:
            reject("worker-parameter", "/constructor/" + key)
    if "algorithms" in constructor:
        algorithms = constructor["algorithms"]
        if type(algorithms) is not list or algorithms != ["layered"]:
            reject("registration-outside-slice", "/constructor/algorithms", "Only the explicit singleton layered registration is admitted")
    for key in ("logging", "measureExecutionTime"):
        if key in arguments and arguments[key] is not False:
            reject("diagnostic-option", "/layoutArguments/" + key, "Only absent/false diagnostics in deterministic E07 positives")
    if values[P + "direction"] not in ("RIGHT", "LEFT", "DOWN", "UP", "UNDEFINED"):
        reject("direction-outside-slice", "/graph/layoutOptions", values[P + "direction"])
    if values[P + "randomSeed"] == 0:
        reject("unseeded-random-path", "", "Seed zero is not a fixed reproducibility claim")
    if values[P + "edgeRouting"] != "ORTHOGONAL":
        reject("routing-outside-slice")
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
            child_options = node["layoutOptions"]
            if (type(child_options) is not dict or len(child_options) != 1 or
                    next(iter(child_options), None) not in ("elk.padding", P + "padding")):
                reject("element-options-outside-slice", where + "/layoutOptions")
            else:
                try:
                    child_resolved = resolve_options(local=child_options)
                    child_padding = child_resolved.values[P + "padding"]
                    if type(next(iter(child_options.values()))) is not str or any(
                            getattr(child_padding, side) > MAX_GEOMETRY_VALUE for side in ("top", "right", "bottom", "left")):
                        reject("child-padding-outside-slice", where + "/layoutOptions")
                except (ValueError, TypeError, OverflowError) as error:
                    reject("child-padding-outside-slice", where + "/layoutOptions", str(error))
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
    incoming = {identity: 0 for identity in node_ids}
    outgoing = {identity: [] for identity in node_ids}
    adjacent = {identity: set() for identity in node_ids}
    for source, target in pairs:
        if source == target:
            continue
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
    has_directed_cycle = len(visited) != count
    self_loops = sum(a == b for a, b in pairs)
    padding = values[P + "padding"]
    direction = values[P + "direction"]
    policy = {"profile": "basic-flat-orthogonal", "direction": "RIGHT" if direction == "UNDEFINED" else direction,
              "padding": {key: getattr(padding, key) for key in ("top", "left", "bottom", "right")},
              "nodeNode": values[P + "spacing.nodeNode"], "betweenLayers": values[P + "layered.spacing.nodeNodeBetweenLayers"],
              "forwardEdges": not has_directed_cycle and self_loops == 0,
              "rankSeparation": "default-layered-components-v2"}
    if values[P + "separateConnectedComponents"] is True:
        policy["layerFrame"] = "independent-components-v1"
    return {"included": not reasons, "reasons": reasons,
            "directionOption": values[P + "direction"], "geometry": policy,
            "topology": {"hasDirectedCycle": has_directed_cycle, "selfLoopCount": self_loops,
                         "parallelExcess": len(pairs) - len(set(pairs)), "totalEdges": len(edges)},
            "directionEvidence": "Actual original option; UNDEFINED resolves RIGHT under fixed default aspectRatio. Input preparation never accepts an engine result."}


def graph(sizes, links, *, direction='RIGHT', seed=17, options=None):
    nodes = [{'id': 'n' + str(i), 'width': w, 'height': h} for i, (w, h) in enumerate(sizes)]
    edges = [{'id': 'e' + str(i), 'sources': ['n' + str(a)], 'targets': ['n' + str(b)]} for i, (a, b) in enumerate(links)]
    selected = {'elk.algorithm': 'layered', 'elk.direction': direction, 'elk.randomSeed': seed,
                'elk.edgeRouting': 'ORTHOGONAL'}
    selected.update(options or {})
    return {'schema': 'py-elk-layout-request/v1', 'constructor': {}, 'layoutArguments': {},
            'graph': {'id': 'root', 'children': nodes, 'edges': edges, 'layoutOptions': selected}}

def variants():
    rows = []
    def add(identity, request, interaction):
        rows.append((identity, request, interaction))
    chain_sizes = [(9.25, 3.5), (27, 11.75), (5.125, 19)]
    chain = [(0, 1), (1, 2)]
    mixed_sizes = [(1e-14, 13), (0, 0), (21, 1e-14), (7.25, 19.5)]
    mixed = [(0, 1), (1, 2), (2, 3), (3, 0), (1, 1), (0, 1)]
    component_sizes = [(7, 13), (19.25, 11), (0, 3.5), (1e-14, 1e-14),
                       (21, 9), (5, 17.25), (13, 0), (2.5, 31)]
    components = [(0, 1), (1, 2), (3, 3), (4, 5), (4, 5)]
    asymmetric = {'elk.padding': '[top=1,left=7,bottom=11,right=17]', 'elk.spacing.nodeNode': 13.5,
                  'elk.layered.spacing.nodeNodeBetweenLayers': 31.25}
    component_options = {'elk.padding': '[top=2,left=3,bottom=5,right=7]', 'elk.spacing.nodeNode': 17.5,
                         'elk.layered.spacing.nodeNodeBetweenLayers': 23.75, 'elk.spacing.componentComponent': 0.25}
    for direction in ('RIGHT', 'LEFT', 'DOWN', 'UP'):
        add('e07-direction-' + direction.lower() + '-asymmetric-chain',
            graph(chain_sizes, chain, direction=direction, options=asymmetric), 'direction x unequal given size x asymmetric padding')
    for direction in ('RIGHT', 'LEFT', 'DOWN', 'UP'):
        add('e07-direction-' + direction.lower() + '-cycle-loop-parallel',
            graph(mixed_sizes, mixed, direction=direction, options=asymmetric), 'direction x cyclic/selfloop/parallel x zero/tiny sizes')
    for direction in ('RIGHT', 'LEFT', 'DOWN', 'UP'):
        add('e07-direction-' + direction.lower() + '-components',
            graph(component_sizes, components, direction=direction, options=component_options), 'direction x 5 weak components x global loop processors x isolates')
    for direction in ('RIGHT', 'LEFT', 'DOWN', 'UP'):
        options = {**component_options, 'elk.separateConnectedComponents': False, 'elk.spacing.componentComponent': 42}
        add('e07-direction-' + direction.lower() + '-unseparated',
            graph(component_sizes, components, direction=direction, seed=-17, options=options), 'direction x false separation x disconnected pipeline')
    isolates = [(1, 1), (11, 7), (0, 0), (31, 17), (1e-14, 3), (5, 29), (2, 0), (13.5, 9.25)]
    add('e07-eight-isolates-unequal', graph(isolates, [], options={'elk.spacing.componentComponent': 7.5, 'elk.spacing.nodeNode': 100}), 'isolated component packing and source node order')
    add('e07-eight-isolates-false', graph(isolates, [], options={'elk.separateConnectedComponents': False, 'elk.spacing.componentComponent': 999, 'elk.spacing.nodeNode': 9}), 'isolated nodes without component split')
    pairs = [(0, 1), (2, 3), (4, 5)]
    for label, spacing in [('zero', 0), ('max', 1_000_000)]:
        add('e07-spacing-components-' + label, graph(component_sizes, pairs, options={'elk.spacing.componentComponent': spacing, 'elk.spacing.nodeNode': 37}), 'component spacing independent of same-layer node spacing')
    diamond = [(0, 1), (0, 2), (1, 3), (2, 3)]
    for label, spacing in [('zero', 0), ('fractional', 0.75)]:
        add('e07-spacing-node-' + label + '-fork', graph([(13, 7), (5, 11), (19, 3), (7, 17)], diamond, direction='DOWN', options={'elk.spacing.nodeNode': spacing}), 'same-layer spacing x vertical direction')
    for label, spacing in [('zero', 0), ('fractional', 0.125), ('max', 1_000_000)]:
        add('e07-spacing-layer-' + label + '-chain', graph([(0, 3), (0, 7), (0, 5)], chain, direction='LEFT', options={'elk.layered.spacing.nodeNodeBetweenLayers': spacing}), 'layer spacing x zero width x negative-axis direction')
    add('e07-padding-zero', graph(chain_sizes, chain, direction='UP', options={'elk.padding': '[top=0,left=0,bottom=0,right=0]'}), 'zero root padding')
    add('e07-padding-asymmetric-fractional', graph(chain_sizes, chain, direction='UP', options={'elk.padding': '[top=0.125,left=3.5,bottom=7.25,right=11.75]'}), 'asymmetric root padding with transposed direction')
    add('e07-padding-max', graph([(0, 1e-14)], [], options={'elk.padding': '[top=1000000,left=1000000,bottom=1000000,right=1000000]'}), 'maximum legal padding and tiny singleton')
    add('e07-seed-negative-boundary', graph(mixed_sizes, mixed, direction='LEFT', seed=-(2 ** 31)), 'minimum signed32 seed')
    add('e07-seed-positive-boundary', graph(mixed_sizes, mixed, direction='LEFT', seed=2 ** 31 - 1), 'maximum signed32 seed')
    implicit = graph(mixed_sizes, mixed)
    implicit['graph'].pop('layoutOptions')
    implicit['graph']['business'] = {'$H': False, 'error': {'stack': 'original business stack'}, 'zero': 0, 'false': False}
    add('e07-seed-default-implicit', implicit, 'all implicit defaults and business fields')
    add('e07-seed-string-negative', graph(mixed_sizes, mixed, direction='UNDEFINED', seed='-17'), 'explicit UNDEFINED x string negative seed')
    all_options = {'algorithm': 'org.eclipse.elk.layered', 'direction': 'DOWN', 'padding': '[top=3,left=5,bottom=7,right=11]',
                   'spacing.nodeNode': 17.5, 'layered.spacing.nodeNodeBetweenLayers': 23.75,
                   'separateConnectedComponents': 'true', 'spacing.componentComponent': '9.25',
                   'edgeRouting': 'ORTHOGONAL', 'randomSeed': '17'}
    full = graph(component_sizes, components); full['graph']['layoutOptions'] = {P + k: v for k, v in all_options.items()}
    add('e07-full-id-options', full, 'all nine canonical full IDs x legal typed/string values')
    constructor = graph(component_sizes, components); constructor['graph'].pop('layoutOptions')
    constructor['constructor']['defaultLayoutOptions'] = {'elk.' + k: v for k, v in {**all_options, 'direction': 'UP', 'separateConnectedComponents': False}.items()}
    add('e07-constructor-defaults-all-nine', constructor, 'constructor global options selected when call missing')
    empty_call = copy.deepcopy(constructor); empty_call['layoutArguments']['layoutOptions'] = {}
    add('e07-call-empty-replaces-all-constructor', empty_call, 'present empty call fully replaces all constructor options')
    call = copy.deepcopy(constructor); call['layoutArguments']['layoutOptions'] = {'elk.' + k: v for k, v in {**all_options, 'algorithm': 'layered', 'direction': 'LEFT', 'padding': '[top=0,left=0,bottom=0,right=0]', 'separateConnectedComponents': True, 'randomSeed': -17}.items()}
    add('e07-call-replaces-constructor', call, 'call whole mapping replaces constructor mapping')
    local = copy.deepcopy(call); local['graph']['layoutOptions'] = {'elk.' + k: v for k, v in {**all_options, 'direction': 'UP', 'padding': '[top=2,left=4,bottom=6,right=8]', 'spacing.nodeNode': 11, 'layered.spacing.nodeNodeBetweenLayers': 19, 'spacing.componentComponent': 13, 'separateConnectedComponents': False, 'randomSeed': 7}.items()}
    add('e07-root-local-overrides-call', local, 'root element overrides selected global mapping for all nine')
    add('e07-component-mode-string-false', graph(component_sizes, components, direction='DOWN', seed='17', options={'elk.separateConnectedComponents': 'false', 'elk.spacing.nodeNode': '0.5', 'elk.layered.spacing.nodeNodeBetweenLayers': '0.25', 'elk.spacing.componentComponent': '3.75'}), 'legal string false and numeric string interactions')
    for label, key, value in [('asymmetric', 'elk.padding', '[top=1,left=3,bottom=5,right=7]'), ('zero', P + 'padding', '[top=0,left=0,bottom=0,right=0]')]:
        child = graph(chain_sizes, chain, options={'elk.padding': '[top=3,left=5,bottom=7,right=11]'})
        child['graph']['children'][1]['layoutOptions'] = {key: value}
        add('e07-child-padding-' + label, child, 'child padding source/effect investigation; not yet admitted or declared effective')
    permuted = graph(mixed_sizes, mixed, direction='DOWN'); permuted['graph']['children'] = [permuted['graph']['children'][i] for i in (2, 0, 3, 1)]
    add('e07-seed-order-node-array', permuted, 'raw node order affects work traversal without reordering public arrays')
    permuted = graph(mixed_sizes, mixed, direction='UP', seed=-1); permuted['constructor']['algorithms'] = ['layered']; permuted['graph']['edges'].reverse()
    add('e07-seed-order-edge-array', permuted, 'raw edge order plus explicit layered registration')
    assert len(rows) == 42 and len({row[0] for row in rows}) == 42
    return rows

def project_variants():
    """Fifty preselected inputs; original64 requests remain byte-identical."""
    rows = variants()
    for direction in ("RIGHT", "LEFT", "DOWN", "UP"):
        for kind, sizes, links in (
            ("zero-simple-ring", [(0, 0)] * 4, [(0, 1), (1, 2), (2, 3), (3, 0)]),
            ("zero-mixed-components", [(0, 0)] * 7, [(0, 1), (1, 2), (3, 4), (4, 5), (5, 3)]),
        ):
            item = graph(sizes, links, direction=direction, options={
                "elk.layered.spacing.nodeNodeBetweenLayers": 0, "elk.spacing.componentComponent": 0,
                "elk.padding": "[top=1,left=3,bottom=5,right=7]"})
            item["graph"]["business"] = {"$H": False, "error": {"stack": "retain"}, "zero": 0, "flag": False}
            rows.append(("e07-" + direction.lower() + "-" + kind, item,
                         "zero-size strict ring/component rank premise"))
    assert len(rows) == 50
    result = []
    for identity, item, interaction in rows:
        selected = classify_request(item)
        if not selected["included"]:
            raise ValueError("Project variant violates E07 proposal: " + identity + " " + str(selected["reasons"]))
        result.append((identity, item, selected["geometry"]))
    return result


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
            copied["geometry"] = selected["geometry"]
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
        cases.append({"id": identity, "request": relative, "origin": "project-authored-e07-variant", "expectedOutcome": "returned", "geometry": geometry})
        generated.append({"id": identity, "request": relative, "requestSha256": hashlib.sha256(raw).hexdigest(),
                          "origin": "independent-project-input", "expectedCoordinatesEmbedded": False})
    lock = load(ROOT / "UPSTREAM.json")
    selected_count = sum(item["included"] for item in decisions)
    portable_master = master.relative_to(ROOT).as_posix() if master.is_relative_to(ROOT) else master.as_posix()
    selection = {"schema": "py-elk-slice-selection/v1", "iteration": "E07", "policy": "flat-four-directions-multicomponent-inputs/proposed-v1",
                 "limits": {"maxChildren": MAX_CHILDREN, "maxTotalEdges": MAX_EDGES, "maxGeometryValue": MAX_GEOMETRY_VALUE},
                 "status": "INPUTS_PREPARED", "supportStatus": "PROPOSED_SOURCE_GUARDS_PENDING",
                 "algorithmSourceGate": "unverified-for-E07-expansion", "master": {"path": portable_master, "sha256": sha256(master), "caseCount": len(decisions)},
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
