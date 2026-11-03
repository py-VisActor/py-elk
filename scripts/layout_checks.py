"""Development-only, stdlib JSON diff, integrity and flat orthogonal geometry checks.

No graph normalization: model arrays, IDs, business data and section IDs survive.
Only geometry numbers receive the project's coordinate tolerance.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ABS_TOL = 1e-6
REL_TOL = 1e-9
SCHEMA = "py-elk-layout-observation/v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError("Nonfinite JSON: " + token)))
    validate_json(value)
    return value


def validate_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Nonfinite JSON number")
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        for item in value.values():
            validate_json(item)
    elif isinstance(value, list):
        for item in value:
            validate_json(item)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValueError("Not a JSON value")


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")


def contained(root: Path, name: str) -> Path:
    if not isinstance(name, str) or "\\" in name or ":" in name:
        raise ValueError("Invalid relative artifact path")
    path = (root / name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Missing or escaping artifact: " + name)
    return path


def pointer(path, key):
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def close(a, b, absolute=ABS_TOL, relative=REL_TOL):
    return abs(a - b) <= max(absolute, relative * max(abs(a), abs(b)))


# Full object shape is still compared. These are the ONLY tolerated numeric paths.
_SHAPE = r"(?:/(?:children|ports|labels)/\d+)*"
_GEOMETRY = re.compile(
    r"^/(?:result|inputAfter)" + _SHAPE + r"/(?:x|y|width|height)$|"
    r"^/(?:result|inputAfter)" + _SHAPE + r"/edges/\d+/labels/\d+/(?:x|y|width|height)$|"
    r"^/(?:result|inputAfter)" + _SHAPE + r"/edges/\d+/sections/\d+/(?:startPoint|endPoint|bendPoints/\d+)/(?:x|y)$|"
    r"^/(?:result|inputAfter)" + _SHAPE + r"/edges/\d+/junctionPoints/\d+/(?:x|y)$"
)


def diff(expected, actual, *, tolerant=False):
    """All differences, using RFC6901 paths; no truncation or implicit ignore list."""
    validate_json(expected)
    validate_json(actual)
    differences = []
    maximum = {"absolute": 0, "relative": 0, "path": None}

    def walk(a, b, path):
        if number(a) and number(b):
            delta = abs(a - b)
            scale = max(abs(a), abs(b))
            if _GEOMETRY.fullmatch(path) and delta > maximum["absolute"]:
                maximum.update(absolute=delta, relative=delta / scale if scale else 0, path=path)
            if a == b or (tolerant and _GEOMETRY.fullmatch(path) and close(a, b)):
                return
            differences.append({"path": path, "kind": "number", "expected": a, "actual": b,
                                "absoluteError": delta, "allowedError": max(ABS_TOL, REL_TOL * scale)
                                if tolerant and _GEOMETRY.fullmatch(path) else 0})
        elif type(a) is not type(b):
            differences.append({"path": path, "kind": "type", "expected": a, "actual": b})
        elif isinstance(a, dict):
            for key in sorted(a.keys() | b.keys()):
                p = pointer(path, key)
                if key not in a:
                    differences.append({"path": p, "kind": "unexpected", "actual": b[key]})
                elif key not in b:
                    differences.append({"path": p, "kind": "missing", "expected": a[key]})
                else:
                    walk(a[key], b[key], p)
        elif isinstance(a, list):
            if len(a) != len(b):
                differences.append({"path": path, "kind": "length", "expected": len(a), "actual": len(b)})
            for i in range(min(len(a), len(b))):
                walk(a[i], b[i], pointer(path, i))
            for i in range(len(b), len(a)):
                differences.append({"path": pointer(path, i), "kind": "missing", "expected": a[i]})
            for i in range(len(a), len(b)):
                differences.append({"path": pointer(path, i), "kind": "unexpected", "actual": b[i]})
        elif a != b:
            differences.append({"path": path, "kind": "value", "expected": a, "actual": b})

    walk(expected, actual, "")
    return {"passed": not differences, "differences": differences, "maxCoordinateError": maximum}


def contract(observation):
    """Envelope policy: engine identity/stack/lifecycle observations are diagnostics.

    The returned graph, named errors and all three mutable inputs are mandatory.
    Lifecycle differences are reported separately, never accepted as lifecycle parity.
    """
    if observation.get("schema") != SCHEMA or observation.get("outcome") not in ("returned", "threw"):
        raise ValueError("Invalid observation envelope")
    required = {"requestSha256", "outcome", "inputAfter", "constructorAfter", "argumentsAfter"}
    required.add("result" if observation["outcome"] == "returned" else "error")
    if not required <= observation.keys():
        raise ValueError("Observation is missing contract fields")
    if observation["outcome"] == "threw":
        if set(observation["error"]) != {"name", "message"} or not all(isinstance(v, str) for v in observation["error"].values()):
            raise ValueError("Errors must preserve name and message")
    return {key: observation[key] for key in sorted(required)}


def compare_observations(expected, actual):
    a, b = contract(expected), contract(actual)
    return {"exact": diff(a, b), "coordinateTolerance": diff(a, b, tolerant=True),
            "lifecycleObservations": {"reference": expected.get("termination"), "candidate": actual.get("termination"),
                                      "acceptance": "NOT_ASSESSED"}}


def input_preservation(request, observation):
    """Report the native-Python nonmutation goal independently from literal JS parity."""
    checks = {name: diff(request[key], observation[name]) for key, name in
              (("graph", "inputAfter"), ("constructor", "constructorAfter"), ("layoutArguments", "argumentsAfter"))}
    return {"preserved": all(item["passed"] for item in checks.values()), "comparisons": checks,
            "acceptance": "OBSERVATION_ONLY; explicit cross-engine side-effect policy remains an M1 decision"}


def geometry(request, observation, policy):
    """Independent constraints for explicitly selected flat, node-only ORTHOGONAL graphs.

    Unsupported coordinate frames, nested graphs, ports and label layout fail closed.
    Direction/layer spacing assertions require a case's acyclic-forward-edge policy.
    """
    errors = []
    checked = []

    def error(path, code, detail=""):
        errors.append({"path": path, "code": code, "detail": detail})

    if observation["outcome"] != "returned":
        return {"status": "NOT_APPLICABLE", "passed": None, "errors": [], "reason": "Error case has no geometry"}
    if policy is None:
        return {"status": "NOT_CHECKED", "passed": None, "errors": [], "reason": "No geometry policy declared"}
    if policy.get("profile") != "basic-flat-orthogonal":
        raise ValueError("Unknown geometry profile")
    original, graph = request.get("graph"), observation.get("result")
    if not isinstance(original, dict) or not isinstance(graph, dict):
        return {"status": "FAIL", "passed": False, "errors": [{"path": "/result", "code": "graph_type"}]}
    nodes, edges = graph.get("children", []), graph.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list) or not all(isinstance(n, dict) for n in nodes + edges):
        return {"status": "FAIL", "passed": False, "errors": [{"path": "/result", "code": "model_type"}]}
    shapes = [original, graph, *original.get("children", []), *nodes]
    if any(any(key in s and s[key] for key in ("ports", "labels")) for s in shapes) or any(n.get("children") or n.get("edges") for n in nodes + original.get("children", [])):
        return {"status": "UNSUPPORTED", "passed": False, "errors": [], "reason": "Ports/labels/nested geometry requires another profile"}
    if any(e.get("labels") for e in edges + original.get("edges", [])):
        return {"status": "UNSUPPORTED", "passed": False, "errors": [], "reason": "Edge label geometry requires another profile"}
    for shape in shapes:
        for key, value in shape.get("layoutOptions", {}).items():
            if key.endswith(("shapeCoords", "edgeCoords")) and value not in ("INHERIT", "PARENT", "CONTAINER"):
                return {"status": "UNSUPPORTED", "passed": False, "errors": [], "reason": "Coordinate frame outside flat profile"}

    def scalar(obj, key, p, nonnegative=False):
        v = obj.get(key)
        if not number(v) or (nonnegative and v < 0):
            error(pointer(p, key), "invalid_number", "Finite" + (" nonnegative" if nonnegative else "") + " number required")
            return None
        return v

    width = scalar(graph, "width", "/result", True)
    height = scalar(graph, "height", "/result", True)
    scalar(graph, "x", "/result")
    scalar(graph, "y", "/result")
    ids = set()
    for i, item in enumerate([graph, *nodes, *edges]):
        identity = item.get("id")
        if not isinstance(identity, str) or not identity or identity in ids:
            error("/result", "id_identity", str(identity))
        else:
            ids.add(identity)
    by_id = {}
    for i, node in enumerate(nodes):
        p = f"/result/children/{i}"
        vals = [scalar(node, k, p, k in ("width", "height")) for k in ("x", "y", "width", "height")]
        if None not in vals and isinstance(node.get("id"), str):
            by_id[node["id"]] = (*vals, p)
    if errors:
        return {"status": "FAIL", "passed": False, "errors": errors}
    padding = policy["padding"]
    for name in ("top", "bottom", "left", "right"):
        if not number(padding[name]) or padding[name] < 0:
            raise ValueError("Invalid padding policy")
    direction = policy["direction"]
    if direction not in ("RIGHT", "LEFT", "DOWN", "UP"):
        raise ValueError("Invalid direction policy")
    for key in ("nodeNode", "betweenLayers"):
        if not number(policy[key]) or policy[key] < 0:
            raise ValueError("Invalid spacing policy")
    for identity, (x, y, w, h, p) in by_id.items():
        if x < padding["left"] - ABS_TOL or y < padding["top"] - ABS_TOL or x + w > width - padding["right"] + ABS_TOL or y + h > height - padding["bottom"] + ABS_TOL:
            error(p, "root_padding_bounds", identity)
    checked.extend(["finite nonnegative dimensions", "unique IDs", "node root padding bounds"])

    source_nodes = original.get("children", [])
    if [n.get("id") for n in source_nodes] != [n.get("id") for n in nodes] or [e.get("id") for e in original.get("edges", [])] != [e.get("id") for e in edges]:
        error("/result", "model_identity_or_order")
    for n in source_nodes:
        if n.get("id") in by_id:
            _, _, w, h, p = by_id[n["id"]]
            if not close(w, n["width"]) or not close(h, n["height"]):
                error(p, "given_node_dimensions")

    horizontal = direction in ("LEFT", "RIGHT")
    boxes = list(by_id.values())
    for i, (x, y, w, h, p) in enumerate(boxes):
        for xx, yy, ww, hh, pp in boxes[i + 1:]:
            if min(x + w, xx + ww) - max(x, xx) > ABS_TOL and min(y + h, yy + hh) - max(y, yy) > ABS_TOL:
                error(p, "node_overlap", pp)
            same_layer = close(x, xx) if horizontal else close(y, yy)
            gap = max(yy - y - h, y - yy - hh) if horizontal else max(xx - x - w, x - xx - ww)
            if same_layer and gap < policy["nodeNode"] - ABS_TOL:
                error(p, "same_layer_spacing", pp)
    checked.extend(["model identity/order", "given dimensions", "sibling overlap", "same layer spacing"])

    def on_border(point, box):
        x, y, w, h, _ = box
        px, py = point["x"], point["y"]
        return (x - ABS_TOL <= px <= x + w + ABS_TOL and y - ABS_TOL <= py <= y + h + ABS_TOL
                and (close(px, x) or close(px, x + w) or close(py, y) or close(py, y + h)))

    section_ids = set()
    for i, edge in enumerate(edges):
        p = f"/result/edges/{i}"
        source, target = edge.get("sources"), edge.get("targets")
        if not isinstance(source, list) or not isinstance(target, list) or len(source) != 1 or len(target) != 1 or not isinstance(source[0], str) or not isinstance(target[0], str) or source[0] not in by_id or target[0] not in by_id:
            error(p, "endpoint_identity")
            continue
        a, b = by_id[source[0]], by_id[target[0]]
        if edge.get("container", graph["id"]) != graph["id"]:
            error(p, "flat_edge_container")
        if policy.get("forwardEdges"):
            gap = {"RIGHT": b[0] - a[0] - a[2], "LEFT": a[0] - b[0] - b[2],
                   "DOWN": b[1] - a[1] - a[3], "UP": a[1] - b[1] - b[3]}[direction]
            if gap < policy["betweenLayers"] - ABS_TOL:
                error(p, "direction_or_layer_spacing")
        sections = edge.get("sections")
        if not isinstance(sections, list) or len(sections) != 1 or not isinstance(sections[0], dict):
            error(p, "single_section_required")
            continue
        section = sections[0]
        sp = p + "/sections/0"
        if not isinstance(section.get("id"), str) or not section["id"] or section["id"] in section_ids:
            error(sp, "section_id")
        else:
            section_ids.add(section["id"])
        if section.get("incomingShape", source[0]) != source[0] or section.get("outgoingShape", target[0]) != target[0] or section.get("incomingSections") or section.get("outgoingSections"):
            error(sp, "section_connectivity")
        bend_points = section.get("bendPoints", [])
        if not isinstance(bend_points, list):
            error(sp, "bend_points_type")
            continue
        points = [section.get("startPoint"), *bend_points, section.get("endPoint")]
        if not all(isinstance(pt, dict) and number(pt.get("x")) and number(pt.get("y")) for pt in points):
            error(sp, "route_point_number")
            continue
        if not on_border(points[0], a) or not on_border(points[-1], b):
            error(sp, "endpoint_not_on_node_border")
        for point in points:
            if point["x"] < -ABS_TOL or point["y"] < -ABS_TOL or point["x"] > width + ABS_TOL or point["y"] > height + ABS_TOL:
                error(sp, "route_outside_root")
        for start, end in zip(points, points[1:]):
            vertical = close(start["x"], end["x"])
            horizontal_segment = close(start["y"], end["y"])
            if not vertical and not horizontal_segment:
                error(sp, "non_orthogonal_segment")
                continue
            for identity, (x, y, w, h, _) in by_id.items():
                if identity in (source[0], target[0]):
                    continue
                hit = ((vertical and x + ABS_TOL < start["x"] < x + w - ABS_TOL
                        and min(max(start["y"], end["y"]), y + h) - max(min(start["y"], end["y"]), y) > ABS_TOL)
                       or (horizontal_segment and y + ABS_TOL < start["y"] < y + h - ABS_TOL
                           and min(max(start["x"], end["x"]), x + w) - max(min(start["x"], end["x"]), x) > ABS_TOL))
                if hit:
                    error(sp, "route_crosses_unrelated_node", identity)
    checked.extend(["single source/target ownership", "section identity/connectivity", "endpoint borders",
                    "orthogonality", "route root bounds", "unrelated node avoidance"])
    if policy.get("forwardEdges"):
        checked.append("DAG forward direction and edge layer spacing")
    # Optional assertion for cases explicitly designed with rectangular components.
    # Not applied to arbitrary polyomino/compound packing or separation=false.
    if "componentRectangleGap" in policy:
        required_gap = policy["componentRectangleGap"]
        if not number(required_gap) or required_gap < 0:
            raise ValueError("Invalid component rectangle gap policy")
        adjacency = {identity: set() for identity in by_id}
        for edge in edges:
            s, t = edge.get("sources", []), edge.get("targets", [])
            if len(s) == len(t) == 1 and s[0] in adjacency and t[0] in adjacency:
                adjacency[s[0]].add(t[0])
                adjacency[t[0]].add(s[0])
        remaining = set(adjacency)
        component_boxes = []
        while remaining:
            stack, component = [min(remaining)], set()
            while stack:
                identity = stack.pop()
                if identity not in component:
                    component.add(identity)
                    stack.extend(adjacency[identity] - component)
            remaining -= component
            component_boxes.append((min(by_id[n][0] for n in component), min(by_id[n][1] for n in component),
                                    max(by_id[n][0] + by_id[n][2] for n in component), max(by_id[n][1] + by_id[n][3] for n in component)))
        for i, (x, y, right, bottom) in enumerate(component_boxes):
            for xx, yy, rr, bb in component_boxes[i + 1:]:
                if max(xx - right, x - rr, yy - bottom, y - bb) < required_gap - ABS_TOL:
                    error("/result", "component_rectangle_spacing")
        checked.append("declared rectangular component gap")
    return {"status": "PASS" if not errors else "FAIL", "passed": not errors, "errors": errors,
            "checked": checked, "limitation": "Flat node-only orthogonal constraints; not proof of ELK strategy/optimality or full feature coverage."}


def validate_suite(path: Path):
    suite = load(path)
    if suite.get("schema") != "py-elk-validation-cases/v1" or not suite.get("cases"):
        raise ValueError("Empty or invalid validation suite")
    identities = set()
    for case in suite["cases"]:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", case["id"]) or case["id"] in identities:
            raise ValueError("Invalid or duplicate case ID")
        identities.add(case["id"])
        request_path = contained(path.parent, case["request"])
        request = load(request_path)
        if request.get("schema") != "py-elk-layout-request/v1" or not {"graph", "constructor", "layoutArguments"} <= request.keys():
            raise ValueError("Invalid layout request")
        if not isinstance(request["constructor"], dict) or not isinstance(request["layoutArguments"], dict):
            raise ValueError("Constructor and layoutArguments must be objects")
        if case["expectedOutcome"] not in ("returned", "threw"):
            raise ValueError("Invalid expected outcome")
    return suite


def verify_capture(directory: Path):
    index = load(directory / "index.json")
    if index.get("schema") != "py-elk-layout-capture/v1" or index.get("status") != "CAPTURED" or not index.get("cases"):
        raise ValueError("Capture is empty, failed, or incomplete")
    if index.get("role") not in ("reference", "candidate") or type(index.get("repeat")) is not int or index["repeat"] < 1 or index.get("failures"):
        raise ValueError("Invalid capture role/repeat/failures")
    lock = load(ROOT / "UPSTREAM.json")
    if index["role"] == "reference" and (index["upstreamCommit"] != lock["javascript"]["commit"] or index["entrypointSha256"] != lock["distribution"]["sha256Files"]["lib/elk.bundled.js"]):
        raise ValueError("Reference baseline differs from UPSTREAM lock")
    for name, digest in index["files"].items():
        if sha256(contained(directory, name)) != digest:
            raise ValueError("Artifact SHA256 mismatch: " + name)
    actual_files = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file() and p != directory / "index.json"}
    if actual_files != set(index["files"]):
        raise ValueError("Capture file denominator differs")
    if "upstream-lock.json" not in index["files"] or sha256(directory / "upstream-lock.json") != index["upstreamLockSha256"]:
        raise ValueError("Captured upstream lock fingerprint differs")
    captured_lock = load(directory / "upstream-lock.json")
    if captured_lock["javascript"]["commit"] != index["upstreamCommit"]:
        raise ValueError("Captured upstream baseline differs")
    suite_path = contained(directory, "suite.json")
    if sha256(suite_path) != index["suiteSha256"]:
        raise ValueError("Suite SHA256 mismatch")
    suite = load(suite_path)
    if suite.get("schema") != "py-elk-validation-cases/v1" or "suite.json" not in index["files"]:
        raise ValueError("Invalid or unhashed captured suite")
    cases = index["cases"]
    if len(cases) != len(suite["cases"]) or [c["id"] for c in cases] != [c["id"] for c in suite["cases"]]:
        raise ValueError("Capture case denominator differs")
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate captured case")
    for case, definition in zip(cases, suite["cases"]):
        if case["definition"] != definition or len(case["observations"]) != index["repeat"] or not case["observations"]:
            raise ValueError("Case definition/repeat denominator differs")
        request = case["request"]
        if request not in index["files"] or sha256(contained(directory, request)) != case["requestSha256"]:
            raise ValueError("Request fingerprint mismatch")
        for name in case["observations"]:
            if name not in index["files"]:
                raise ValueError("Unhashed observation")
            observation = load(contained(directory, name))
            contract(observation)
            if observation["requestSha256"] != case["requestSha256"]:
                raise ValueError("Observation request fingerprint differs")
            if index["role"] == "reference" and (observation.get("engine", {}).get("name") != "elkjs" or observation["engine"].get("entrypointSha256") != index["entrypointSha256"]):
                raise ValueError("Reference observation identity differs")
            if index["role"] == "candidate" and observation.get("engine", {}).get("name") != "pyelk":
                raise ValueError("Candidate observation identity differs")
    return index


def seed_of(request):
    """Root local seed wins; explicit call options replace constructor defaults."""
    local = (request.get("graph") or {}).get("layoutOptions", {})
    args = request["layoutArguments"]
    options = args.get("layoutOptions", request["constructor"].get("defaultLayoutOptions", {}))
    for values in (local, options):
        for key in ("org.eclipse.elk.randomSeed", "elk.randomSeed", "randomSeed"):
            if key in values:
                raw = values[key]
                if type(raw) is int:
                    value = raw
                elif isinstance(raw, str) and re.fullmatch(r"[+-]?\d+", raw):
                    value = int(raw)
                else:
                    return None
                return value if -(2 ** 31) <= value < 2 ** 31 and value != 0 else None
    return None


def determinism(observations, request):
    if len(observations) < 2 or seed_of(request) is None:
        return {"passed": False, "status": "NOT_ESTABLISHED", "reason": "Need >=2 fresh runs and an explicit nonzero seed"}
    differences = [diff(contract(observations[0]), contract(other)) for other in observations[1:]]
    return {"passed": all(d["passed"] for d in differences), "status": "CHECKED", "repeats": len(observations), "comparisons": differences,
            "limitation": "Fresh processes only; same-instance lifecycle/concurrency not assessed."}


def compare_captures(reference_dir: Path, candidate_dir: Path, *, replay=False):
    reference, candidate = verify_capture(reference_dir), verify_capture(candidate_dir)
    if reference["role"] != "reference" or candidate["role"] != ("reference" if replay else "candidate"):
        raise ValueError("Expected reference and candidate roles; use selftest for reference-only checks")
    lock = load(ROOT / "UPSTREAM.json")
    if reference["upstreamCommit"] != lock["javascript"]["commit"] or reference["entrypointSha256"] != lock["distribution"]["sha256Files"]["lib/elk.bundled.js"]:
        raise ValueError("Reference baseline differs from UPSTREAM lock")
    if reference["suiteSha256"] != candidate["suiteSha256"]:
        raise ValueError("Reference/candidate suites differ")
    reports = []
    for r, c in zip(reference["cases"], candidate["cases"]):
        if r["requestSha256"] != c["requestSha256"]:
            raise ValueError("Reference/candidate request differs: " + r["id"])
        expected = [load(reference_dir / name) for name in r["observations"]]
        actual = [load(candidate_dir / name) for name in c["observations"]]
        request = load(reference_dir / r["request"])
        policy = r["definition"].get("geometry")
        comparisons = [compare_observations(expected[0], obs) for obs in actual]
        geometries = [geometry(request, obs, policy) for obs in actual]
        reference_geometry = [geometry(request, obs, policy) for obs in expected]
        rd, cd = determinism(expected, request), determinism(actual, request)
        outcome = all(obs["outcome"] == r["definition"]["expectedOutcome"] for obs in expected + actual)
        geometry_pass = all(g["passed"] is True for g in geometries + reference_geometry) if policy and outcome and actual[0]["outcome"] == "returned" else True
        passed = outcome and geometry_pass and rd["passed"] and cd["passed"] and all(d["coordinateTolerance"]["passed"] for d in comparisons)
        reports.append({"id": r["id"], "passed": passed, "expectedOutcomeMatched": outcome,
                        "comparison": comparisons, "geometry": geometries, "referenceGeometry": reference_geometry,
                        "referenceInputPreservation": [input_preservation(request, obs) for obs in expected],
                        "candidateInputPreservation": [input_preservation(request, obs) for obs in actual],
                        "referenceDeterminism": rd, "candidateDeterminism": cd,
                        "semanticConstraintsPassed": geometry_pass if policy else None})
    return {"schema": "py-elk-layout-comparison/v1", "status": ("REFERENCE_REPRODUCED" if replay else "SCOPED_CASES_MATCH") if all(r["passed"] for r in reports) else "FAIL",
            "passed": all(r["passed"] for r in reports), "caseCount": len(reports), "cases": reports,
            "tolerance": {"absolute": ABS_TOL, "relative": REL_TOL, "appliesTo": "geometry numeric paths only"},
            "referenceIndexSha256": sha256(reference_dir / "index.json"), "candidateIndexSha256": sha256(candidate_dir / "index.json"),
            "purpose": "reference replay; zero Python algorithms verified" if replay else "candidate differential check",
            "limitation": "Scoped differential evidence only; no automatic capability-ledger promotion, lifecycle or release acceptance."}


def negative_controls(reference_dir: Path, out: Path):
    index = verify_capture(reference_dir)
    if index["role"] != "reference":
        raise ValueError("Negative controls require an official reference capture")
    positive = next(c for c in index["cases"] if c["id"] == "layered-diamond-right")
    negative = next(c for c in index["cases"] if c["id"] == "error-unknown-endpoint")
    observation = load(reference_dir / positive["observations"][0])
    request = load(reference_dir / positive["request"])
    error_observation = load(reference_dir / negative["observations"][0])
    if observation["outcome"] != "returned" or error_observation["outcome"] != "threw":
        raise ValueError("Control fixture outcomes differ")
    controls = []

    def compare_control(name, base, mutate, expect=True):
        altered = copy.deepcopy(base)
        mutate(altered)
        result = compare_observations(base, altered)
        passed = result["coordinateTolerance"]["passed"] is expect
        write(out / (name + ".json"), {"alteredObservation": altered, "comparison": result})
        controls.append({"id": name, "passed": passed, "expectedMatch": expect})

    compare_control("identical-positive", observation, lambda o: None)
    compare_control("within-tolerance-positive", observation, lambda o: o["result"]["children"][0].update(x=o["result"]["children"][0]["x"] + ABS_TOL / 10))
    compare_control("coordinate-negative", observation, lambda o: o["result"]["children"][0].update(x=o["result"]["children"][0]["x"] + 1), False)
    compare_control("endpoint-negative", observation, lambda o: o["result"]["edges"][0]["targets"].__setitem__(0, "missing"), False)
    compare_control("field-deletion-negative", observation, lambda o: o["result"]["children"][0].pop("width"), False)
    compare_control("model-order-negative", observation, lambda o: o["result"]["children"].reverse(), False)
    compare_control("section-id-negative", observation, lambda o: o["result"]["edges"][0]["sections"][0].update(id="invented"), False)
    compare_control("option-default-negative", observation, lambda o: o["inputAfter"]["layoutOptions"].update({"elk.spacing.nodeNode": 999}), False)
    compare_control("seed-fingerprint-negative", observation, lambda o: o.update(requestSha256="0" * 64), False)
    compare_control("side-effect-negative", observation, lambda o: o["argumentsAfter"].update(layoutOptions={}), False)
    compare_control("business-number-negative", observation, lambda o: o["result"]["business"].update(weight=1e-9 + 1e-12), False)
    compare_control("boolean-type-negative", observation, lambda o: o["result"]["children"][0]["data"].update(enabled=1), False)
    compare_control("error-name-negative", error_observation, lambda o: o["error"].update(name="WrongError"), False)
    compare_control("error-message-negative", error_observation, lambda o: o["error"].update(message="wrong message"), False)

    geometric = copy.deepcopy(observation)
    geometric["result"]["children"][1].update(x=geometric["result"]["children"][0]["x"], y=geometric["result"]["children"][0]["y"])
    g = geometry(request, geometric, positive["definition"]["geometry"])
    write(out / "overlap-negative.json", {"alteredObservation": geometric, "geometry": g})
    controls.append({"id": "overlap-negative", "passed": g["passed"] is False and any(e["code"] == "node_overlap" for e in g["errors"])})
    for name, mutate, code in (
        ("root-bounds-negative", lambda o: o["result"].update(width=1), "root_padding_bounds"),
        ("detached-endpoint-negative", lambda o: o["result"]["edges"][0]["sections"][0]["startPoint"].update(x=-10, y=-10), "endpoint_not_on_node_border"),
        ("diagonal-negative", lambda o: o["result"]["edges"][0]["sections"][0].update(bendPoints=[{"x": -7, "y": -9}]), "non_orthogonal_segment"),
        ("section-connectivity-negative", lambda o: o["result"]["edges"][0]["sections"][0].update(incomingShape="missing"), "section_connectivity"),
    ):
        altered = copy.deepcopy(observation)
        mutate(altered)
        g = geometry(request, altered, positive["definition"]["geometry"])
        write(out / (name + ".json"), {"alteredObservation": altered, "geometry": g})
        controls.append({"id": name, "passed": g["passed"] is False and any(e["code"] == code for e in g["errors"])})
    altered = copy.deepcopy(observation)
    altered["result"]["children"][0]["x"] += 1
    det = determinism([observation, altered], request)
    write(out / "determinism-negative.json", det)
    controls.append({"id": "determinism-negative", "passed": det["passed"] is False})
    positives = []
    for case in index["cases"]:
        req = load(reference_dir / case["request"])
        observed = [load(reference_dir / name) for name in case["observations"]]
        geometry_checks = [geometry(req, o, case["definition"].get("geometry")) for o in observed]
        outcome_ok = all(o["outcome"] == case["definition"]["expectedOutcome"] for o in observed)
        det = determinism(observed, req)
        geometry_ok = all(g["passed"] is True for g in geometry_checks) if case["definition"].get("geometry") else True
        positives.append({"id": case["id"], "passed": outcome_ok and geometry_ok and det["passed"], "geometry": geometry_checks, "determinism": det})
    passed = all(c["passed"] for c in controls + positives)
    return {"schema": "py-elk-harness-selftest/v1", "status": "HARNESS_VERIFIED" if passed else "FAIL", "passed": passed,
            "controls": controls, "officialPositiveCases": positives, "pythonAlgorithmsVerified": 0,
            "limitation": "Reference/validator checks only; no Python layout implementation exercised."}
