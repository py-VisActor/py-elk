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
from source_read_cache import read_digest, read_json

ROOT = Path(__file__).resolve().parents[1]
ABS_TOL = 1e-6
REL_TOL = 1e-9
SCHEMA = "py-elk-layout-observation/v1"
NATIVE_PROFILE = "native-basic-layered-v1"
PROFILES = ("strict", NATIVE_PROFILE)


def sha256(path: Path) -> str:
    return read_digest(path)


def _parse_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result

    value = json.loads(text, object_pairs_hook=pairs,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError("Nonfinite JSON: " + token)))
    validate_json(value)
    return value


def load(path: Path):
    return read_json(path, _parse_json)


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


def _raw_comparison(expected, actual):
    a, b = contract(expected), contract(actual)
    return {"exact": diff(a, b), "coordinateTolerance": diff(a, b, tolerant=True),
            "lifecycleObservations": {"reference": expected.get("termination"), "candidate": actual.get("termination"),
                                      "acceptance": "NOT_ASSESSED"}}


def _native_request_context(request, expected, actual):
    """Only original bytes establish an observation's request identity."""
    if isinstance(request, Path):
        raw = request.read_bytes()
    elif isinstance(request, bytes):
        raw = request
    else:
        raise ValueError("Native profile requires the original request Path or bytes")
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("Duplicate JSON key: " + key)
            value[key] = item
        return value
    context = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                         parse_constant=lambda token: (_ for _ in ()).throw(ValueError("Nonfinite JSON: " + token)))
    validate_json(context)
    if (not isinstance(context, dict) or context.get("schema") != "py-elk-layout-request/v1"
            or not {"constructor", "graph", "layoutArguments"} <= context.keys()):
        raise ValueError("Invalid native request context schema")
    digest = hashlib.sha256(raw).hexdigest()
    if any(observation["requestSha256"] != digest for observation in (expected, actual)):
        raise ValueError("Native request fingerprint differs from original bytes")
    lock = load(ROOT / "UPSTREAM.json")
    reference_engine, candidate_engine = expected.get("engine", {}), actual.get("engine", {})
    if (not isinstance(reference_engine, dict) or reference_engine.get("name") != "elkjs"
            or reference_engine.get("version") != lock["javascript"]["version"]
            or reference_engine.get("entrypoint") != "lib/elk.bundled.js"
            or reference_engine.get("entrypointSha256") != lock["distribution"]["sha256Files"]["lib/elk.bundled.js"]):
        raise ValueError("Native profile reference engine identity differs")
    if not isinstance(candidate_engine, dict) or candidate_engine.get("name") != "pyelk":
        raise ValueError("Native profile requires a pyelk candidate observation")
    if not isinstance(context["constructor"], dict) or not isinstance(context["layoutArguments"], dict):
        raise ValueError("Native profile constructor and arguments must be mappings")
    if any(key in context["constructor"] for key in ("workerUrl", "workerFactory")):
        raise ValueError("Explicit worker parameters are outside native profile scope")
    return context, digest, lock


def _native_definition(lock):
    path = ROOT / "references/native-contract.json"
    definition = load(path)
    expected_baseline = {"upstreamVersion": lock["javascript"]["version"],
                         "upstreamCommit": lock["javascript"]["commit"],
                         "entrypoint": "lib/elk.bundled.js",
                         "entrypointSha256": lock["distribution"]["sha256Files"]["lib/elk.bundled.js"]}
    if (definition.get("schema") != "py-elk-native-contract/v1" or definition.get("profileId") != NATIVE_PROFILE
            or definition.get("status") != "frozen-design" or type(definition.get("revision")) is not int
            or definition["revision"] != 1 or definition.get("baseline") != expected_baseline):
        raise ValueError("Native profile definition identity differs")
    return {"path": "references/native-contract.json", "sha256": sha256(path), "revision": 1}


