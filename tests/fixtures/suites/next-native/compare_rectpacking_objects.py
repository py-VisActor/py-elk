"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: drawing and mutable row helpers only."""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.rectpacking import (DrawingData, WHOLE_DRAWING,
        compute_scale_measure, calculate_dimensions, reset_coordinates,
        BlockRow, RectRow, Block)
    from pyelk.execution.json_transfer import JsonLayoutSession
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('rectpacking-objects-probe.cjs'))

    def number(value):
        if math.isnan(value): return 'NaN'
        if math.isinf(value): return 'Infinity' if value > 0 else '-Infinity'
        if value == 0 and math.copysign(1, value) < 0: return '-0'
        return value

    d = s['drawing']
    drawing = DrawingData(d['aspectRatio'], d['width'], d['height'], WHOLE_DRAWING, *d['next'])
    def draw():
        return dict(width=drawing.drawing_width, height=drawing.drawing_height,
            scale=number(drawing.scale_measure), next=[drawing.next_x_coordinate, drawing.next_y_coordinate],
            descriptorSame=drawing.placement_option is WHOLE_DRAWING)
    drawings = [draw()]
    for key, value in d['actions']:
        (drawing.set_drawing_width if key == 'width' else drawing.set_drawing_height)(value)
        drawings.append(draw())
    nodes = copy.deepcopy(s['nodes'])
    dimensions = calculate_dimensions(nodes)
    reset_coordinates(nodes)
    node_view = lambda node: [node.get(k, 0) for k in ('x', 'y', 'width', 'height')]
    reset = [node_view(node) for node in nodes]
    state = JsonLayoutSession({'id': 'row-owner'})
    row = BlockRow(state, s['row']['x'], s['row']['y'], s['row']['spacing'])
    old_list = row.rects
    def snap():
        return dict(row=[row.x, row.y, row.width, row.height], nodes=[node_view(node) for node in nodes],
            sameList=row.rects is old_list, count=len(row.rects))
    rows = [snap()]
    for node in nodes:
        row.add_rectangle(node)
        rows.append(snap())
    row.set_x(s['row']['move'][0]); row.set_y(s['row']['move'][1]); rows.append(snap())
    row.update_row(); rows.append(snap())
    row.rects.clear(); row.update_row(); rows.append(snap())
    a = s['aggregate']; aggregate = RectRow(a['y'], a['spacing']); aggregate_list = aggregate.children
    agg = lambda: [aggregate.width, number(aggregate.height)]
    aggregates = [agg()]; aggregate.notify_about_node_change(); aggregates.append(agg())
    absent = Block(state, 0, 0, aggregate, a['spacing'])
    absent.width, absent.height = a['absentWidth'], a['absentHeight']
    aggregate.remove_block(absent); aggregates.append(agg())
    actual = dict(drawings=drawings, scales=[number(compute_scale_measure(*v)) for v in d['scaleInputs']],
        dimensions=[number(dimensions.x), number(dimensions.y)], reset=reset, rows=rows,
        aggregates=aggregates, aggregateListSame=aggregate.children is aggregate_list, layoutExecuted=False)
    comparison = diff(original['observation'], actual)
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Actual drawing cache/scale, dimensions/reset, mutable BlockRow setters/update and RectRow empty sentinels/absent remove only; not packing/search/expand')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
