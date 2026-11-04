"""Compare only the new prepared MrTree routing/compaction object cases.

Usage: python compare_mrtree_routing.py PRIVATE_SRC REQUEST ORACLE REPORT
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms import mrtree as m
    from pyelk.algorithms.layered.graph import Vec2
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    r = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['requestSha256'] == sha(request)
    rows = []
    for s, expected in zip(r['cases'], original['cases'], strict=True):
        assert s['id'] == expected['id']
        graph = m.TGraph(None, properties={'direction': s['direction'], 'mrtree.compaction': s['compaction'],
                                          'mrtree.edgeRoutingMode': s['mode'], 'spacing.nodeNode': s.get('spacing', 20)})
        nodes = []
        for i, spec in enumerate(s['nodes']):
            node = m.TNode(i, graph, 'n' + str(i), pos=Vec2(*spec['pos']), size=Vec2(*spec['size']))
            m.set_tree_level(node, spec['level'])
            if i == 0: node.properties['ROOT'] = True
            nodes.append(node)
            graph.nodes.append(node)
        for spec in s['edges']:
            edge = m.TEdge(nodes[spec[0]], nodes[spec[1]])
            graph.edges.append(edge)
            edge.source.outgoing_edges.append(edge)
            edge.target.incoming_edges.append(edge)
            edge.bend_points.extend(Vec2(*p) for p in (spec[2] if len(spec) > 2 else []))
        def snapshot():
            return dict(nodes=[dict(id=n.id, pos=[n.pos.x, n.pos.y], level=n.properties['mrtree.treeLevel'],
                                    constraints=[c.id for c in n.properties.setdefault('COMPACT_CONSTRAINTS', [])]) for n in graph.nodes],
                        edges=[dict(source=e.source.id, target=e.target.id, bends=[[v.x, v.y] for v in e.bend_points]) for e in graph.edges])
        value = dict(before=snapshot())
        m.compact_graph(graph)
        value['compacted'] = snapshot()
        m.calculate_level_coordinates(graph)
        m.route_edges(graph)
        value['routed'] = snapshot()
        rows.append(dict(id=s['id'], actual=value, expected=expected['value'], differences=diff(expected['value'], value)['differences']))
    boxed = []
    for level in r['boxed']:
        graph = m.TGraph(None)
        a, b = m.TNode(1, graph, 'a'), m.TNode(2, graph, 'b')
        graph.nodes.extend([a, b]); graph.edges.append(m.TEdge(a, b))
        m.set_tree_level(a, level); m.set_tree_level(b, level)
        boxed.append(dict(level=level, value=dict(sameBox=m._level_token(a) is m._level_token(b),
                                                outgoingCount=len(m.all_outgoing_edges(a, graph)), incomingCount=len(m.all_incoming_edges(b, graph)))))
    mean = m._mean(r['mean'])
    numeric = dict(boxed=boxed, mean=dict(mean=mean, secondAbove=r['mean'][1] > mean))
    numeric_diff = diff({k: original[k] for k in numeric}, numeric)['differences']
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if name == 'pyelk' or name.startswith('pyelk.') if getattr(module, '__file__', None)}
    hashes = {p.relative_to(source).as_posix(): before[p] for p in imported}
    unchanged = all(sha(p) == before[p] for p in imported)
    value = dict(passed=unchanged and not numeric_diff and all(not row['differences'] for row in rows),
                 rows=rows, numeric=numeric, numericDifferences=numeric_diff, sourceTreeUnchanged=unchanged,
                 importedSourcesSha256=hashes, inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
                 scope='Prepared object-level compaction, routing, boxed integer level identity and mean; no provider/micro-layout/public API claim')
    report.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(passed=value['passed'], cases=len(rows), numericChecks=len(boxed)+1, failed=[row['id'] for row in rows if row['differences']], numericDifferences=numeric_diff)))
    return 0 if value['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