def _native_success_scope(request):
    """Conservative v1 scope, selected by key presence rather than truthiness."""
    graph, constructor, arguments = request["graph"], request["constructor"], request["layoutArguments"]
    if not isinstance(graph, dict):
        raise ValueError("Successful native profile requires a flat graph mapping")
    if "algorithms" in constructor:
        algorithms = constructor["algorithms"]
        if not isinstance(algorithms, list) or any(not isinstance(value, str) for value in algorithms) or "layered" not in algorithms:
            raise ValueError("Successful native profile requires layered to be registered")
    for flag in ("logging", "measureExecutionTime"):
        if flag in arguments and type(arguments[flag]) is not bool:
            raise ValueError("Native profile logging/timing flags must be booleans")
    option_sets = []
    for owner, key in ((constructor, "defaultLayoutOptions"), (arguments, "layoutOptions"), (graph, "layoutOptions")):
        options = owner[key] if key in owner else {}
        if not isinstance(options, dict):
            raise ValueError("Native profile option containers must be mappings or absent")
        option_sets.append(options)
    for options in option_sets:
        for selector in ("algorithm", "edgeRouting"):
            keys = ("org.eclipse.elk." + selector, "elk." + selector)
            found = [key for key in keys if key in options]
            if len(found) > 1 or selector in options:
                raise ValueError("Ambiguous or bare selector is outside native profile scope")
            if any(key.endswith("." + selector) and key not in keys for key in options):
                raise ValueError("Unknown selector form is outside native profile scope")
        for key, value in options.items():
            if key.endswith(("shapeCoords", "edgeCoords")) and value != "INHERIT":
                raise ValueError("Alternate coordinate frame is outside native profile scope")
            if key.endswith("hierarchyHandling") and value == "INCLUDE_CHILDREN":
                raise ValueError("Hierarchy-aware execution is outside native profile scope")
    global_options = option_sets[1] if "layoutOptions" in arguments else option_sets[0]
    for selector, accepted in (("algorithm", ("layered", "org.eclipse.elk.layered")), ("edgeRouting", ("ORTHOGONAL",))):
        present, value = False, None
        for options in (option_sets[2], global_options):
            keys = [key for key in ("org.eclipse.elk." + selector, "elk." + selector) if key in options]
            if keys:
                present, value = True, options[keys[0]]
                break
        if present and (not isinstance(value, str) or value not in accepted):
            raise ValueError("Successful selector is outside native profile scope: " + selector)
    _native_flat_graph_scope(graph)


def _native_flat_graph_scope(graph):
    """Check model scope for input and each result without resolving selectors."""
    if not isinstance(graph, dict):
        raise ValueError("Native profile requires a flat graph mapping")
    children = graph["children"] if "children" in graph else []
    edges = graph["edges"] if "edges" in graph else []
    if not isinstance(children, list) or not isinstance(edges, list):
        raise ValueError("Native profile child and edge collections must be arrays")
    identities = set()
    for shape in (graph, *children):
        if not isinstance(shape, dict) or not isinstance(shape.get("id"), str) or not shape["id"] or shape["id"] in identities:
            raise ValueError("Native profile shapes require unique string identities")
        identities.add(shape["id"])
        for key in ("ports", "labels"):
            if key in shape and (not isinstance(shape[key], list) or shape[key]):
                raise ValueError("Ports/labels are outside native profile scope")
        if "layoutOptions" in shape:
            shape_options = shape["layoutOptions"]
            if not isinstance(shape_options, dict):
                raise ValueError("Native profile shape option containers must be mappings or absent")
            for key, value in shape_options.items():
                if key.endswith(("shapeCoords", "edgeCoords")) and value != "INHERIT":
                    raise ValueError("Alternate shape coordinate frame is outside native profile scope")
                if key.endswith("hierarchyHandling") and value == "INCLUDE_CHILDREN":
                    raise ValueError("Hierarchy-aware shape execution is outside native profile scope")
        if shape is not graph:
            for key in ("children", "edges"):
                if key in shape and (not isinstance(shape[key], list) or shape[key]):
                    raise ValueError("Nested graphs are outside native profile scope")
            if any(not number(shape.get(key)) or shape[key] < 0 for key in ("width", "height")):
                raise ValueError("Native profile requires given finite nonnegative node dimensions")
    node_ids = {node["id"] for node in children}
    for edge in edges:
        if (not isinstance(edge, dict) or not isinstance(edge.get("id"), str) or not edge["id"] or edge["id"] in identities
                or any(key in edge for key in ("source", "target"))):
            raise ValueError("Native profile requires unique extended edge identities")
        identities.add(edge["id"])
        if any(not isinstance(edge.get(key), list) or len(edge[key]) != 1
               or not isinstance(edge[key][0], str) or edge[key][0] not in node_ids for key in ("sources", "targets")):
            raise ValueError("Native profile requires one known source and target per edge")
        if "labels" in edge and (not isinstance(edge["labels"], list) or edge["labels"]):
            raise ValueError("Edge labels are outside native profile scope")


