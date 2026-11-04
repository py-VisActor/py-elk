"""Compare new official radial graphs to the real default-micro native path.

Usage: python compare_radial.py PRIVATE_SRC ORACLE REPORT [CASE_ID]
All strict differences remain; only absent generated runtime $H is classified
separately from the established numeric geometry/business comparison.
"""
import base64
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback


def main():
    source, oracle, report = map(Path, sys.argv[1:4])
    selected = sys.argv[4] if len(sys.argv) > 4 else None
    source = source.resolve()
    sha = lambda b: hashlib.sha256(b).hexdigest()
    def tree():
        return {p.relative_to(source).as_posix(): sha(p.read_bytes()) for p in source.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    before = tree()
    sys.path.insert(0, str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.algorithms import radial
    root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(root / 'scripts'))
    from layout_checks import diff, _GEOMETRY, pointer
    def geometry_status(value):
        invalid, nulls = [], []
        def visit(item, path):
            if _GEOMETRY.fullmatch(path):
                try: finite = type(item) in (int, float) and math.isfinite(item)
                except OverflowError: finite = False
                if not finite: invalid.append(path)
                if item is None: nulls.append(path)
            elif type(item) is dict:
                for key, child in item.items(): visit(child, pointer(path, key))
            elif type(item) is list:
                for index, child in enumerate(item): visit(child, pointer(path, index))
        visit(value, '/result')
        return invalid, nulls
    def hashes(node, path=''):
        result = set() if '$H' in node else {path+'/$H'}
        for i, p in enumerate(node.get('ports', [])):
            if '$H' not in p: result.add(path+'/ports/'+str(i)+'/$H')
        for i, child in enumerate(node.get('children', [])):
            result.update(hashes(child, path+'/children/'+str(i)))
        return result
    original = json.loads(oracle.read_bytes())
    assert original['upstream']['distributionSha256']['lib/elk-worker.js'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    rows = []
    for c in original['cases']:
        if selected and selected != c['id']: continue
        request_raw = base64.b64decode(c['requestBytesBase64'], validate=True)
        observation_raw = base64.b64decode(c['observationBytesBase64'], validate=True)
        assert sha(request_raw) == c['requestSha256'] and sha(observation_raw) == c['observationSha256']
        request = json.loads(request_raw); expected = json.loads(observation_raw)
        assert expected['requestSha256'] == sha(request_raw) and expected['outcome'] == 'returned'
        preserved = copy.deepcopy(request); calls = []
        invalid_reference, null_reference = geometry_status(expected['result'])
        row = dict(id=c['id'], requestSha256=sha(request_raw), observationSha256=sha(observation_raw),
                   upstreamNonfiniteGeometry=bool(null_reference), upstreamNullGeometryPaths=null_reference)
        try:
            state = JsonLayoutSession(request['graph'])
            actual_micro = state.node_micro_layout
            def observe(node):
                calls.append(node['id'])
                return actual_micro(node)
            state.node_micro_layout = observe
            radial._layout(state, state.graph)
            actual = state.export()
            strict = diff(expected['result'], actual, tolerant=False)
            # Established profile paths are rooted under /result; wrapping
            # selects the existing policy without changing its tolerances.
            geometry = diff({'result': expected['result']}, {'result': actual}, tolerant=True)
            generated = {'/result'+p for p in hashes(request['graph'])}
            runtime_hash = lambda d: d['path'] in generated and d['kind'] == 'missing' and type(d.get('expected')) is int
            mandatory = [d for d in geometry['differences'] if not runtime_hash(d)]
            wire_parity = not mandatory and calls == [request['graph']['id']] and diff(preserved, request)['passed']
            invalid_actual, _ = geometry_status(actual)
            row.update(result=actual, strictDifference=strict, geometryBusinessDifference=geometry,
                       mandatoryDifferences=mandatory, observedDefaultMicroCalls=calls,
                       inputPreserved=diff(preserved, request)['passed'],
                       sourceWireParity=wire_parity, validFiniteGeometry=wire_parity and not invalid_reference and not invalid_actual)
        except Exception as error:
            row.update(sourceWireParity=False, validFiniteGeometry=False, errorType=type(error).__name__, error=str(error), traceback=traceback.format_exc(), observedDefaultMicroCalls=calls)
        rows.append(row)
    assert rows and (not selected or len(rows) == 1)
    unchanged = before == tree()
    result = dict(sourceWireParity=unchanged and all(row['sourceWireParity'] for row in rows),
                  validFiniteGeometryCount=sum(row['validFiniteGeometry'] for row in rows),
                  upstreamNonfiniteGeometryCount=sum(row['upstreamNonfiniteGeometry'] for row in rows),
                  rows=rows, sourceTreeSha256=before, sourceTreeUnchanged=unchanged,
                  comparatorSha256=sha(Path(__file__).read_bytes()), oracleSha256=sha(oracle.read_bytes()),
                  comparisonHelperSha256=sha((root/'scripts/layout_checks.py').read_bytes()),
                  scope='Actual private radial provider with real default generic micro; no full/public API or installed package acceptance',
                  referenceReexecuted=False, fullValidation=False, installedPackageValidated=False)
    with report.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(sourceWireParity=result['sourceWireParity'], cases=len(rows),
                          validFiniteGeometryCount=result['validFiniteGeometryCount'],
                          upstreamNonfiniteGeometryCount=result['upstreamNonfiniteGeometryCount'],
                          failed=[row['id'] for row in rows if not row['sourceWireParity']])))
    return 0 if result['sourceWireParity'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
