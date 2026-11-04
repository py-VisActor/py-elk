"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: lazy configuration object witness."""
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
    from pyelk.algorithms.layered.layout_configuration import LayoutProcessorConfiguration, LayeredPhase, create_from
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('layout-configuration-probe.cjs'))
    phases = list(LayeredPhase)
    processors = [object() for _ in s['processors']]
    c = LayoutProcessorConfiguration()
    items = c.list
    saved = c.get_list_item(s['initialReadIndex'])
    buckets = list(items)
    initial = dict(currentIndex=c.current_index, length=len(items),
        distinct=all(x is not y for i, x in enumerate(buckets) for j, y in enumerate(buckets) if i != j))
    fluent = c.before(phases[s['beforePhase']]) is c
    for index in s['beforeMembers']:
        c.add(processors[index])
    copied = create_from(c)
    copied_bucket = copied.get_list_item(s['beforePhase'])
    original_bucket = c.get_list_item(s['beforePhase'])
    shares = processors[0] in copied_bucket and processors[0] in original_bucket
    copied_bucket.add(processors[s['copyExtraProcessor']])
    def membership(cfg):
        return [None if bucket is None else [p in bucket for p in processors] for bucket in cfg.list]
    copy_state = dict(listDistinct=copied.list is not items,
        bucketsDistinct=all(a is not b for a, b in zip(copied.list, items)),
        sharesProcessorObjects=shares, currentIndex=copied.current_index,
        original=membership(c), copy=membership(copied))
    tail_fluent = c.add_after(phases[s['tailPhase']], processors[s['tailProcessor']]) is c
    tail = dict(currentIndex=c.current_index, length=len(items), membership=membership(c))
    c.set_list_item(s['nullIndex'], None)
    explicit_null = c.get_list_item(s['nullIndex']) is None
    returned = c.clear()
    clear = dict(returnUndefined=returned is None, listIdentity=c.list is items,
        length=len(c.list), currentIndex=c.current_index, detachedBucketStillAlive=saved is not None)
    fresh = c.get_list_item(s['initialReadIndex'])
    actual = dict(initial=initial, fluent=fluent, copyState=copy_state, tailFluent=tail_fluent,
        tail=tail, explicitNull=explicit_null, clear=clear, newBucket=fresh is not saved,
        newBucketsEmpty=membership(c), sourceObjectApi=True, layoutExecuted=False)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(p in before and sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual,
        expected=original['observation'], comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Source configuration API with supplied processor identities: lazy distinct buckets, fluent cursor, shallow membership copy, explicit null, detached aliases and clear return')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
