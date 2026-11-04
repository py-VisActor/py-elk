"""Replay original object-level MrTree stages, not complete provider layout.

Usage: python compare_mrtree_stages.py PRIVATE_SRC REQUEST ORACLE REPORT
"""
from pathlib import Path
import hashlib
import json
import math
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:])
    original = json.loads(oracle.read_bytes())
    assert hashlib.sha256(request.read_bytes()).hexdigest() == original['requestSha256']
    def hashes():
        return {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((source / 'pyelk').rglob('*')) if p.is_file()
                and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    before = hashes()
    sys.path.insert(0, str(source.resolve()))
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from pyelk.algorithms import mrtree as m
    from layout_checks import diff
    rows = []
    for s, expected in zip(json.loads(request.read_bytes())['cases'], original['cases'], strict=True):
        g = m.TGraph(None, properties={'mrtree.searchOrder': s.get('order', 'DFS'), 'direction': s.get('direction', 'DOWN'),
                                     'spacing.nodeNode': s.get('spacing', 20), 'mrtree.weighting': s.get('weighting', 'MODEL_ORDER')})
        names, edges = {}, {}
        for i, spec in enumerate(s['nodes']):
            n = m.TNode(99+i, g, 'n'+str(i))
            n.pos.x, n.pos.y = spec.get('pos', [0, 0])
            n.size.x, n.size.y = spec.get('size', [20, 10])
            if 'constraint' in spec:
                n.properties['mrtree.positionConstraint'] = spec['constraint']
            g.nodes.append(n)
            names[n] = 'n'+str(i)
        for i, (a, b) in enumerate(s['edges']):
            e = m.TEdge(g.nodes[a], g.nodes[b])
            g.edges.append(e)
            e.source.outgoing_edges.append(e)
            e.target.incoming_edges.append(e)
            edges[e] = 'e'+str(i)

        def snapshot():
            for n in g.nodes:
                names.setdefault(n, n.label)
            for i, e in enumerate(g.edges):
                edges.setdefault(e, 'dummy'+str(i))
            defaults = {'ROOT': False, 'DUMMY': False, 'FAN': 0, 'DESCENDANTS': 0, 'ID': '', 'POSITION': 0,
                        'XCOOR': 0, 'YCOOR': 0, 'LEVELHEIGHT': 0, 'PRELIM': 0, 'MODIFIER': 0, 'TREE_LEVEL': 0}
            return dict(nodes=[dict(key=names[n], id=n.id, label=n.label, pos=[n.pos.x, n.pos.y], size=[n.size.x, n.size.y],
                                    incoming=[edges[e] for e in n.incoming_edges], outgoing=[edges[e] for e in n.outgoing_edges],
                                    properties={k: n.properties.get('mrtree.treeLevel' if k == 'TREE_LEVEL' else k, v) for k, v in defaults.items()})
                               for n in g.nodes], edges=[dict(key=edges[e], source=names[e.source], target=names[e.target]) for e in g.edges],
                        eliminated=[edges[e] for e in g.properties.get('REMOVABLE_EDGES', [])])

        value = {'before': snapshot()}
        m.treeify(g)
        value['treeified'] = snapshot()
        m.find_roots(g)
        value['rooted'] = snapshot()
        if s.get('walk'):
            for fn in [m.calculate_fan, m.calculate_levels, m.order_nodes, m.calculate_level_heights, m.set_neighbors, m.place_nodes]:
                fn(g)
            value['placed'] = snapshot()
            m.transform_directions(g)
            m.set_node_positions(g)
            value['positioned'] = snapshot()
        m.untreeify(g)
        value['restored'] = snapshot()
        reference = expected['value']
        # Only explicit numeric property slots are deboxed. Original raw JSON
        # retains GWT Integer objects; no business field or geometry is removed.
        import copy
        reference = copy.deepcopy(reference)
        for stage in reference.values():
            for n in stage['nodes']:
                for key, prop in n['properties'].items():
                    if type(prop) is dict and set(prop) == {'value_0'}:
                        n['properties'][key] = prop['value_0']
        result = diff(reference, value)
        rows.append(dict(id=s['id'], comparison=result, actual=value, expected=reference))
    numeric = []
    special = {'NaN': math.nan, 'Infinity': math.inf, '-Infinity': -math.inf}
    for row in original['rounding']:
        value = special[row['input']] if isinstance(row['input'], str) else row['input']
        actual = m._round_to_int32(value)
        numeric.append(dict(input=row['input'], actual=actual, expected=row['result'], exact=type(actual) is int and actual == row['result']))
    assert hashes() == before, 'Private source changed during execution'
    result = dict(passed=all(row['comparison']['passed'] for row in rows) and all(n['exact'] for n in numeric),
                  cases=rows, rounding=numeric, sourceTreeSha256=before,
                  referenceSha256=hashlib.sha256(oracle.read_bytes()).hexdigest(),
                  comparatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  scope='Object phases and numeric adapter only; full routing, micro-layout and provider acceptance not assessed')
    report.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(passed=result['passed'], stageCases=len(rows), roundingCases=len(numeric),
                         failed=[row['id'] for row in rows if not row['comparison']['passed']],
                         failedRounding=[n['input'] for n in numeric if not n['exact']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