def _project_reference_shape_hashes(original, reference, candidate, *, prefix, adaptations, violations):
    """Project only a reference-generated shape field at identity-preserving paths."""
    if not isinstance(original, dict):
        return
    if not isinstance(reference, dict) or not isinstance(candidate, dict):
        violations.append({"path": prefix, "reason": "Shape mappings are required for identity-preserving projection"})
        return
    def visit(before, after, native, path):
        if not isinstance(before, dict):
            return
        if not isinstance(after, dict) or not isinstance(native, dict):
            violations.append({"path": path, "reason": "Shape mapping differs"})
            return
        if any(not diff(before.get("id"), value.get("id"))["passed"] for value in (after, native)):
            violations.append({"path": path, "reason": "Shape identity differs; generated-field projection is forbidden"})
            return
        if "$H" in before:
            for label, shape in (("reference", after), ("candidate", native)):
                if "$H" not in shape or not diff(before["$H"], shape["$H"])["passed"]:
                    violations.append({"path": path + "/$H", "reason": "User-provided shape field changed", "side": label})
            return
        if "$H" in native:
            violations.append({"path": path + "/$H", "reason": "Candidate supplied an unrequested shape field"})
            return
        if "$H" in after:
            if "id" not in before or "id" not in after or "id" not in native:
                violations.append({"path": path, "reason": "A generated shape field requires explicit matching identities"})
                return
            value = after["$H"]
            try:
                finite_integer = number(value) and value == math.trunc(value)
            except OverflowError:
                finite_integer = False
            if not finite_integer:
                violations.append({"path": path + "/$H", "reason": "Reference-generated shape field is not a finite integer"})
                return
            del after["$H"]
            adaptations.append({"rule": "GWT-SHAPE-HASH-01", "path": path + "/$H", "referenceValue": value,
                                "action": "omit_reference_added_shape_field", "candidateRequirement": "absent"})
    visit(original, reference, candidate, prefix)
    old_nodes = original.get("children", [])
    ref_nodes, candidate_nodes = reference.get("children", []), candidate.get("children", [])
    if not all(isinstance(value, list) for value in (old_nodes, ref_nodes, candidate_nodes)):
        violations.append({"path": prefix + "/children", "reason": "Child collections are not matching arrays"})
        return
    if len(old_nodes) != len(ref_nodes) or len(old_nodes) != len(candidate_nodes):
        violations.append({"path": prefix + "/children", "reason": "Child count differs; generated-field projection is forbidden"})
        return
    for i, (before, after, native) in enumerate(zip(old_nodes, ref_nodes, candidate_nodes)):
        visit(before, after, native, prefix + f"/children/{i}")


