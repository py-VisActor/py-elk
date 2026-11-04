"""Independent, finite-scope algorithm geometry checks over saved JSON only.

No pyelk implementation is imported. This is a set of geometric quality
predicates, not a coordinate oracle or a claim about all algorithm options.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    'mrtree-tree-base', 'mrtree-compaction', 'mrtree-cycle-dfs',
    'radial-base', 'radial-radius', 'radial-compactor',
    'box-simple-base', 'box-group_dec', 'rectpacking-base', 'rectpacking-simple',
    'spore-overlap-base', 'spore-overlap-scanline', 'disco-base', 'disco-component-space',
)
TOLERANCE = 1e-6


def key(value):
    return type(value).__name__, value


def option(graph, name, default=None):
    values = graph.get('layoutOptions', {})
    return next((values[prefix + name] for prefix in ('org.eclipse.elk.', 'elk.', '')
                 if prefix + name in values), default)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def flat_nodes(graph):
    nodes = graph.get('children', [])
    return (len(nodes) >= 2 and all(not n.get('children') and not n.get('ports')
                                  and not n.get('labels') for n in nodes))


def topology(graph):
    nodes = graph.get('children', [])
    identifiers = [key(n['id']) for n in nodes]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError('Duplicate node identity')
    adjacency = {identifier: [] for identifier in identifiers}
    incoming = {identifier: 0 for identifier in identifiers}
    undirected = {identifier: set() for identifier in identifiers}
    for edge in graph.get('edges', []):
        if len(edge.get('sources', [])) != 1 or len(edge.get('targets', [])) != 1:
            raise ValueError('Only simple direct-node edges are assessed')
        source, target = key(edge['sources'][0]), key(edge['targets'][0])
        if source not in adjacency or target not in adjacency:
            raise ValueError('Port or external endpoint')
        adjacency[source].append(target)
        incoming[target] += 1
        undirected[source].add(target)
        undirected[target].add(source)
    components = []
    remaining = set(identifiers)
    for identifier in identifiers:
        if identifier not in remaining:
            continue
        component, work = set(), [identifier]
        while work:
            current = work.pop()
            if current in component:
                continue
            component.add(current)
            remaining.discard(current)
            work.extend(undirected[current] - component)
        components.append(component)
    roots = [identifier for identifier in identifiers if incoming[identifier] == 0]
    depth = {}
    if len(roots) == 1 and all(count <= 1 for count in incoming.values()):
        work = [(roots[0], 0)]
        while work:
            identifier, level = work.pop()
            if identifier in depth:
                depth = {}
                break
            depth[identifier] = level
            work.extend((child, level + 1) for child in adjacency[identifier])
    if len(depth) != len(nodes):
        depth = {}
    return adjacency, depth, roots, components


def rectangle(node):
    return node['x'], node['y'], node['x'] + node['width'], node['y'] + node['height']


def intersects(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > TOLERANCE and min(a[3], b[3]) - max(a[1], b[1]) > TOLERANCE


def assess(request, observation):
    graph = request['graph']
    algorithm = str(option(graph, 'algorithm', '')).split('.')[-1]
    report = {'algorithm': algorithm, 'status': 'NOT_ASSESSED', 'checks': [],
              'notAssessed': [], 'failures': [], 'metrics': {}, 'tolerance': TOLERANCE}

    def skip(reason):
        report['notAssessed'].append(reason)
        return report

    def check(name, failures):
        report['checks'].append({'predicate': name, 'passed': not failures, 'failures': failures})
        report['failures'].extend({'predicate': name, **row} for row in failures)

    if observation.get('outcome') != 'returned':
        return skip('The observation did not return geometry; errors are not geometric passes')
    if not flat_nodes(graph) or graph.get('labels') or request.get('constructor'):
        return skip('Requires flat direct leaf nodes without labels/ports or constructor defaults')
    result = observation['result']
    original = {key(node['id']): node for node in graph['children']}
    actual = {key(node['id']): node for node in result.get('children', [])}
    bad = []
    if set(original) != set(actual):
        bad.append({'reason': 'Node identity set differs'})
    for identifier, node in actual.items():
        if any(not number(node.get(name)) for name in ('x', 'y', 'width', 'height')):
            bad.append({'node': identifier, 'reason': 'Nonfinite or absent rectangle'})
        elif node['width'] < 0 or node['height'] < 0:
            bad.append({'node': identifier, 'reason': 'Negative extent'})
    if bad:
        check('finite-node-rectangles', bad)
        report['status'] = 'FAIL'
        return report
    try:
        adjacency, depth, roots, components = topology(graph)
    except ValueError as error:
        return skip(str(error))

    if algorithm == 'mrtree':
        if not depth or option(graph, 'mrtree.compaction', False) is not False:
            return skip('Tree layer bands require a unique rooted simple tree and compaction=false')
        direction = option(graph, 'direction', 'DOWN')
        if direction not in ('DOWN', 'UP', 'LEFT', 'RIGHT'):
            return skip('An explicit cardinal direction is required')
        horizontal = direction in ('LEFT', 'RIGHT')
        sign = -1 if direction in ('LEFT', 'UP') else 1
        bands = {}
        for identifier, level in depth.items():
            n = actual[identifier]
            start = n['x'] if horizontal else n['y']
            end = start + (n['width'] if horizontal else n['height'])
            lo, hi = (start, end) if sign > 0 else (-end, -start)
            bands.setdefault(level, []).append((lo, hi))
        bad = []
        gap = option(graph, 'spacing.nodeNode', 20)
        if not number(gap) or gap < 0:
            return skip('Nonnegative numeric spacing is required')
        for level in range(1, len(bands)):
            previous_end = max(hi for _, hi in bands[level - 1])
            next_start = min(lo for lo, _ in bands[level])
            if next_start + TOLERANCE < previous_end + gap:
                bad.append({'depth': level, 'previousEnd': previous_end, 'nextStart': next_start, 'spacing': gap})
        check('directional-parent-child-depth-bands', bad)
        report['metrics']['treeDepth'] = max(depth.values())
    elif algorithm == 'radial':
        radius = option(graph, 'radial.radius')
        if (not depth or option(graph, 'radial.compactor', 'NONE') != 'NONE'
                or option(graph, 'radial.rotate', False) is not False
                or not number(radius) or radius <= 0):
            return skip('Requires a unique rooted tree, explicit positive radius, NONE compactor, no rotation')
        root = actual[roots[0]]
        center = (root['x'] + root['width']/2, root['y'] + root['height']/2)
        rings = {}
        for identifier, level in depth.items():
            n = actual[identifier]
            distance = math.hypot(n['x'] + n['width']/2 - center[0], n['y'] + n['height']/2 - center[1])
            rings.setdefault(level, []).append(distance)
        bad = []
        for level, distances in rings.items():
            if max(distances) - min(distances) > TOLERANCE:
                bad.append({'depth': level, 'reason': 'Unequal center radii', 'radii': distances})
            if level and min(distances) + TOLERANCE < max(rings[level - 1]) + radius:
                bad.append({'depth': level, 'reason': 'Radial increment smaller than requested radius'})
        check('concentric-depth-rings-with-minimum-radius-increment', bad)
        report['metrics']['radiiByDepth'] = rings
        report['notAssessed'].append('No radial rectangle-nonoverlap or exact depth*radius claim; radius extension is allowed')
    elif algorithm in ('box', 'rectpacking', 'sporeOverlap', 'disco'):
        if option(graph, 'fixedGraphSize', False) is not False:
            return skip('A fixed container can legitimately fail containment')
        if algorithm == 'sporeOverlap' and option(graph, 'overlapRemoval.runScanline', True) is not True:
            return skip('This overlap-removal guarantee is scoped to scanline enabled')
        cross_components = algorithm == 'disco'
        membership = {identifier: index for index, component in enumerate(components) for identifier in component}
        pairs, overlaps = 0, []
        items = list(actual.items())
        for index, (identifier, node) in enumerate(items):
            for other_id, other in items[index + 1:]:
                if cross_components and membership[identifier] == membership[other_id]:
                    continue
                pairs += 1
                if intersects(rectangle(node), rectangle(other)):
                    overlaps.append({'nodes': [identifier, other_id]})
        if not pairs:
            return skip('No distinct component pair' if cross_components else 'No rectangle pair')
        check('different-component-node-rectangle-separation' if cross_components else 'node-rectangle-nonoverlap', overlaps)
        if cross_components:
            boxes = []
            for component in components:
                rectangles = [rectangle(actual[identifier]) for identifier in component]
                boxes.append((min(r[0] for r in rectangles), min(r[1] for r in rectangles),
                              max(r[2] for r in rectangles), max(r[3] for r in rectangles)))
            report['metrics']['componentBounds'] = boxes
            report['metrics']['interlockingComponentBoxPairs'] = sum(intersects(a, b) for i, a in enumerate(boxes) for b in boxes[i+1:])
            report['notAssessed'].append('Component-box nonoverlap is NOT_APPLICABLE to POLYOMINO interlocking; same-component nodes may overlap')
        if algorithm in ('box', 'rectpacking', 'sporeOverlap'):
            bad = []
            if any(not number(result.get(name)) or result[name] < 0 for name in ('width', 'height')):
                bad.append({'reason': 'Invalid container extent'})
            else:
                for identifier, node in actual.items():
                    x0, y0, x1, y1 = rectangle(node)
                    if x0 < -TOLERANCE or y0 < -TOLERANCE or x1 > result['width'] + TOLERANCE or y1 > result['height'] + TOLERANCE:
                        bad.append({'node': identifier, 'reason': 'Rectangle outside container'})
            check('node-rectangles-contained-in-container', bad)
        report['metrics']['assessedRectanglePairs'] = pairs
    else:
        return skip('No predicate declared for this provider')
    report['status'] = 'FAIL' if report['failures'] else 'PASS'
    return report


def audit_archive(archive):
    rows = []
    with zipfile.ZipFile(archive) as source:
        for identifier in CASES:
            request_name = 'tests/fixtures/suites/full-option-effects-nonlayered/requests/' + identifier + '.json'
            request_raw = source.read(request_name)
            request = json.loads(request_raw)
            bindings = {'request': {'path': request_name, 'sha256': hashlib.sha256(request_raw).hexdigest()}}
            row = {'id': identifier, 'bindings': bindings}
            for role, folder in (('source', 'reference'), ('native', 'native')):
                name = 'test-runs/full-native-closure/B/nonlayered-effects-' + folder + '-01/' + identifier + '.json'
                raw = source.read(name)
                observation = json.loads(raw)
                if observation['requestSha256'] != bindings['request']['sha256']:
                    raise ValueError('Saved request SHA differs: ' + identifier)
                bindings[role] = {'path': name, 'sha256': hashlib.sha256(raw).hexdigest()}
                row[role] = assess(request, observation)
            rows.append(row)
    counts = {role: {state: sum(row[role]['status'] == state for row in rows)
                     for state in ('PASS', 'FAIL', 'NOT_ASSESSED')} for role in ('source', 'native')}
    return {'schema': 'pyelk-independent-algorithm-geometry/v1', 'rows': rows, 'counts': counts,
            'passed': all(row[role]['status'] != 'FAIL' for row in rows for role in ('source', 'native')),
            'archiveSha256': hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
            'sourceExecutions': 0, 'nativeExecutions': 0, 'wholeOptionGeometryComplete': False,
            'scope': 'Flat unlabelled direct leaf rectangles and stated simple-tree/option preconditions only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=ROOT/'references/full-native-closure/options.zip')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit_archive(args.archive)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'passed': result['passed'], 'counts': result['counts'], 'layoutExecutions': 0}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
