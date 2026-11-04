"""Compare the private parser with saved original parser objects.

Usage: python compare_options_parser.py PRIVATE_SRC REQUEST ORACLE REPORT [CASE_ID]
Source null/invalid and nonfinite acceptance are kept visible: the documented
native host returns explicit validation errors instead of silent fallback.
"""
from pathlib import Path
import dataclasses
import hashlib
import json
import sys
from collections.abc import Mapping


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    selected = sys.argv[5] if len(sys.argv) > 5 else None
    original = json.loads(oracle.read_bytes())
    assert original['requestSha256'] == hashlib.sha256(request.read_bytes()).hexdigest()
    def hashes():
        return {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((source / 'pyelk').rglob('*')) if p.is_file()
                and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    before = hashes()
    sys.path.insert(0, str(source.resolve()))
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from pyelk.options.schema import OPTION_SPECS
    from pyelk.options.resolution import _parse
    from layout_checks import diff

    def view(value, spec):
        if isinstance(value, Mapping):
            return {k: view(v, OPTION_SPECS[k]) for k, v in value.items()}
        if type(value) is frozenset:
            return [v for v in spec.accepted_values if v in value]
        if dataclasses.is_dataclass(value):
            return dataclasses.asdict(value)
        return value

    rows = []
    for s, e in zip(json.loads(request.read_bytes())['cases'], original['cases'], strict=True):
        if selected is not None and s['id'] != selected:
            continue
        assert s['id'] == e['id'] and s['value'] == e['input'] and s['option'] == e['option']
        spec = OPTION_SPECS[s['option']]
        try:
            actual = view(_parse(spec, s['value'], ''), spec)
            error = None
        except Exception as exc:
            actual = None
            error = dict(type=type(exc).__name__, code=getattr(exc, 'code', None), message=str(exc))
        expected = e['result']['value']
        explicit_host_policy = expected is None or (type(expected) is dict and 'nonfinite' in expected)
        if explicit_host_policy:
            passed = error is not None and error['code'] == 'INVALID_OPTION_VALUE'
            comparison = None
        else:
            comparison = diff(expected, actual)
            passed = error is None and comparison['passed']
        rows.append(dict(id=s['id'], passed=passed, original=expected, actual=actual, nativeError=error,
                         explicitHostPolicy=explicit_host_policy, comparison=comparison))
    assert rows and hashes() == before
    value = dict(passed=all(row['passed'] for row in rows), count=len(rows), rows=rows, sourceTreeSha256=before,
                 comparatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 originalSha256=hashlib.sha256(oracle.read_bytes()).hexdigest(),
                 scope='Parser primitive only; no243-option/full context/provider/public API acceptance')
    report.write_text(json.dumps(value, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(passed=value['passed'], count=len(rows), failed=[row['id'] for row in rows if not row['passed']])))
    return 0 if value['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