def compare_observations(expected, actual, *, profile="strict", request=None):
    if profile not in PROFILES:
        raise ValueError("Unknown comparison profile: " + str(profile))
    raw = _raw_comparison(expected, actual)
    raw_strict = {"exact": raw["exact"], "coordinateTolerance": raw["coordinateTolerance"],
                  "passed": raw["coordinateTolerance"]["passed"]}
    report = {**raw, "profile": profile, "rawStrict": raw_strict, "adaptations": [],
              "inputPreservation": {"preserved": None, "acceptance": "NOT_ASSESSED"},
              "publicContract": {**raw_strict, "violations": []}, "passed": raw_strict["passed"]}
    if profile == "strict":
        return report
    context, digest, lock = _native_request_context(request, expected, actual)
    report["profileDefinition"] = _native_definition(lock)
    report["requestSha256"] = digest
    if expected["outcome"] == "returned":
        _native_success_scope(context)
    preservation = input_preservation(context, actual)
    preservation["acceptance"] = "REQUIRED_BY_PROFILE"
    report["inputPreservation"] = preservation
    public_expected, public_actual = copy.deepcopy(contract(expected)), contract(actual)
    violations, adaptations = [], []
    for key, after in (("constructor", "constructorAfter"), ("layoutArguments", "argumentsAfter")):
        if not diff(context[key], expected[after])["passed"]:
            violations.append({"path": "/" + after, "reason": "Reference mutated a non-adaptable call input"})
    matched_outcomes = expected["outcome"] == actual["outcome"]
    if not matched_outcomes:
        violations.append({"path": "/outcome", "reason": "Observation outcomes differ"})
    elif expected["outcome"] == "returned":
        for side, observation in (("reference", expected), ("candidate", actual)):
            try:
                _native_flat_graph_scope(observation["result"])
            except ValueError as error:
                violations.append({"path": "/result", "reason": str(error), "side": side})
        if not diff(expected["inputAfter"], expected["result"])["passed"]:
            violations.append({"path": "/inputAfter", "reason": "Successful reference inputAfter does not exactly equal result"})
        _project_reference_shape_hashes(context["graph"], public_expected["result"], actual["result"],
                                        prefix="/result", adaptations=adaptations, violations=violations)
    else:
        reduced_input = copy.deepcopy(expected["inputAfter"])
        _project_reference_shape_hashes(context["graph"], reduced_input, actual["inputAfter"],
                                        prefix="/inputAfter", adaptations=adaptations, violations=violations)
        if not diff(context["graph"], reduced_input)["passed"]:
            violations.append({"path": "/inputAfter", "reason": "Reference error changed fields beyond verified shape hashes"})
    if matched_outcomes and not violations:
        for change in diff(context["graph"], expected["inputAfter"])["differences"]:
            adaptations.append({"rule": "NATIVE-INPUT-01", "path": "/inputAfter" + change["path"],
                                "action": "compare_candidate_to_original_request", "referenceChange": change})
        public_expected["inputAfter"] = copy.deepcopy(context["graph"])
    else:
        # No partially satisfied rule can make an unsupported reference contract pass.
        public_expected = copy.deepcopy(contract(expected))
        adaptations = []
    exact, tolerant = diff(public_expected, public_actual), diff(public_expected, public_actual, tolerant=True)
    report["adaptations"] = adaptations
    report["publicContract"] = {"exact": exact, "coordinateTolerance": tolerant, "violations": violations,
                                "passed": tolerant["passed"] and preservation["preserved"] and not violations}
    report["passed"] = report["publicContract"]["passed"]
    return report


def input_preservation(request, observation):
    """Report the native-Python nonmutation goal independently from literal JS parity."""
    checks = {name: diff(request[key], observation[name]) for key, name in
              (("graph", "inputAfter"), ("constructor", "constructorAfter"), ("layoutArguments", "argumentsAfter"))}
    return {"preserved": all(item["passed"] for item in checks.values()), "comparisons": checks,
            "acceptance": "OBSERVATION_ONLY; explicit cross-engine side-effect policy remains an M1 decision"}


