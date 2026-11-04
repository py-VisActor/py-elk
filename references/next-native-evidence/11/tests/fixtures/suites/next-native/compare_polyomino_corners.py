"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: first native counterpart of saved seven source cases."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5]); source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.polyomino import Polyomino, NORTH, EAST, SOUTH, WEST, compare_corners
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes()); request_value = json.loads(request.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('polyomino-corners-probe.cjs'))
    directions = dict(NORTH=NORTH, EAST=EAST, SOUTH=SOUTH, WEST=WEST)
    rows = []
    for case, expected in zip(request_value['cases'], original['cases'], strict=True):
        assert case['id'] == expected['id']
        first = Polyomino([(directions[name], 0, 0) for name in case['first']])
        second = Polyomino([(directions[name], 0, 0) for name in case['second']])
        value = compare_corners(first, second)
        actual = dict(id=case['id'], firstActualDirections=[d.name for d, _, _ in first.polyomino_extensions],
            secondActualDirections=[d.name for d, _, _ in second.polyomino_extensions], outcome='returned', value=value)
        rows.append(dict(id=case['id'], actual=actual, expected=expected,
            differences=diff(expected, actual)['differences']))
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows,
        sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        newOriginalProcesses=0, layoutExecuted=False, fullValidation=False,
        scope='Only first native corner comparator counterpart of the saved seven actual original cases; no common packer execution or full provider claim')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows))))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
