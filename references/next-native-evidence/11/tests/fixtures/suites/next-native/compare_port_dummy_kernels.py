"""Compare original inverted/merger helpers with supplied intermediate objects.

Usage: python compare_port_dummy_kernels.py PRIVATE_SRC REQUEST ORACLE REPORT [CASE_ID]
This runs no full layout or graph admission pipeline.
"""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    selected = sys.argv[5] if len(sys.argv) > 5 else None
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import LGraph, LNode, LPort, LEdge, Layer, Vec2, set_layer, set_port_owner, set_source, set_target
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.inverted_ports import inverted_port_processor
    from pyelk.algorithms.layered.hyperedge_merger import hyperedge_dummy_merger
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('port-dummy-kernels-probe.cjs'))
    rows = []
    for s, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert s['id'] == expected['id']
        if selected and selected != s['id']:
            continue
        graph = LGraph(None, None, None)
        layers = [Layer(graph) for _ in range(s['layerCount'])]
        graph.layers.extend(layers)
        nodes, ports, edges, labels, names, by_node, by_edge, initial_junctions = [], {}, [], [], {}, {}, {}, {}
        def name(obj): return None if obj is None else names[id(obj)]
        for spec in s['nodes']:
            node = LNode(graph, type=spec.get('type', 'NORMAL'), pos=Vec2(*spec.get('pos', [0, 0])),
                         size=Vec2(*spec.get('size', [20, 12])), properties={'PORT_CONSTRAINTS': 'FIXED_SIDE'})
            names[id(node)] = spec['id']; nodes.append(node); by_node[spec['id']] = node
            set_layer(node, layers[spec['layer']])
            for dto, key in [('hasLabels', 'LONG_EDGE_HAS_LABEL_DUMMIES'), ('beforeLabel', 'LONG_EDGE_BEFORE_LABEL_DUMMY')]:
                if dto in spec: node.properties[key] = spec[dto]
            for item in spec['ports']:
                port = LPort(id=item.get('scratchId', 0)); set_port_owner(port, node); set_side(port, item['side'])
                names[id(port)] = item['id']; ports[item['id']] = port
        for spec in s['nodes']:
            node = by_node[spec['id']]
            for dto, key in [('sourceMarker', 'LONG_EDGE_SOURCE'), ('targetMarker', 'LONG_EDGE_TARGET')]:
                if dto in spec: node.properties[key] = ports[spec[dto]]
        for item in s['edges']:
            edge = LEdge(properties={'ORIGIN': {'rawId': item['id']}}); edge.labels = []
            names[id(edge)] = item['id']; edges.append(edge); by_edge[item['id']] = edge
            set_source(edge, ports[item['source']]); set_target(edge, ports[item['target']])
            if item.get('emptyJunction'):
                edge.properties['JUNCTION_POINTS'] = []; initial_junctions[id(edge)] = edge.properties['JUNCTION_POINTS']
        for item in s['edges']:
            for spec in item.get('labels', []):
                label = SimpleNamespace(properties={'EDGE_LABELS_PLACEMENT': spec['placement']})
                if 'marker' in spec: label.properties['END_LABEL_EDGE'] = by_edge[spec['marker']]
                names[id(label)] = spec['id']; labels.append(label); by_edge[item['id']].labels.append(label)
        if s['operation'] == 'inverted': inverted_port_processor(graph)
        else: hyperedge_dummy_merger(graph)
        index = 0
        for layer in layers:
            for node in layer.nodes:
                if id(node) not in names:
                    key = 'd'+str(index); index += 1; names[id(node)] = key; nodes.append(node)
                    for i, port in enumerate(node.ports): names[id(port)] = key+'.p'+str(i)
        index = 0
        for node in nodes:
            for port in node.ports:
                for edge in [*port.incoming_edges, *port.outgoing_edges]:
                    if id(edge) not in names:
                        names[id(edge)] = 'x'+str(index); index += 1; edges.append(edge)
        value = dict(layers=[[name(node) for node in layer.nodes] for layer in layers],
                     nodes=[dict(id=name(node), type=node.type, pos=[node.pos.x, node.pos.y], size=[node.size.x, node.size.y],
                                 layerPointer=layers.index(node.layer) if node.layer is not None else None,
                                 physicallyInLayer=node.layer is not None and any(node is item for item in node.layer.nodes),
                                 origin=name(node.properties.get('ORIGIN')), sourceMarker=name(node.properties.get('LONG_EDGE_SOURCE')),
                                 targetMarker=name(node.properties.get('LONG_EDGE_TARGET')),
                                 sourceMarkerPresent='LONG_EDGE_SOURCE' in node.properties, targetMarkerPresent='LONG_EDGE_TARGET' in node.properties,
                                 ports=[dict(id=name(port), scratchId=port.id, side=port.side, size=[port.size.x, port.size.y],
                                             incoming=[name(edge) for edge in port.incoming_edges], outgoing=[name(edge) for edge in port.outgoing_edges])
                                        for port in node.ports]) for node in nodes],
                     edges=[dict(id=name(edge), source=name(edge.source), target=name(edge.target), originRawId=edge.properties.get('ORIGIN', {}).get('rawId'),
                                 junctionPresent='JUNCTION_POINTS' in edge.properties,
                                 originalJunctionIdentity=(initial_junctions[id(edge)] is edge.properties.get('JUNCTION_POINTS')) if id(edge) in initial_junctions else None,
                                 labels=[name(label) for label in getattr(edge, 'labels', [])]) for edge in edges],
                     labels=[dict(id=name(label), endLabelEdge=name(label.properties.get('END_LABEL_EDGE'))) for label in labels], fullLayoutValidated=False)
        rows.append(dict(id=s['id'], actual=value, expected=expected['value'], differences=diff(expected['value'], value)['differences']))
    assert rows and (not selected or len(rows) == 1)
    imported = {Path(module.__file__).resolve() for key, module in tuple(sys.modules.items())
                if (key == 'pyelk' or key.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows,
                  importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported}, sourceTreeUnchanged=unchanged,
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
                  scope='Actual two source processors on supplied intermediate objects; no layout, scheduler, crossing or public admission', fullLayoutValidated=False)
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows), failed=[row['id'] for row in rows if row['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