def is_default_simple_ring(request):
    """Original-input-only premise for the reviewed GREEDY/NS ring lemma.

    A connected directed simple ring becomes a Hamiltonian chain plus one
    shortcut after default GREEDY. Unit-minimum NETWORK_SIMPLEX ranks are
    distinct. This says nothing about arbitrary strongly connected graphs.
    Advanced strategies and local options deliberately fail closed.
    """
    try:
        original = request["graph"]
        nodes, edges = original["children"], original["edges"]
        if not 2 <= len(nodes) <= 8 or len(edges) != len(nodes):
            return False
        if any(item.get(key) for item in [original, *nodes, *edges]
               for key in ("ports", "labels", "properties")):
            return False
        if any(node.get(key) for node in nodes for key in ("children", "edges", "layoutOptions")):
            return False
        if any(edge.get("layoutOptions") for edge in edges):
            return False
        allowed = {"algorithm", "direction", "edgeRouting", "randomSeed", "padding",
                   "separateConnectedComponents", "spacing.nodeNode", "spacing.componentComponent",
                   "layered.spacing.nodeNodeBetweenLayers"}
        constructor, arguments = request.get("constructor", {}), request.get("layoutArguments", {})
        if set(constructor) - {"defaultLayoutOptions", "algorithms"} or set(arguments) - {"layoutOptions", "logging", "measureExecutionTime"}:
            return False
        if "algorithms" in constructor and constructor["algorithms"] != ["layered"]:
            return False
        effective = {}
        defaults = arguments.get("layoutOptions", constructor.get("defaultLayoutOptions", {}))
        for container in (defaults, original.get("layoutOptions", {})):
            normalized = {}
            for key, value in container.items():
                name = key.removeprefix("org.eclipse.elk.").removeprefix("elk.")
                if name not in allowed or (name in normalized and normalized[name] != value):
                    return False
                normalized[name] = value
            effective.update(normalized)
        if effective.get("algorithm", "layered") not in ("layered", "elk.layered", "org.eclipse.elk.layered"):
            return False
        if effective.get("direction", "UNDEFINED") not in ("UNDEFINED", "RIGHT") or effective.get("edgeRouting", "ORTHOGONAL") != "ORTHOGONAL":
            return False
        identities = [node["id"] for node in nodes]
        if any(type(identity) is not str or not identity for identity in identities) or len(set(identities)) != len(nodes):
            return False
        successor, predecessors = {}, set()
        for edge in edges:
            if len(edge["sources"]) != 1 or len(edge["targets"]) != 1:
                return False
            source, target = edge["sources"][0], edge["targets"][0]
            if source not in identities or target not in identities or source == target or source in successor or target in predecessors:
                return False
            successor[source] = target
            predecessors.add(target)
        visited, current = set(), identities[0]
        while current not in visited:
            visited.add(current)
            current = successor[current]
        return current == identities[0] and len(visited) == len(nodes)
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


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
    ring_layers = False
    component_premise = None
    independent_frames = "layerFrame" in policy
    rank_v2 = policy.get("rankSeparation") == "default-layered-components-v2"
    rank_v3 = policy.get("rankSeparation") == "default-layered-adjacent-edge-v3"
    if independent_frames or rank_v2 or rank_v3:
        if rank_v3:
            from e09_geometry_premise import premises
        else:
            from e07_geometry_premise import premises
        component_premise = premises(request)
        frame_valid = (policy.get("layerFrame") == "independent-components-v1" and component_premise is not None
                       and component_premise["options"]["separateConnectedComponents"] is True)
        if independent_frames and not frame_valid:
            return {"status": "FAIL", "passed": False, "errors": [{"path": "/graph", "code": "layer_frame_premise"}]}
        if component_premise is None or policy.get("direction") != component_premise["options"]["direction"]:
            return {"status": "FAIL", "passed": False, "errors": [{"path": "/graph", "code": "rank_separation_premise"}]}
        selected = component_premise["options"]
        if (policy.get("padding") != selected["padding"] or policy.get("nodeNode") != selected["spacing.nodeNode"]
                or policy.get("betweenLayers") != selected["layered.spacing.nodeNodeBetweenLayers"]
                or ("componentRectangleGap" in policy and policy["componentRectangleGap"] != selected["spacing.componentComponent"])):
            return {"status": "FAIL", "passed": False, "errors": [{"path": "/graph", "code": "geometry_option_premise"}]}
    if "rankSeparation" in policy:
        if policy["rankSeparation"] not in ("default-greedy-simple-ring-v1", "default-layered-components-v2", "default-layered-adjacent-edge-v3"):
            raise ValueError("Unknown rank separation policy")
        if not (rank_v2 or rank_v3) and not is_default_simple_ring(request):
            return {"status": "FAIL", "passed": False, "errors": [{"path": "/graph", "code": "rank_separation_premise"}]}
        ring_layers = not (rank_v2 or rank_v3)
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
    for index, (before, after) in enumerate(zip(original.get("edges", []), edges)):
        if any(before.get(key) != after.get(key) for key in ("sources", "targets")):
            error("/result/edges/" + str(index), "original_endpoint_identity")
    for n in source_nodes:
        if n.get("id") in by_id:
            _, _, w, h, p = by_id[n["id"]]
            if not close(w, n["width"]) or not close(h, n["height"]):
                error(p, "given_node_dimensions")

    horizontal = direction in ("LEFT", "RIGHT")
    # Equal axis coordinates do not prove equal layers: zero-width/height
    # nodes and zero layer spacing can put distinct DAG layers at one x/y.
    # Only the original input's acyclic reachability may disprove that guess;
    # never trust a candidate's rewritten edge endpoints to waive spacing.
    reaches = {}
    if policy.get("forwardEdges") is True:
        adjacency = {identity: set() for identity in by_id}
        valid_dag = True
        for edge in original.get("edges", []):
            sources, targets = edge.get("sources"), edge.get("targets")
            if (not isinstance(sources, list) or not isinstance(targets, list) or len(sources) != 1 or len(targets) != 1
                    or not isinstance(sources[0], str) or not isinstance(targets[0], str)
                    or sources[0] not in adjacency or targets[0] not in adjacency):
                valid_dag = False
                break
            adjacency[sources[0]].add(targets[0])
        indegrees = {identity: 0 for identity in adjacency}
        for targets in adjacency.values():
            for target in targets:
                indegrees[target] += 1
        ready = [identity for identity, degree in indegrees.items() if degree == 0]
        visited = 0
        while ready:
            identity = ready.pop()
            visited += 1
            for target in adjacency[identity]:
                indegrees[target] -= 1
                if indegrees[target] == 0:
                    ready.append(target)
        if valid_dag and visited == len(adjacency):
            for identity in adjacency:
                descendants, pending = set(), list(adjacency[identity])
                while pending:
                    target = pending.pop()
                    if target not in descendants:
                        descendants.add(target)
                        pending.extend(adjacency[target])
                reaches[identity] = descendants
    boxes = list(by_id.items())
    for i, (identity, (x, y, w, h, p)) in enumerate(boxes):
        for other, (xx, yy, ww, hh, pp) in boxes[i + 1:]:
            if min(x + w, xx + ww) - max(x, xx) > ABS_TOL and min(y + h, yy + hh) - max(y, yy) > ABS_TOL:
                error(p, "node_overlap", pp)
            same_layer = close(x, xx) if horizontal else close(y, yy)
            gap = max(yy - y - h, y - yy - hh) if horizontal else max(xx - x - w, x - xx - ww)
            different_dag_layers = other in reaches.get(identity, ()) or identity in reaches.get(other, ())
            distinct_source_ranks = (rank_v2 or rank_v3) and frozenset((identity, other)) in component_premise["distinctRanks"]
            separate_frames = (independent_frames and identity in component_premise["membership"] and other in component_premise["membership"]
                               and component_premise["membership"][identity] != component_premise["membership"][other])
            if same_layer and not different_dag_layers and not ring_layers and not distinct_source_ranks and not separate_frames and gap < policy["nodeNode"] - ABS_TOL:
                error(p, "same_layer_spacing", pp)
    checked.extend(["model identity/order", "given dimensions", "sibling overlap", "same layer spacing"])
    if ring_layers:
        checked.append("explicit original simple-ring distinct-rank source lemma")
    if rank_v2:
        checked.append("original per-component DAG/simple-ring distinct-rank source lemmas")
    if rank_v3:
        checked.append("original guarded adjacent-nonself-edge plus DAG/simple-ring distinct-rank source lemmas")
    if independent_frames:
        checked.append("original independent component frames; other geometry checks remain active")

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


