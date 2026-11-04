"""Compare native cell objects with a previously captured original Node oracle.

Usage: python compare_cells.py PRIVATE_SRC REQUEST_JSON ORACLE_JSON REPORT_JSON
No reference execution or expected generation occurs in this script.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main():
    source, request, oracle, report = map(Path, sys.argv[1:])
    original = json.loads(oracle.read_bytes())
    specifications = json.loads(request.read_bytes())
    assert original['requestSha256'] == hashlib.sha256(request.read_bytes()).hexdigest()
    sys.path.insert(0, str(source.resolve()))
    from pyelk.algorithms.layered import cell_layout as m
    from pyelk.algorithms.layered.graph import Insets, Vec2

    def build(s):
        kind = s['kind']
        if kind == 'atomic':
            c = m.AtomicCell()
        elif kind == 'grid':
            c = m.GridContainerCell(s.get('tabular', False), s.get('symmetrical', False), s.get('gap', 0))
        elif kind == 'strip':
            c = m.StripContainerCell(s.get('mode', 0), s.get('symmetrical', False), s.get('gap', 0))
        else:
            c = m.LabelCell(s.get('gap', 0), s.get('horizontalMode', True))
        p = s.get('padding', [0, 0, 0, 0])
        c.padding = Insets(top=p[0], right=p[1], bottom=p[2], left=p[3])
        c.contributes_to_minimum_width = c.contributes_to_minimum_height = s.get('contributes', True)
        if 'minimum' in s:
            c.minimum_content_area_size = Vec2(*s['minimum'])
        if 'rect' in s:
            c.cell_rectangle = m.Rectangle(*s['rect'])
        if kind == 'grid':
            c.only_center_cell_contributes_to_minimum_size = s.get('onlyCenter', False)
            if 'centerMinimum' in s:
                c.set_center_cell_minimum_size(Vec2(*s['centerMinimum']))
            for e in s.get('children', []):
                c.set_cell(e['row'], e['col'], build(e['cell']))
        elif kind == 'strip':
            for e in s.get('children', []):
                c.set_cell(e['area'], build(e['cell']))
        elif kind == 'label':
            if 'horizontalAlignment' in s:
                c.set_horizontal_alignment(s['horizontalAlignment'])
            if 'verticalAlignment' in s:
                c.set_vertical_alignment(s['verticalAlignment'])
            for size in s.get('labels', []):
                c.add_label(SimpleNamespace(pos=Vec2(), size=Vec2(*size)))
        return c

    def rect(r):
        return [r.x, r.y, r.width, r.height]

    def snapshot(c, s):
        o = dict(minimum=[c.get_minimum_width(), c.get_minimum_height()],
                 helperMinimum=[m.min_width_of_cell(c, False), m.min_height_of_cell(c, False)],
                 respectedMinimum=[m.min_width_of_cell(c, True), m.min_height_of_cell(c, True)],
                 rect=rect(c.cell_rectangle))
        if s['kind'] == 'grid':
            o['centerRect'] = rect(c.center_cell_rect)
            o['children'] = [snapshot(c.get_cell(e['row'], e['col']), e['cell']) for e in s.get('children', [])]
        elif s['kind'] == 'strip':
            o['children'] = [snapshot(c.get_cell(e['area']), e['cell']) for e in s.get('children', [])]
        elif s['kind'] == 'label':
            o['labels'] = [[l.pos.x, l.pos.y, l.size.x, l.size.y] for l in c.labels]
        return o

    rows = []
    for case, expected in zip(specifications['cases'], original['results'], strict=True):
        assert case['id'] == expected['id']
        c = build(case['cell'])
        if case['cell']['kind'] in ('grid', 'strip'):
            c.layout_children_horizontally()
            c.layout_children_vertically()
        elif case['cell']['kind'] == 'label':
            c.apply_label_layout()
        value = snapshot(c, case['cell'])
        rows.append(dict(id=case['id'], exact=value == expected['value'], actual=value, expected=expected['value']))
    result = dict(passed=all(row['exact'] for row in rows), count=len(rows), rows=rows,
                  filesSha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                               [Path(__file__), request, oracle, Path(m.__file__)]},
                  scope='Cell object geometry only; full layout and integration not assessed')
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(passed=result['passed'], count=len(rows), failed=[row['id'] for row in rows if not row['exact']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
