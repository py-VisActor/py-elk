"""Replay saved port primitive observations against an isolated native source tree.

This command imports the requested private source and executes only its local
helpers/importer. It never starts Node, lays out a graph, installs a wheel, or
turns historical primitive evidence into full algorithm acceptance.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "tests/fixtures/suites/next-native"
WORKER_SHA = "275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86"
COUNTS = {"init": 12, "order": 8, "import": 2, "adapter": 1}
sys.path.insert(0, str(ROOT / "scripts"))
from layout_checks import diff as json_diff


def same_json(actual, expected):
    """JSON values: booleans differ from numbers; no geometry tolerance."""
    return json_diff(expected, actual, tolerant=False)["passed"]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_bytes())


def basename(value):
    cls = PureWindowsPath if "\\" in value or re.match(r"^[A-Za-z]:", value) else PurePosixPath
    return cls(value).name


def raw64(value):
    return base64.b64decode(value, validate=True)


def command_check(command, observation, probe_name):
    require(type(command["exitCode"]) is int and command["exitCode"] == 0,
            "Original reference command failed")
    require(len(command["argv"]) >= 2 and basename(command["argv"][1]) == probe_name,
            "Original reference probe role differs")
    require(type(command["pid"]) is int and command["pid"] > 0
            and observation["pid"] == command["pid"], "Original observation/command PID differs")
    require(observation["workerSha256"] == WORKER_SHA, "Original fixed worker identity differs")


def embedded_reference(wrapper, request_path, probe_name, suite):
    request_raw = raw64(wrapper["requestBytesBase64"])
    require(request_raw == request_path.read_bytes(), "Saved original request bytes differ")
    raw = raw64(wrapper["observationBytesBase64"])
    require(digest(raw) == wrapper["observationSha256"], "Original observation digest differs")
    value = json.loads(raw)
    require(value["requestSha256"] == digest(request_raw), "Original request/observation link differs")
    require(value["candidateExecuted"] is False, "Reference observation contains a candidate execution")
    command_check(wrapper["command"], value, probe_name)
    for stream in ("stdout", "stderr"):
        require(digest(raw64(wrapper[stream + "BytesBase64"])) == wrapper["command"][stream + "Sha256"],
                "Original command log digest differs")
    expected_probe = wrapper.get("probeSha256", value.get("probeSha256"))
    require(expected_probe == digest((suite / probe_name).read_bytes()), "Original probe source bytes differ")
    return json.loads(request_raw), value


def modules(source):
    source = source.resolve()
    sys.path.insert(0, str(source))
    package = importlib.import_module("pyelk")
    require(Path(package.__file__).resolve() == source / "pyelk/__init__.py",
            "Imported pyelk is not the requested private source")
    return {name: importlib.import_module("pyelk." + name) for name in (
        "algorithms.layered.graph", "algorithms.layered.ports", "algorithms.layered.node_size",
        "algorithms.layered.import_export", "execution.context")}


def source_files(source):
    package = source / "pyelk"
    require(package.is_dir(), "Private pyelk source directory is missing")
    return {p.relative_to(source).as_posix(): digest(p.read_bytes())
            for p in sorted(package.rglob("*")) if p.is_file()
            and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def init_rows(api, suite):
    g, p = api["algorithms.layered.graph"], api["algorithms.layered.ports"]
    request, observation = embedded_reference(load(suite / "ports-helper-oracle.json"),
        suite / "ports-helper-request.json", "ports-helper-probe.cjs", suite)
    require(observation["proposalSha256"] == digest((suite / "ports-init-source-original.json").read_bytes()),
            "Original initialization source snapshot differs")
    rows = []
    for case, expected in zip(request["cases"], observation["cases"], strict=True):
        node = g.LNode(g.LGraph(None, None, None), size=g.Vec2(*case["nodeSize"]))
        port = g.LPort(owner=node, side=case["side"], pos=g.Vec2(*case["position"]),
            size=g.Vec2(*case["portSize"]), anchor=g.Vec2(*case["anchor"]),
            properties=copy.deepcopy(case["properties"]))
        inferred = p.calc_port_side(port, case["direction"])
        anchor = g.Vec2(*case["explicitAnchor"]) if case.get("explicitAnchor") is not None else None
        p.initialize_port(port, case["constraints"], case["direction"], anchor)
        if "sideAfter" in case:
            p.set_side(port, case["sideAfter"])
        actual = dict(id=case["id"], inferredSide=inferred, side=port.side,
            anchor=[port.anchor.x, port.anchor.y], properties=port.properties,
            explicitlySuppliedPortAnchor=port.explicitly_supplied_port_anchor)
        rows.append(dict(id=case["id"], passed=same_json(actual, expected), actual=actual, expected=expected))
    return rows


def order_rows(api, suite):
    g, p = api["algorithms.layered.graph"], api["algorithms.layered.ports"]
    wrapper = load(suite / "ports-order-oracle.json")
    request, observation = embedded_reference(wrapper,
        suite / "ports-order-request.json", "ports-order-probe.cjs", suite)
    originals = ("ports-init-source-original.json", "ports-order-source-original.json", "ports-sort-source-original.json")
    paths = wrapper["command"]["argv"][3:6]
    actual_sources = observation["sourceFilesSha256"]
    require(len(paths) == 3 and set(actual_sources) == set(paths)
            and all(actual_sources[path] == digest((suite / name).read_bytes())
                    for path, name in zip(paths, originals, strict=True)),
            "Original order/sort source snapshot roles differ")
    rows = []
    for case, expected in zip(request["cases"], observation["cases"], strict=True):
        graph = g.LGraph(None, None, None)
        node = g.LNode(graph, properties={"PORT_CONSTRAINTS": case["constraints"]})
        for item in case["ports"]:
            port = g.LPort(id=item["id"], side=item["side"], pos=g.Vec2(*item["position"]))
            if "index" in item:
                port.properties["PORT_INDEX"] = item["index"]
            if "dummySide" in item:
                port.properties["PORT_DUMMY"] = g.LNode(graph, properties={"EXT_PORT_SIDE": item["dummySide"]})
            port.incoming_edges = [g.LEdge(properties={"REVERSED": x}) for x in item.get("incoming", [])]
            port.outgoing_edges = [g.LEdge(properties={"REVERSED": x}) for x in item.get("outgoing", [])]
            g.set_port_owner(port, node)
        if case.get("layerless"):
            graph.layerless_nodes = [node]
        else:
            graph.layers = [g.Layer(graph, [node])]
        if case.get("processSides"):
            p.process_port_sides(graph)
        p.sort_port_lists(graph, case.get("strategy", "INPUT_ORDER"))
        actual = dict(id=case["id"], portOrder=[v.id for v in node.ports], sides=[v.side for v in node.ports],
            constraints=node.properties["PORT_CONSTRAINTS"], cached=node.port_sides_cached,
            ranges={k: list(v) for k, v in node.port_side_indices.items()})
        rows.append(dict(id=case["id"], passed=same_json(actual, expected), actual=actual, expected=expected))
    return rows


def import_rows(api, suite):
    reference = load(suite / "ports-import-oracle.json")
    rows = []
    for entry in reference["cases"]:
        request, observation = embedded_reference(entry, suite / (entry["id"] + ".json"),
                                                  "ports-import-probe.cjs", suite)
        require(entry["readOnlyApiResultExactToOriginal"] is True and len(observation["imports"]) == 1,
                "Saved read-only importer marker or snapshot count differs; marker is not independently reauthenticated")
        context = api["execution.context"].create_context(request["graph"],
            constructor=request.get("constructor"), layout_arguments=request.get("layoutArguments"))
        before = context.original_graph
        graph = api["algorithms.layered.import_export"].import_ports_graph(context, None)
        require(same_json(context.original_graph, before), "Private importer changed the original input")
        nodes = []
        for node in graph.layerless_nodes:
            ports = []
            for port in node.ports:
                properties = {key: port.properties[key] for key in (
                    "PORT_INDEX", "PORT_BORDER_OFFSET", "PORT_RATIO_OR_POSITION", "INSIDE_CONNECTIONS")
                    if key in port.properties}
                ports.append(dict(id=None if port.origin is None else port.origin.id, side=port.side,
                    position=[port.pos.x, port.pos.y], size=[port.size.x, port.size.y],
                    anchor=[port.anchor.x, port.anchor.y], explicitlySuppliedPortAnchor=port.explicitly_supplied_port_anchor,
                    properties=properties, incoming=[e.origin.id for e in port.incoming_edges],
                    outgoing=[e.origin.id for e in port.outgoing_edges]))
            nodes.append(dict(id=node.origin.id, position=[node.pos.x, node.pos.y], size=[node.size.x, node.size.y],
                              constraints=node.properties["PORT_CONSTRAINTS"], ports=ports))
        actual = dict(direction=graph.properties["DIRECTION"], flags=sorted(graph.properties["GRAPH_PROPERTIES"]), nodes=nodes)
        expected = observation["imports"][0]
        rows.append(dict(id=entry["id"], passed=same_json(actual, expected), actual=actual, expected=expected))
    return rows


def adapter_rows(api, suite):
    request_raw = (suite / "port-context-adapter-request.json").read_bytes()
    request, observation = json.loads(request_raw), load(suite / "port-context-adapter-oracle.json")
    command = load(suite / "port-context-adapter-oracle.command.json")
    command_check(command, observation, "port-context-adapter-probe.cjs")
    require(observation["requestSha256"] == digest(request_raw)
            and observation["probeSha256"] == digest((suite / "port-context-adapter-probe.cjs").read_bytes()),
            "Original adapter probe/request bytes differ")
    g, n = api["algorithms.layered.graph"], api["algorithms.layered.node_size"]
    node = g.LNode(g.LGraph(None, None, None), type=request["nodeType"],
                  properties={"PORT_LABELS_PLACEMENT": set(request["portLabelsPlacement"])})
    port = g.LPort(side=request["portSide"], outgoing_edges=[g.LEdge() for _ in range(request["rawOutgoingCount"])])
    g.set_port_owner(port, node)
    context = n.NodeContext(node, transparent_north_south_edges=request["transparentNorthSouthEdges"])
    n.create_port_contexts(context)
    actual = context.port_contexts[port.side][0].labels_next_to_port
    expected = observation["result"]["labelsNextToPort"]
    return [dict(id="transparent-ns-owner-early-empty", passed=same_json(actual, expected),
                 actual=actual, expected=expected)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Source directory containing private pyelk/")
    parser.add_argument("--suite", type=Path, default=SUITE)
    parser.add_argument("--role", choices=["all", *COUNTS], default="all")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    require(not args.out.exists(), "Use a new output path; previous evidence is retained")
    before = source_files(args.source)
    api = modules(args.source)
    operations = {"init": init_rows, "order": order_rows, "import": import_rows, "adapter": adapter_rows}
    reports = {}
    for role in operations if args.role == "all" else [args.role]:
        rows = operations[role](api, args.suite)
        require(len(rows) == COUNTS[role] and len({v["id"] for v in rows}) == COUNTS[role],
                "Original primitive case denominator differs: " + role)
        reports[role] = dict(passed=all(r["passed"] for r in rows), count=len(rows), rows=rows)
    require(source_files(args.source) == before, "Private source changed during primitive comparison")
    result = dict(passed=all(v["passed"] for v in reports.values()), roles=reports,
        privateSourceFilesSha256=before, comparatorSha256=digest(Path(__file__).read_bytes()),
        suiteFilesSha256={p.name: digest(p.read_bytes()) for p in sorted(args.suite.iterdir())
                         if p.is_file() and (p.name.startswith("ports-") or p.name.startswith("port-context-"))},
        referenceReexecuted=False, graphLayoutExecuted=False, installedPackageValidated=False,
        fullValidation=False, historicalExecutionAuthenticated=False,
        scope="Saved original Node observations versus current private helpers/importer; no candidate full layout")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], roles={k: v["count"] for k, v in reports.items()},
                          graphLayoutExecuted=False, referenceReexecuted=False)))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
