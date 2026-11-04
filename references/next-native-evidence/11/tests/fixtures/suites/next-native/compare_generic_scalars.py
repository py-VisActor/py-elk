"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT [CASE_ID]; saved original parser only."""
import hashlib
import json
import os
from pathlib import Path
import sys

source, request_path, oracle_path, output_path = map(Path, sys.argv[1:5])
selected = sys.argv[5] if len(sys.argv) > 5 else None
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
from layout_checks import diff
sys.path.insert(0, str(source.resolve()))
import pyelk
from pyelk.options.generic import METADATA_SCALAR_SPECS, parse_generic_mapping
from pyelk.options.resolution import resolve_options
from pyelk._errors import OptionValidationError, UnknownOptionError, UnsupportedOptionError

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
before = {str(path.relative_to(source)): sha(path) for path in source.rglob('*.py')}
request = json.loads(request_path.read_text('utf-8'))
oracle = json.loads(oracle_path.read_text('utf-8'))
assert oracle['requestSha256'] == sha(request_path)
expected = {row['id']: row for row in oracle['cases']}
rows = []
for case in request['cases']:
    if selected and case['id'] != selected:
        continue
    parsed, raw = parse_generic_mapping({case['option']: case['value']})
    spec = METADATA_SCALAR_SPECS[case['option']]
    value = parsed[case['option']]
    if spec.kind == 'enum_ordinal': value = {'enum': value}
    elif spec.kind == 'enumset':
        assert type(value) is frozenset
        value = {'members': [member for member in spec.accepted_values if member in value]}
    elif spec.kind == 'signed_number': assert type(value) is float
    elif spec.kind == 'integer': assert type(value) is int
    assert raw == {case['option']: case['value']}
    rows.append({'id': case['id'], 'value': value, 'expected': expected[case['id']]['value'],
                 'passed': diff(expected[case['id']]['value'], value)['passed']})
assert rows, 'Select an existing case'
if selected is None:
    for raw, error in [({'elk.alignment': 'CENTER', 'alignment': 'CENTER'}, OptionValidationError),
                       ({'elk.noSuchOption': 'x'}, UnknownOptionError),
                       ({'elk.padding': '[left=3]'}, UnsupportedOptionError),
                       ({'elk.aspectRatio': 'Infinity'}, OptionValidationError)]:
        try: parse_generic_mapping(raw)
        except error: pass
        else: raise AssertionError('Expected declared native validation policy')
    # Generic declarations/explicit parser are isolated from the bounded path.
    bounded = resolve_options()
    assert bounded.values['org.eclipse.elk.edgeRouting'] == 'ORTHOGONAL'
    assert bounded.values['org.eclipse.elk.separateConnectedComponents'] is True
    assert len(METADATA_SCALAR_SPECS) == 225
after = {str(path.relative_to(source)): sha(path) for path in source.rglob('*.py')}
assert before == after
report = {'passed': all(row['passed'] for row in rows), 'cases': rows, 'pid': os.getpid(), 'parentPid': os.getppid(),
          'python': sys.executable, 'modulePath': str(Path(pyelk.__file__).resolve()),
          'sourceBeforeSha256': before, 'sourceAfterSha256': after, 'requestSha256': sha(request_path),
          'oracleSha256': sha(oracle_path), 'parserDeclarations': 225, 'sessionReaderIntegrated': False,
          'layoutExecuted': False, 'fullValidation': False}
with output_path.open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps({'passed': report['passed'], 'cases': len(rows), 'report': str(output_path)}))
raise SystemExit(0 if report['passed'] else 1)
