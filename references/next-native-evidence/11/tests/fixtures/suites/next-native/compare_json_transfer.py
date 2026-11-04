"""Compare a private provider session against saved original observations.

Usage: python compare_json_transfer.py PRIVATE_SRC ORACLE_RECEIPT REPORT
The explicit bottom-up provider calls below are a development harness, not a
complete RecursiveGraphLayoutEngine implementation or public API acceptance.
"""
import hashlib
import json
import base64
from pathlib import Path
import sys


def main():
    source, oracle, report = map(Path, sys.argv[1:])
    root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(source.resolve()))
    sys.path.insert(0, str(root / 'scripts'))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.algorithms import fixed, box, random
    from layout_checks import diff
    package = Path(sys.modules['pyelk'].__file__).parent
    relevant = [package / 'execution/json_transfer.py', package / 'algorithms/fixed.py',
                package / 'algorithms/box.py', package / 'algorithms/random.py']
    identities = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in relevant}
    rows = []
    for c in json.loads(oracle.read_bytes())['cases']:
        request_raw = base64.b64decode(c['requestBytesBase64'])
        observation_raw = base64.b64decode(c['observationBytesBase64'])
        assert hashlib.sha256(request_raw).hexdigest() == c['requestSha256']
        assert hashlib.sha256(observation_raw).hexdigest() == c['observationSha256']
        request, original = json.loads(request_raw), json.loads(observation_raw)
        before = json.dumps(request, sort_keys=True)
        session = JsonLayoutSession(request['graph'])

        def visit(node, inherited='layered'):
            algorithm = session.option(node, 'algorithm', inherited).split('.')[-1]
            for child in node.get('children', []):
                visit(child, algorithm)
            if node.get('children'):
                {'fixed': fixed._layout, 'box': box._layout, 'random': random._layout}[algorithm](session, node)

        visit(session.graph)
        result = session.export()
        strict = diff(original['result'], result)
        mandatory = [d for d in strict['differences'] if d['path'].split('/')[-1] != '$H']
        rows.append(dict(id=c['id'], result=result, strictDifference=strict,
                         mandatoryDifferences=mandatory,
                         inputPreserved=json.dumps(request, sort_keys=True) == before))
    assert identities == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in relevant}
    value = dict(passed=all(not row['mandatoryDifferences'] and row['inputPreserved'] for row in rows),
                 caseCount=len(rows), rows=rows, sourceFilesSha256=identities,
                 oracleSha256=hashlib.sha256(oracle.read_bytes()).hexdigest(),
                 harnessSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 limitations=['All raw strict differences retained. GWT $H is separately identified, not certified equal.',
                              'Explicit harness provider traversal is not full recursive engine, parser or installed/public API acceptance.'])
    report.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(passed=value['passed'], caseCount=len(rows),
                         mandatoryDifferenceCount=sum(len(row['mandatoryDifferences']) for row in rows),
                         strictDifferenceCount=sum(len(row['strictDifference']['differences']) for row in rows))))
    return 0 if value['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