DETERMINISM_POLICIES = ("explicit-nonzero-seed", "elkjs-0.12.1-default-seed-v1")


def _default_seed_evidence():
    policy = load(ROOT / "references/e04-determinism-policy.json")
    lock = load(ROOT / "UPSTREAM.json")
    baseline = {"version": lock["javascript"]["version"], "commit": lock["javascript"]["commit"],
                "entrypointSha256": lock["distribution"]["sha256Files"]["lib/elk.bundled.js"]}
    evidence = policy["sourceEvidence"]
    if (policy["schema"] != "py-elk-determinism-policy/v1" or policy["id"] != DETERMINISM_POLICIES[1]
            or policy["status"] != "source-reviewed" or type(policy["defaultSeed"]) is not int or policy["defaultSeed"] != 1
            or not diff(policy["baseline"], baseline)["passed"]
            or evidence["path"] != "references/e03-option-sources.json" or evidence["optionId"] != "org.eclipse.elk.randomSeed"
            or sha256(contained(ROOT, evidence["path"])) != evidence["sha256"]):
        raise ValueError("Default seed policy is not bound to the fixed source evidence")
    options = load(contained(ROOT, evidence["path"]))["options"]
    default = next(item["declaredDefault"] for item in options if item["id"] == evidence["optionId"])
    if type(default) is not int or default != 1:
        raise ValueError("Fixed reference default seed differs")
    return policy


def _seed_is_omitted(request):
    constructor, arguments = request["constructor"], request["layoutArguments"]
    graph = request.get("graph")
    if not isinstance(constructor, dict) or not isinstance(arguments, dict) or not isinstance(graph, dict):
        return False
    local = graph.get("layoutOptions", {})
    selected = arguments.get("layoutOptions", constructor.get("defaultLayoutOptions", {}))
    return (isinstance(local, dict) and isinstance(selected, dict)
            and not any(key in values for values in (local, selected)
                        for key in ("org.eclipse.elk.randomSeed", "elk.randomSeed", "randomSeed")))


