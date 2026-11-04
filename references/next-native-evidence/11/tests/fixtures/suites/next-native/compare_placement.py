"""Compare staged native ports to an original-worker primitive oracle.

Usage: python compare_placement.py PRIVATE_SRC REQUEST ORACLE REPORT
"""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main():
    source, request, oracle, report = map(Path, sys.argv[1:])
    expected = json.loads(oracle.read_bytes())
    assert expected['requestSha256'] == hashlib.sha256(request.read_bytes()).hexdigest()
    sys.path.insert(0, str(source.resolve()))
    from pyelk.algorithms.layered.graph import LGraph, LNode, LPort, Vec2, Insets
    from pyelk.algorithms.layered import node_size as m
    rows = []
    for case, original in zip(json.loads(request.read_bytes())['cases'], expected['results'], strict=True):
        props = {'PORT_ALIGNMENT_' + k: v for k, v in case.get('alignments', {}).items()}
        if 'alignment' in case:
            props['PORT_ALIGNMENT_DEFAULT'] = case['alignment']
        node = LNode(LGraph(None, None, None), properties=props)
        groups = {s: [] for s in ('NORTH', 'EAST', 'SOUTH', 'WEST')}
        ports = []
        for item in case['ports']:
            p = LPort(id=item['id'], side=item['side'], pos=Vec2(*item.get('pos', [0, 0])), size=Vec2(*item.get('size', [4, 4])))
            if 'ratio' in item:
                p.properties['PORT_RATIO_OR_POSITION'] = item['ratio']
            if 'offset' in item:
                p.properties['PORT_BORDER_OFFSET'] = item['offset']
            groups[p.side].append(m.PlacementPortContext(p, port_margin=Insets(*item.get('margin', [0, 0, 0, 0]))))
            ports.append(p)
        # Original NodeContext's ordered multimap reverses SOUTH/WEST volatile
        # IDs. Placement consumes these prepared lists; it does not sort them.
        for side in ('SOUTH', 'WEST'):
            groups[side].reverse()
        cells = {}
        for side, spec in case.get('cells', {}).items():
            cells[side] = SimpleNamespace(cell_rectangle=SimpleNamespace(**dict(zip(('x', 'y', 'width', 'height'), spec['rect']))),
                                          padding=Insets(*spec.get('padding', [0, 0, 0, 0])), minimum_content_area_size=Vec2(*spec['minimum']))
        context = m.PortPlacementContext(node, Vec2(*case.get('nodeSize', [100, 60])), case['constraints'], groups, cells, case.get('spacing', 10), set(case.get('options', [])))
        before = [[p.pos.x, p.pos.y] for p in ports]
        m.place_horizontal_ports(context)
        m.offset_southern_ports_by_node_size(context)
        m.place_vertical_ports(context)
        staged = [[p.pos.x, p.pos.y] for p in ports]
        m.apply_port_positions(context)
        value = dict(effectiveAlignments={s: m.get_port_alignment(context, s) for s in groups}, before=before, staged=staged,
                     ports=[dict(id=p.id, pos=[p.pos.x, p.pos.y]) for p in ports])
        assert case['id'] == original['id']
        rows.append(dict(id=case['id'], exact=value == original['value'], actual=value, expected=original['value']))
    result = dict(passed=all(row['exact'] for row in rows), count=len(rows), rows=rows,
                  filesSha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), request, oracle, Path(m.__file__)]},
                  scope='Primitive staged placement with supplied cells, not full layout or calculated node sizing')
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(passed=result['passed'], count=len(rows), failed=[row['id'] for row in rows if not row['exact']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
