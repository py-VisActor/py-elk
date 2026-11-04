"""Compare real NS helpers using supplied intermediate dummy coordinates.

Usage: python compare_ns_helpers.py PRIVATE_SRC REQUEST ORACLE REPORT [CASE_ID]
This is local pre/post processing, not a layout or crossing calculation.
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    selected = sys.argv[5] if len(sys.argv) > 5 else None
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import LGraph, LNode, LPort, LEdge, Layer, Vec2, set_layer, set_port_owner, set_source, set_target
    from pyelk.algorithms.layered.north_south_ports import north_south_port_preprocessor, north_south_port_postprocessor
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['requestSha256'] == sha(request)
    rows = []
    for s, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert s['id'] == expected['id']
        if selected and selected != s['id']: continue
        graph = LGraph(None, None, None, properties={'CONSIDER_MODEL_ORDER_STRATEGY': s['strategy'], 'EDGE_ROUTING': s['routing']})
        layer = Layer(graph); graph.layers.append(layer)
        nodes, ports, edges, names, by_port, initial_junctions = [], [], [], {}, {}, {}
        def name(obj): return None if obj is None else names[id(obj)]
        for spec in s['nodes']:
            node = LNode(graph, pos=Vec2(*spec.get('pos', [0, 0])), size=Vec2(*spec.get('size', [40, 30])), properties={'PORT_CONSTRAINTS': 'FIXED_SIDE'})
            names[id(node)] = spec['id']; nodes.append(node); set_layer(node, layer)
            for item in spec['ports']:
                p = LPort(id=len(ports), side=item['side'], pos=Vec2(*item.get('pos', [2, 3])), anchor=Vec2(*item.get('anchor', [1, 2])))
                set_port_owner(p, node)
                if 'allowSwitch' in item: p.properties['ALLOW_NON_FLOW_PORTS_TO_SWITCH_SIDES'] = item['allowSwitch']
                names[id(p)] = item['id']; by_port[item['id']] = p; ports.append(p)
        for item in s['edges']:
            e = LEdge(); names[id(e)] = item['id']; edges.append(e)
            set_source(e, by_port[item['source']]); set_target(e, by_port[item['target']])
            e.bend_points = [Vec2(*p) for p in item.get('bends', [])]
            if item.get('emptyJunction'):
                e.properties['JUNCTION_POINTS'] = []; initial_junctions[id(e)] = e.properties['JUNCTION_POINTS']
        def snapshot():
            return dict(layer=[name(n) for n in layer.nodes],
                        nodes=[dict(id=name(n), type=n.type, origin=name(n.properties.get('ORIGIN')), hint=n.properties.get('CROSSING_HINT'),
                                    layoutUnit=name(n.properties.get('IN_LAYER_LAYOUT_UNIT')),
                                    successors=[name(x) for x in n.properties.get('IN_LAYER_SUCCESSOR_CONSTRAINTS', [])],
                                    associates=[name(x) for x in n.properties.get('BARYCENTER_ASSOCIATES', [])],
                                    inLayer=n.layer is not None, graphRetained=n.graph is graph,
                                    ports=[dict(id=name(p), side=p.side, origin=name(p.properties.get('ORIGIN')), dummy=name(p.properties.get('PORT_DUMMY')),
                                                incoming=[name(e) for e in p.incoming_edges], outgoing=[name(e) for e in p.outgoing_edges],
                                                splineY=p.properties.get('SPLINE_NS_PORT_Y_COORD')) for p in n.ports]) for n in nodes],
                        edges=[dict(id=name(e), source=name(e.source), target=name(e.target), bends=[[p.x, p.y] for p in e.bend_points],
                                    junctionPresent='JUNCTION_POINTS' in e.properties, junctions=[[p.x, p.y] for p in e.properties.get('JUNCTION_POINTS', [])],
                                    initialJunctionIdentityPreserved=(initial_junctions[id(e)] is e.properties.get('JUNCTION_POINTS')) if id(e) in initial_junctions else None) for e in edges])
        north_south_port_preprocessor(graph)
        index = 0
        for n in layer.nodes:
            if id(n) not in names:
                key = 'd'+str(index); index += 1; names[id(n)] = key; nodes.append(n)
                for i, p in enumerate(n.ports): names[id(p)] = key+'.p'+str(i)
        value = dict(pre=snapshot())
        index = 0
        for n in nodes:
            if n.type == 'NORTH_SOUTH_PORT':
                n.pos = Vec2(*(s['dummyPlacement']['start'][i]+index*s['dummyPlacement']['step'][i] for i in range(2)))
                index += 1
        north_south_port_postprocessor(graph)
        value.update(post=snapshot(), dummyCoordinatesSupplied=True)
        rows.append(dict(id=s['id'], actual=value, expected=expected['value'], differences=diff(expected['value'], value)['differences']))
    assert rows and (not selected or len(rows) == 1)
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if name == 'pyelk' or name.startswith('pyelk.') if getattr(module, '__file__', None)}
    unchanged = all(sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and all(not r['differences'] for r in rows), rows=rows,
                  importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported}, sourceTreeUnchanged=unchanged,
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
                  scope='Actual NS pre/post local objects with explicit supplied dummy coordinates, no layout/crossing/public pipeline claim',
                  fullLayoutValidated=False, dummyCoordinatesSupplied=True)
    with report.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(passed=result['passed'], cases=len(rows), failed=[r['id'] for r in rows if r['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
