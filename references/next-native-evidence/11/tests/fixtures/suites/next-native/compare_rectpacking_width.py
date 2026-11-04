"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: new width approximation objects."""
import copy
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5]); source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.rectpacking import AreaApproximation
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('rectpacking-width-probe.cjs'))
    rows = []
    for case, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert case['id'] == expected['id']
        nodes = copy.deepcopy(case['nodes'])
        approximation = AreaApproximation(case['aspectRatio'], case['goal'], case['lastPlaceShift'])
        drawing = approximation.approx_bounding_box(nodes, case['spacing'], case['padding'])
        actual = dict(positions=[[n.get(k, 0) for k in ('x', 'y', 'width', 'height')] for n in nodes],
            drawing=dict(width=drawing.drawing_width, height=drawing.drawing_height, scale=drawing.scale_measure,
                next=[drawing.next_x_coordinate, drawing.next_y_coordinate], descriptor=drawing.placement_option.name),
            layoutExecuted=False)
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
        scope='Actual width candidate/filter/shift helpers on new ordered node objects; no phase default injection or complete rectangle-packing provider')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows))))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
