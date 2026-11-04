"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: new fill/successor/container objects."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5]); source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.algorithms.disco import DCElement, DCComponent, DCPolyomino, Vec2
    from pyelk.algorithms.polyomino import (successor_jitter, successor_line_by_line,
        successor_manhattan, successor_max_norm, SuccessorQuadrants,
        SuccessorCombination, Polyominoes, EAST, WEST)
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes()); original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('polyomino-traversal-probe.cjs'))
    state = JsonLayoutSession({'id': 'traversal-object-owner'})
    def make():
        w, h = s['size']; component = DCComponent(state)
        component.add_elements([DCElement([Vec2(0, 0), Vec2(w, 0), Vec2(w, h), Vec2(0, h)])])
        poly = DCPolyomino(component, 1, 1)
        for x in range(poly.x_size):
            for y in range(poly.y_size): poly.set(x, y, False, False)
        return poly
    p, other = make(), make(); sequences = {}
    for name, function in [('jitter', successor_jitter), ('lineByLine', successor_line_by_line),
                            ('manhattan', successor_manhattan), ('maxNorm', successor_max_norm)]:
        at = tuple(s['successorStart']); sequence = []
        for _ in range(s['successorSteps']):
            at = function(at); sequence.append(list(at))
        sequences[name] = sequence
    p.polyomino_extensions.append((EAST, 0, 0)); quadrant = SuccessorQuadrants(successor_jitter)
    flags = lambda: [quadrant.pos_x, quadrant.neg_x, quadrant.pos_y, quadrant.neg_y]
    first = list(quadrant(tuple(s['quadrantStart']), p)); first_flags = flags()
    p.polyomino_extensions.clear(); p.polyomino_extensions.append((WEST, 0, 0))
    stale = list(quadrant(tuple(s['quadrantStart']), p)); stale_flags = flags()
    other.polyomino_extensions.append((WEST, 0, 0))
    refreshed = list(quadrant(tuple(s['quadrantStart']), other)); refreshed_flags = flags()
    combination = SuccessorCombination(SuccessorQuadrants(successor_line_by_line), SuccessorQuadrants(successor_jitter))
    combined = list(combination(tuple(s['quadrantStart']), p)); p.polyomino_extensions.clear()
    combined_without = list(combination(tuple(s['quadrantStart']), p))
    for x, y in s['strong']: p.set(x, y, False, True)
    for x, y in s['weak']: p.set(x, y, True, False)
    cells = lambda grid: [[grid.retrieve(x, y) for x in range(grid.x_size)] for y in range(grid.y_size)]
    fill_before = cells(p); input_polys = [p, other]; container = Polyominoes(input_polys, s['aspectRatio'], True)
    actual = dict(sequences=sequences, quadrants=dict(first=first, firstFlags=first_flags,
        stale=stale, staleFlags=stale_flags, refreshed=refreshed, refreshedFlags=refreshed_flags,
        combined=combined, combinedWithoutExtensions=combined_without), fillBefore=fill_before, fillAfter=cells(p),
        container=dict(size=[container.grid.x_size, container.grid.y_size], listOwned=container.polys is not input_polys,
            polysShared=container.polys[0] is p and container.polys[1] is other), layoutExecuted=False)
    comparison = diff(original['observation'], actual)
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)}, layoutExecuted=False,
        fullValidation=False, scope='New deterministic successors, same-poly quadrant cache, strong-cell fill and actual container ownership/grid calculation only; no packing execution')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