def _seed_alias_conflict(request):
    graph, constructor, arguments = request.get("graph"), request.get("constructor"), request.get("layoutArguments")
    if not isinstance(graph, dict) or not isinstance(constructor, dict) or not isinstance(arguments, dict):
        return False
    selected = arguments.get("layoutOptions", constructor.get("defaultLayoutOptions", {}))
    return any(isinstance(values, dict) and sum(key in values for key in
               ("org.eclipse.elk.randomSeed", "elk.randomSeed", "randomSeed")) > 1
               for values in (graph.get("layoutOptions", {}), selected))


def determinism(observations, request, *, policy="explicit-nonzero-seed"):
    if policy not in DETERMINISM_POLICIES:
        raise ValueError("Unknown determinism policy")
    seed = seed_of(request)
    default_evidence = None
    if policy == DETERMINISM_POLICIES[1]:
        default_evidence = _default_seed_evidence()
        for observed in observations:
            engine = observed.get("engine", {})
            if engine.get("name") not in ("elkjs", "pyelk"):
                raise ValueError("Default seed policy requires a known reference/native engine")
            if engine["name"] == "elkjs" and (engine.get("version") != default_evidence["baseline"]["version"]
                    or engine.get("entrypointSha256") != default_evidence["baseline"]["entrypointSha256"]):
                raise ValueError("Default seed policy reference entrypoint differs")
        if _seed_alias_conflict(request):
            seed = None
        elif seed is None and _seed_is_omitted(request):
            seed = default_evidence["defaultSeed"]
    if len(observations) < 2 or seed is None:
        reason = ("Need >=2 fresh runs and an explicit nonzero seed" if policy == DETERMINISM_POLICIES[0]
                  else "Need >=2 fresh runs and an unambiguous nonzero seed, explicit or source-proven omitted default")
        return {"passed": False, "status": "NOT_ESTABLISHED", "reason": reason}
    differences = [diff(contract(observations[0]), contract(other)) for other in observations[1:]]
    report = {"passed": all(d["passed"] for d in differences), "status": "CHECKED", "repeats": len(observations), "comparisons": differences,
              "limitation": "Fresh processes only; same-instance lifecycle/concurrency not assessed."}
    if default_evidence:
        report.update(policy=policy, seed=seed, seedSource="fixed-source-default" if _seed_is_omitted(request) else "explicit-request",
                      sourceEvidence=default_evidence["sourceEvidence"])
    return report


def compare_captures(reference_dir: Path, candidate_dir: Path, *, replay=False, profile="strict", determinism_policy="explicit-nonzero-seed"):
    if determinism_policy not in DETERMINISM_POLICIES:
        raise ValueError("Unknown determinism policy")
    if profile not in PROFILES:
        raise ValueError("Unknown comparison profile: " + str(profile))
    if replay and profile != "strict":
        raise ValueError("Reference replay requires the strict profile")
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
        comparisons = [compare_observations(expected[0], obs, profile=profile,
                                            request=reference_dir / r["request"] if profile != "strict" else None)
                       for obs in actual]
        geometries = [geometry(request, obs, policy) for obs in actual]
        reference_geometry = [geometry(request, obs, policy) for obs in expected]
        rd, cd = determinism(expected, request, policy=determinism_policy), determinism(actual, request, policy=determinism_policy)
        outcome = all(obs["outcome"] == r["definition"]["expectedOutcome"] for obs in expected + actual)
        geometry_pass = all(g["passed"] is True for g in geometries + reference_geometry) if policy and outcome and actual[0]["outcome"] == "returned" else True
        passed = outcome and geometry_pass and rd["passed"] and cd["passed"] and all(d["passed"] for d in comparisons)
        reports.append({"id": r["id"], "passed": passed, "expectedOutcomeMatched": outcome,
                        "comparison": comparisons, "geometry": geometries, "referenceGeometry": reference_geometry,
                        "referenceInputPreservation": [input_preservation(request, obs) for obs in expected],
                        "candidateInputPreservation": [input_preservation(request, obs) for obs in actual],
                        "referenceDeterminism": rd, "candidateDeterminism": cd,
                        "semanticConstraintsPassed": geometry_pass if policy else None})
    return {"schema": "py-elk-layout-comparison/v1", "profile": profile, "determinismPolicy": determinism_policy,
            "status": ("REFERENCE_REPRODUCED" if replay else "SCOPED_CASES_MATCH") if all(r["passed"] for r in reports) else "FAIL",
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
