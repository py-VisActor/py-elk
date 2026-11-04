"""Original-only premises for E07 geometry assertions; computes no layout.

This deliberately imports no candidate admission/options/algorithm module.
Only the nine reviewed option spellings and bounded flat input domain qualify.
"""
import math
import re

_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_DEFAULTS = {"algorithm": "layered", "direction": "UNDEFINED", "edgeRouting": "ORTHOGONAL",
             "randomSeed": 1, "padding": dict.fromkeys(("top", "right", "bottom", "left"), 12),
             "separateConnectedComponents": True, "spacing.nodeNode": 20,
             "spacing.componentComponent": 20, "layered.spacing.nodeNodeBetweenLayers": 20}


def _number(value):
    if type(value) is str:
        if not _DECIMAL.fullmatch(value):
            raise ValueError("Invalid decimal")
        value = float(value)
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("Invalid nonnegative number")
    return value


def _padding(value):
    if type(value) is not str or not value.startswith("[") or not value.endswith("]"):
        raise ValueError("Only four-side string padding")
    parsed = {}
    for part in value[1:-1].split(","):
        pair = part.split("=")
        if len(pair) != 2 or pair[0].strip() not in _DEFAULTS["padding"] or pair[0].strip() in parsed:
            raise ValueError("Invalid padding fields")
        parsed[pair[0].strip()] = _number(pair[1].strip())
    if set(parsed) != set(_DEFAULTS["padding"]):
        raise ValueError("Incomplete padding")
    return parsed


def _scope(container):
    if type(container) is not dict:
        raise ValueError("Invalid option mapping")
    parsed = {}
    for key, value in container.items():
        if type(key) is not str or not key.startswith(("elk.", "org.eclipse.elk.")):
            raise ValueError("Unknown alias")
        name = key[len("org.eclipse.elk."):] if key.startswith("org.eclipse.elk.") else key[len("elk."):]
        if name not in _DEFAULTS or name in parsed:
            raise ValueError("Unknown/duplicate option")
        if name == "algorithm":
            if value not in ("layered", "org.eclipse.elk.layered"):
                raise ValueError("Other algorithm")
        elif name == "direction":
            if value not in ("UNDEFINED", "RIGHT", "LEFT", "DOWN", "UP"):
                raise ValueError("Unknown direction")
        elif name == "edgeRouting":
            if value != "ORTHOGONAL":
                raise ValueError("Other router")
        elif name == "separateConnectedComponents":
            if type(value) is str and value.lower() in ("true", "false"):
                value = value.lower() == "true"
            if type(value) is not bool:
                raise ValueError("Invalid boolean")
        elif name == "randomSeed":
            if type(value) is str and _INTEGER.fullmatch(value):
                value = int(value)
            if type(value) is not int or not -(2**31) <= value < 2**31:
                raise ValueError("Invalid seed")
        elif name == "padding":
            value = _padding(value)
        else:
            value = _number(value)
        parsed[name] = value
    return parsed


