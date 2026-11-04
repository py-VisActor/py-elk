"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT: one real private DisCo request."""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback


def main():
    source, request_path, original_path, report = map(Path, sys.argv[1:5])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    def tree():
        return {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*')
            if p.is_file() and p.suffix != '.pyc' and '__pycache__' not in p.parts}
    before = tree()
    sys.path.insert(0, str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.algorithms import disco
    root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(root / 'scripts'))
    from layout_checks import diff, _GEOMETRY, pointer
    assert Path(disco.__file__).resolve() == source / 'pyelk/algorithms/disco.py'
    request = json.loads(request_path.read_bytes())
    original = json.loads(original_path.read_bytes())
    assert original['requestSha256'] == sha(request_path)
    assert original['engine']['entrypointSha256'] == 'b1032b7cfd2a57c54c6f0e8369d7665e19a579954f7cd20a6dae28f1912ea0d7'
    assert original['outcome'] == 'returned'
    saved = copy.deepcopy(request)
    def hashes(node, path=''):
        result = set() if '$H' in node else {path + '/$H'}
        for i, port in enumerate(node.get('ports', [])):
            if '$H' not in port:
                result.add(path + '/ports/' + str(i) + '/$H')
        for i, child in enumerate(node.get('children', [])):
            result.update(hashes(child, path + '/children/' + str(i)))
        return result
    def nonfinite(value):
        invalid = []
        def visit(item, path):
            if _GEOMETRY.fullmatch(path):
                if type(item) not in (int, float) or not math.isfinite(item):
                    invalid.append(path)
            elif type(item) is dict:
                for key, child in item.items():
                    visit(child, pointer(path, key))
            elif type(item) is list:
                for index, child in enumerate(item):
                    visit(child, pointer(path, index))
        visit(value, '/result')
        return invalid
    result = dict(sourceWireParity=False, validFiniteGeometry=False,
        originalTermination=original.get('termination'), fullValidation=False,
        installedPackageValidated=False, publicAPIIntegrated=False, wholeAlgorithmAccepted=False)
    calls = dict(micro=[], packComponents=[], invoke=[])
    try:
        constructor = request.get('constructor', {})
        arguments = request.get('layoutArguments', {})
        selected = arguments.get('layoutOptions', constructor.get('defaultLayoutOptions', {}))
        state = JsonLayoutSession(request['graph'], selected)
        real_micro, real_invoke, real_pack = state.node_micro_layout, state.invoke_layout, disco.pack_polyominoes
        def micro(node):
            calls['micro'].append(node['id'])
            return real_micro(node)
        def invoke(*args):
            calls['invoke'].append(args[1])
            return real_invoke(*args)
        def pack(holder):
            calls['packComponents'].append(len(holder.polys))
            return real_pack(holder)
        state.node_micro_layout, state.invoke_layout, disco.pack_polyominoes = micro, invoke, pack
        try:
            disco._layout(state, state.graph)
            actual = state.export()
        finally:
            disco.pack_polyominoes = real_pack
        strict = diff(original['result'], actual)
        geometry = diff({'result': original['result']}, {'result': actual}, tolerant=True)
        generated = {'/result' + path for path in hashes(request['graph'])}
        mandatory = [d for d in geometry['differences'] if not
            (d['path'] in generated and d['kind'] == 'missing' and type(d.get('expected')) is int)]
        preserved = diff(saved, request)['passed']
        wire = not mandatory and preserved and calls == dict(micro=[], invoke=[], packComponents=[2])
        bad_reference, bad_actual = nonfinite(original['result']), nonfinite(actual)
        result.update(sourceWireParity=wire, validFiniteGeometry=wire and not bad_reference and not bad_actual,
            result=actual, strictDifference=strict, geometryBusinessDifference=geometry,
            mandatoryDifferences=mandatory, inputPreserved=preserved,
            originalNonfiniteGeometryPaths=bad_reference, actualNonfiniteGeometryPaths=bad_actual)
    except Exception as error:
        result.update(errorType=type(error).__name__, error=str(error), traceback=traceback.format_exc())
    unchanged = tree() == before
    result['sourceWireParity'] &= unchanged
    result['validFiniteGeometry'] &= unchanged
    result.update(actualDelegatedCalls=calls, sourceTreeUnchanged=unchanged, sourceTreeSha256=before,
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request_path, original_path)},
        comparisonHelperSha256=sha(root / 'scripts/layout_checks.py'),
        scope='One new connected-pair plus isolated component DisCo request with real raster/common packer and geometry transfer. No underlying provider was selected; default Micro correctly not invoked. Raw strict hash differences and original lifecycle retained separately.')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(sourceWireParity=result['sourceWireParity'], validFiniteGeometry=result['validFiniteGeometry'],
        mandatoryDifferences=len(result.get('mandatoryDifferences', [])), error=result.get('error'))))
    return 0 if result['sourceWireParity'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
