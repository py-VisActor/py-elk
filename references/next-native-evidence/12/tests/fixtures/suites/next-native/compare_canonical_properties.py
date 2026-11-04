"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: exact-id shallow property binding."""
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
    from pyelk.algorithms.layered.graph import LGraph
    from pyelk.algorithms.layered.native_properties import bind_native_properties, CanonicalPropertyMap
    from pyelk.algorithms.layered.integer_box_tokens import IntegerBoxToken
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('canonical-properties-probe.cjs'))
    state = JsonLayoutSession(s)
    snapshot = state.property_snapshot(state.graph)
    graph = LGraph(None, None, None)
    bag = bind_native_properties(graph, snapshot)
    key = 'org.eclipse.elk.force.model'
    present = key in bag
    value = bag[key] if present else None
    actual = dict(keys=sorted(bag), foreignFullIdPresent=present, foreignValue=value,
        foreignValueShared=present and value is snapshot.values['force.model'], layoutExecuted=False)
    comparison = diff(original['observation'], actual, tolerant=False)
    # This is the previously declared native Integer-assignment policy, not a
    # claim that generic erased Java PropertyHolder rejects Boolean values.
    policy_bag = CanonicalPropertyMap({'MODEL_ORDER': 0})
    rejected = False
    try:
        policy_bag.integer_boxes['MODEL_ORDER'] = IntegerBoxToken(False)
    except TypeError:
        rejected = True
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(p in before and sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and comparison['passed'] and rejected,
        actual=actual, expected=original['observation'], comparison=comparison,
        nativeAssignmentPolicy=dict(boolTokenRejected=rejected), sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Actual imported foreign registered Property id survives shallow copy/binding; separate native Integer token policy rejects bool payload, no source erased-PropertyHolder type claim')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']), boolTokenRejected=rejected)))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
