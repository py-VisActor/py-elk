"""Generate project-authored validation inputs, never expected coordinates.

Writes a NEW directory; review/edit inputs and regenerate official observations
explicitly. Existing fixtures and evidence are never overwritten.
"""
import argparse
import copy
from pathlib import Path

from layout_checks import write


def generate(out):
    out.mkdir(parents=True, exist_ok=False)
    cases = []
    padding = {"top": 12, "left": 12, "bottom": 12, "right": 12}

    def add(name, sizes, links, direction="RIGHT", *, forward=True, options=None,
            constructor=None, arguments=None, local=None, expected="returned", geometric=True, missing_graph=False):
        layout = {"elk.algorithm": "layered", "elk.direction": direction, "elk.randomSeed": "7",
                  "elk.padding": "[top=12,left=12,bottom=12,right=12]", "elk.spacing.nodeNode": "20",
                  "elk.layered.spacing.nodeNodeBetweenLayers": "30", "elk.separateConnectedComponents": "true",
                  "elk.spacing.componentComponent": "40", "elk.edgeRouting": "ORTHOGONAL"}
        if options:
            layout.update(options)
        if local is not None:
            layout = local
        nodes = [{"id": identity, "width": w, "height": h, "data": {"cost": 0.125, "enabled": True}} for identity, w, h in sizes]
        edges = [{"id": f"e{i}", "sources": [a], "targets": [b]} for i, (a, b) in enumerate(links)]
        graph = {"id": "root", "business": {"description": "preserve custom fields", "weight": 1e-9},
                 "layoutOptions": layout, "children": nodes, "edges": edges}
        request = {"schema": "py-elk-layout-request/v1", "constructor": constructor or {},
                   "layoutArguments": arguments or {}, "graph": None if missing_graph else graph}
        case = {"id": name, "request": f"requests/{name}.json", "origin": "project-authored",
                "expectedOutcome": expected, "geometry": {"profile": "basic-flat-orthogonal", "direction": direction,
                  "padding": copy.deepcopy(padding), "nodeNode": 20, "betweenLayers": 30, "forwardEdges": forward} if geometric else None}
        write(out / case["request"], request)
        cases.append(case)
        return request, case

    two = [("a", 40, 30), ("b", 40, 30)]
    three = [*two, ("c", 40, 30)]
    diamond = [*three, ("d", 40, 30)]
    diamond_edges = [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]
    add("layered-empty", [], [])
    add("layered-singleton", two[:1], [])
    add("layered-chain", three, [("a", "b"), ("b", "c")])
    add("layered-fork", three, [("a", "b"), ("a", "c")])
    add("layered-join", three, [("a", "c"), ("b", "c")])
    for direction in ("RIGHT", "LEFT", "DOWN", "UP"):
        add("layered-diamond-" + direction.lower(), diamond, diamond_edges, direction)
    add("layered-long-edge", diamond, [("a", "b"), ("b", "c"), ("c", "d"), ("a", "d")])
    add("layered-cycle", three, [("a", "b"), ("b", "c"), ("c", "a")], forward=False)
    add("layered-self-loop", two[:1], [("a", "a")], forward=False)
    add("layered-parallel-edges", two, [("a", "b"), ("a", "b")])
    _, case = add("layered-disconnected", diamond, [("a", "b"), ("c", "d")])
    case["geometry"]["componentRectangleGap"] = 40
    add("layered-unequal-sizes", [("a", 70, 15), ("b", 20, 80), ("c", 100, 35), ("d", 25, 55)], diamond_edges)
    add("layered-zero-size", [("a", 0, 0), ("b", 0, 0)], [("a", "b")])
    _, case = add("layered-custom-spacing", diamond, diamond_edges, options={"elk.spacing.nodeNode": 37,
                  "elk.layered.spacing.nodeNodeBetweenLayers": 53, "elk.padding": "[top=11,left=17,bottom=23,right=31]"})
    case["geometry"].update(nodeNode=37, betweenLayers=53, padding={"top": 11, "left": 17, "bottom": 23, "right": 31})
    add("layered-unseparated-components", diamond, [("a", "b"), ("c", "d")], options={"elk.separateConnectedComponents": False})
    local = {"elk.algorithm": "layered", "elk.randomSeed": 7, "elk.padding": "[top=12,left=12,bottom=12,right=12]",
             "elk.spacing.nodeNode": 20, "elk.layered.spacing.nodeNodeBetweenLayers": 30, "elk.edgeRouting": "ORTHOGONAL"}
    default = {"defaultLayoutOptions": {"elk.direction": "DOWN"}}
    add("options-constructor-default", two, [("a", "b")], "DOWN", local=local, constructor=default)
    add("options-explicit-empty-replaces-default", two, [("a", "b")], local=local, constructor=default, arguments={"layoutOptions": {}})
    add("options-call-replaces-default", two, [("a", "b")], "LEFT", local=local, constructor=default, arguments={"layoutOptions": {"elk.direction": "LEFT"}})
    full_options = {"org.eclipse.elk.algorithm": "org.eclipse.elk.layered", "org.eclipse.elk.randomSeed": 7,
                    "org.eclipse.elk.direction": "RIGHT", "org.eclipse.elk.padding": "[top=12,left=12,bottom=12,right=12]",
                    "org.eclipse.elk.spacing.nodeNode": 20, "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": 30,
                    "org.eclipse.elk.separateConnectedComponents": True, "org.eclipse.elk.spacing.componentComponent": 40,
                    "org.eclipse.elk.edgeRouting": "ORTHOGONAL"}
    add("options-full-ids", diamond, diamond_edges, local=full_options)
    add("error-unknown-endpoint", two, [("a", "missing")], expected="threw", geometric=False)
    add("error-unknown-algorithm", two, [("a", "b")], options={"elk.algorithm": "does-not-exist"}, expected="threw", geometric=False)
    add("error-missing-graph", [], [], arguments={"layoutOptions": {"elk.randomSeed": 7}}, expected="threw", geometric=False, missing_graph=True)
    write(out / "cases.json", {"schema": "py-elk-validation-cases/v1", "cases": cases})
    return len(cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    print(generate(parser.parse_args().out))
