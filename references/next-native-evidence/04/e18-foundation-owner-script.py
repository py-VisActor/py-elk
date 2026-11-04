"""Changed-closure owner check, not an independent upstream oracle."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / '.local/migration-next/src'))
from pyelk.algorithms.force import FNode, FEdge, FBendpoint, FLabel, FGraph


def run():
    graph = FGraph()
    a, b = FNode('a'), FNode('b')
    a.id, b.id = 0, 1
    graph.nodes.extend([a, b])
    edge = FEdge()
    edge.source, edge.target = a, b
    edge.properties['priority'] = 3
    graph.edges.append(edge)
    reverse = FEdge()
    reverse.source, reverse.target = b, a
    reverse.properties['priority'] = 2
    graph.edges.append(reverse)
    graph.calc_adjacency()
    assert graph.adjacency == [[0, 3], [2, 0]]
    assert graph.get_connection(a, b) == 5
    first, second = FBendpoint(edge), FBendpoint(edge)
    other = FBendpoint(reverse)
    assert graph.get_connection(first, second) == 3
    assert graph.get_connection(first, other) == 0
    assert graph.bend_points == []  # Constructor does not append graph list.
    assert edge.bendpoints == [first, second]
    a.position.x, a.position.y = 0, 0
    b.position.x, b.position.y = 30, 60
    edge.distribute_bendpoints()
    assert [(x.position.x, x.position.y) for x in edge.bendpoints] == [(10, 20), (20, 40)]
    a.size.x = a.size.y = 10
    b.size.x = b.size.y = 20
    assert (edge.source_point().x, edge.source_point().y) == (2.5, 5)
    assert (edge.target_point().x, edge.target_point().y) == (25, 50)
    label = FLabel(edge, 'label')
    label.size.x, label.size.y = 8, 6
    assert graph.labels == [] and edge.labels == [label]
    quadrants = []
    for source, target, expected in [((30, 60), (0, 0), (20, 19)),
                                     ((30, 0), (0, 60), (20, 35)),
                                     ((0, 60), (30, 0), (20, 19)),
                                     ((0, 0), (30, 60), (20, 19))]:
        a.position.x, a.position.y = source
        b.position.x, b.position.y = target
        label.refresh_position()
        actual = (label.position.x, label.position.y)
        assert actual == expected, (source, target, actual, expected)
        quadrants.append(list(actual))
    label.properties['edgeLabels.inline'] = True
    label.refresh_position()
    assert (label.position.x, label.position.y) == (11, 27)
    assert list(graph.particles()) == [a, b]
    path = ROOT / '.local/migration-next/src/pyelk/algorithms/force.py'
    return {'passed': True, 'scope': 'F01/F02 owner checks; independent Node oracle pending',
            'sourceSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'quadrantPositions': quadrants}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