def premises(request):
    """Return effective options, original components and proven rank pairs.

    A DAG reachable pair has distinct unit NS ranks. A strict simple ring has
    all distinct ranks after GREEDY plus NS. No other SCC is granted that fact.
    Failure returns None, never a partially relaxed premise.
    """
    try:
        if request.get("schema") != "py-elk-layout-request/v1":
            return None
        constructor, arguments, graph = (request[name] for name in ("constructor", "layoutArguments", "graph"))
        if type(constructor) is not dict or type(arguments) is not dict or type(graph) is not dict:
            return None
        if set(constructor) - {"defaultLayoutOptions", "algorithms"} or set(arguments) - {"layoutOptions", "logging", "measureExecutionTime"}:
            return None
        if "algorithms" in constructor and constructor["algorithms"] != ["layered"]:
            return None
        if any(type(arguments[k]) is not bool or arguments[k] for k in ("logging", "measureExecutionTime") if k in arguments):
            return None
        if "defaultLayoutOptions" in constructor and type(constructor["defaultLayoutOptions"]) is not dict:
            return None
        selected = arguments.get("layoutOptions", constructor.get("defaultLayoutOptions", {}))
        options = {**_DEFAULTS, **_scope(selected), **_scope(graph.get("layoutOptions", {}))}
        if options["randomSeed"] == 0 or any(v > 1_000_000 for v in options["padding"].values()):
            return None
        if any(options[k] > 1_000_000 for k in options if "spacing." in k):
            return None
        options["direction"] = "RIGHT" if options["direction"] == "UNDEFINED" else options["direction"]
        nodes, edges = graph.get("children", []), graph.get("edges", [])
        if type(nodes) is not list or type(edges) is not list or len(nodes) > 8 or len(edges) > 28:
            return None
        if any(k in graph for k in ("x", "y", "width", "height", "logging")):
            return None
        all_ids = [graph["id"], *[n["id"] for n in nodes], *[e["id"] for e in edges]]
        if any(type(i) is not str or not i for i in all_ids) or len(set(all_ids)) != len(all_ids):
            return None
        if any(k in item for item in [graph, *nodes, *edges] for k in ("properties", "$H")):
            return None
        if any(item.get(k) for item in [graph, *nodes, *edges] for k in ("ports", "labels")):
            return None
        if any(type(item[k]) is not list for item in [graph, *nodes, *edges]
               for k in ("ports", "labels") if k in item):
            return None
        for node in nodes:
            if any(type(node[k]) is not list for k in ("children", "edges") if k in node):
                return None
            if any(node.get(k) for k in ("children", "edges")) or any(k in node for k in ("x", "y")):
                return None
            if any(_number(node[k]) > 1_000_000 or type(node[k]) not in (int, float) for k in ("width", "height")):
                return None
            local = _scope(node.get("layoutOptions", {}))
            if set(local) - {"padding"} or ("padding" in local and any(v > 1_000_000 for v in local["padding"].values())):
                return None
        names = [node["id"] for node in nodes]
        outgoing, adjacent = {i: [] for i in names}, {i: set() for i in names}
        pairs = []
        for edge in edges:
            if "layoutOptions" in edge and type(edge["layoutOptions"]) is not dict:
                return None
            if any(k in edge for k in ("source", "target", "sourcePort", "targetPort")):
                return None
            if edge.get("layoutOptions") or any(k in edge for k in ("sections", "junctionPoints", "bendPoints", "startPoint", "endPoint", "sourcePoint", "targetPoint", "container")):
                return None
            if type(edge["sources"]) is not list or type(edge["targets"]) is not list or len(edge["sources"]) != 1 or len(edge["targets"]) != 1:
                return None
            s,t = edge["sources"][0],edge["targets"][0]
            if s not in outgoing or t not in outgoing:
                return None
            outgoing[s].append(t);adjacent[s].add(t);adjacent[t].add(s);pairs.append((s,t))
        membership, groups = {}, []
        for name in names:
            if name in membership:
                continue
            pending, group = [name], set()
            while pending:
                n = pending.pop()
                if n not in group:
                    group.add(n);pending.extend(adjacent[n]-group)
            for n in group:
                membership[n] = len(groups)
            groups.append(group)
        ranks = set()
        for group in groups:
            links = [(s,t) for s,t in pairs if s in group]
            indegree = {n:0 for n in group}
            for s,t in links:
                indegree[t] += 1
            remaining = dict(indegree)
            ready = [n for n in group if remaining[n] == 0]
            seen = 0
            while ready:
                n = ready.pop();seen += 1
                for t in outgoing[n]:
                    remaining[t] -= 1
                    if remaining[t] == 0:ready.append(t)
            if seen == len(group):
                for n in group:
                    reached,pending=set(),outgoing[n][:]
                    while pending:
                        t=pending.pop()
                        if t not in reached:
                            reached.add(t);pending.extend(outgoing[t])
                    ranks.update(frozenset((n,t)) for t in reached)
            elif len(group) >= 2 and len(links) == len(group) and all(indegree[n] == len(outgoing[n]) == 1 and outgoing[n][0] != n for n in group):
                ranks.update(frozenset((a,b)) for a in group for b in group if a != b)
        return {"options":options,"membership":membership,"distinctRanks":ranks}
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return None
