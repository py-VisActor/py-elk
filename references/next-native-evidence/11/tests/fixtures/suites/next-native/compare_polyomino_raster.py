"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: new raster/overlay object comparison."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.algorithms.disco import (DCElement, DCComponent, DCExtension,
        DCPolyomino, Vec2, NORTH, EAST, SOUTH, WEST)
    from pyelk.algorithms.polyomino import PlanarGrid
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff

    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('polyomino-raster-probe.cjs'))
    directions = dict(NORTH=NORTH, EAST=EAST, SOUTH=SOUTH, WEST=WEST)
    cells = lambda grid: [[grid.retrieve(x, y) for x in range(grid.x_size)] for y in range(grid.y_size)]
    rows = []
    for case, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert case['id'] == expected['id']
        state = JsonLayoutSession({'id': 'raster-identity-owner'})
        elements = [DCElement([Vec2(*point) for point in polygon]) for polygon in case['polygons']]
        for item in case['extensions']:
            DCExtension(elements[item['element']], directions[item['direction']], Vec2(*item['middle']), item['width'])
        component = DCComponent(state)
        component.add_elements(elements)
        poly = DCPolyomino(component, *case['cellSize'])
        dest = PlanarGrid(*case['destination'])
        for x, y, value in case['existing']:
            dest.set(x, y, bool(value & 2), bool(value & 1))
        raster = cells(poly)
        filled_bounds = list(poly.get_filled_bounds())
        extensions = [[direction.name, start, end] for direction, start, end in poly.polyomino_extensions]
        collision_before = dest.intersects_polyomino(poly, *case['offset'])
        dest.add_polyomino(poly, *case['offset'])
        actual = dict(dimensions=[poly.p_width, poly.p_height], raster=raster,
            filledBounds=filled_bounds, extensions=extensions, position=[poly.x, poly.y],
            destination=cells(dest), destinationBounds=list(dest.get_filled_bounds()),
            collisionBefore=collision_before, collisionAfter=dest.intersects_polyomino(poly, *case['offset']),
            representeeSame=poly.representee is component, layoutExecuted=False)
        rows.append(dict(id=case['id'], actual=actual, expected=expected['value'],
            differences=diff(expected['value'], actual)['differences']))
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows,
        sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Actual DCPolyomino construction, strict raster predicates, extension rays, center-based overlay/collision and filled bounds only; no common packer/provider claim')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
