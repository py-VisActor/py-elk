"""F03/F04 changed-closure owner checks, not a full provider acceptance."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / '.local/migration-next/src'))
from pyelk.algorithms.force import (FNode, FEdge, FLabel, FGraph, FBendpoint,
    import_graph, apply_layout, split_components, recombine_components)
from pyelk.execution.json_transfer import JsonLayoutSession


def check_import():
    request = {'id': 'r', 'width': 77, 'height': 66,
        'layoutOptions': {'nodeSize.fixedGraphSize': True},
        'children': [{'id': 'a', 'x': 3, 'y': 4, 'width': 0, 'height': 0},
                     {'id': 'b', 'x': 30, 'y': 40, 'width': 20, 'height': 10}],
        'edges': [{'id': 'ab', 'sources': ['a'], 'targets': ['b'],
                   'labels': [{'id': 'label', 'text': 'edge', 'width': 0, 'height': 0}]}]}
    original = json.dumps(request, sort_keys=True)
    state = JsonLayoutSession(request)
    graph = import_graph(state, state.graph)
    a, b = graph.nodes
    assert (a.position.x, a.position.y, a.size.x, a.size.y) == (3, 4, 1, 1)
    assert (b.position.x, b.position.y) == (40, 45)
    assert (graph.labels[0].size.x, graph.labels[0].size.y) == (1, 1)
    edge = graph.edges[0]
    first = {'id': 'kept', 'business': {'untouched': True}}
    edge.origin['sections'] = [first, {'id': 'removed'}]
    apply_layout(graph)
    assert edge.origin['sections'] == [first]
    assert first['business'] == {'untouched': True}
    assert state.graph['width'] == 77 and state.graph['height'] == 66
    assert (a.origin['x'], a.origin['y']) == (50.5, 50.5)
    assert state.computed_options[id(state.graph)]['childAreaWidth'] == 47.5
    assert state.computed_options[id(state.graph)]['childAreaHeight'] == 46.5
    assert json.dumps(request, sort_keys=True) == original
    return {'clampedSize': [a.size.x, a.size.y], 'originalCenter': [a.position.x, a.position.y],
            'fixedGraphSize': [state.graph['width'], state.graph['height']]}


def check_components():
    graph = FGraph()
    nodes = [FNode(str(i)) for i in range(4)]
    for index, node in enumerate(nodes):
        node.id = index
        node.size.x = node.size.y = 10
        node.position.x = index*20
    graph.nodes.extend(nodes)
    edges = []
    for name, source, target in [('ab', 0, 1), ('bc', 1, 2), ('ca', 2, 0)]:
        edge = FEdge()
        edge.source, edge.target = nodes[source], nodes[target]
        edge.properties['name'] = name
        label = FLabel(edge, name)
        graph.labels.append(label)
        graph.edges.append(edge)
        edges.append(edge)
    rng = object()
    graph.properties['RANDOM'] = rng
    components = split_components(graph)
    assert len(components) == 2
    first, isolated = components
    names = [edge.properties['name'] for edge in first.edges]
    assert names == ['ca', 'bc', 'ab', 'ca'], names
    assert [label.text for label in first.labels] == names
    assert first.properties['RANDOM'] is isolated.properties['RANDOM'] is rng
    assert [node.id for node in first.nodes] == [0, 1, 2]
    assert isolated.nodes[0].id == 0
    graph.properties['separateConnectedComponents'] = False
    assert split_components(graph) == [graph]
    assert recombine_components([first]) is first
    empty = recombine_components([])
    assert empty is not graph and empty.nodes == [] and empty.origin is None
    bend = FBendpoint(edges[2])
    bend.position.x = 1
    first.bend_points.append(bend)
    merged = recombine_components(components)
    assert merged.properties['RANDOM'] is rng
    assert merged.bend_points == []  # Original move omits graph.bendPoints.
    assert len(merged.edges) == 4  # Same cycle edge appears twice, uncorrected.
    assert len(merged.labels) == 4
    return {'cycleEdgeOrder': names, 'componentSizes': [len(x.nodes) for x in components],
            'returnedEdgeCount': len(merged.edges), 'mergedGraphBendPointCount': len(merged.bend_points)}


if __name__ == '__main__':
    result = {'scope': 'F03/F04 owner checks only; independent original oracle pending',
              'import': check_import(), 'components': check_components(),
              'filesSha256': {'.local/migration-next/src/pyelk/algorithms/force.py':
                  hashlib.sha256((ROOT/'.local/migration-next/src/pyelk/algorithms/force.py').read_bytes()).hexdigest()}}
    print(json.dumps(result, indent=2))
