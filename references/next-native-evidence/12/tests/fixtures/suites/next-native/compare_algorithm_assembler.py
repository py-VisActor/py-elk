"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: source assembler callback fixture."""
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
    from pyelk.algorithms.layered.layout_configuration import LayoutProcessorConfiguration, LayeredPhase
    from pyelk.algorithms.layered.algorithm_assembler import AlgorithmAssembler
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('algorithm-assembler-probe.cjs'))
    phases = list(LayeredPhase)
    graph = object()
    events, counts, bodies, factories = [], {}, {}, {}
    def configuration(rows):
        cfg = LayoutProcessorConfiguration()
        for when, phase, name in rows:
            method = cfg.add_before if when == 'before' else cfg.add_after
            method(phases[phase], factories[name])
        return cfg
    class Processor:
        def __init__(self, name):
            self.name = name
        def get_layout_processor_configuration(self, received):
            events.append(dict(kind='config', name=self.name, graphIdentity=received is graph))
            return configuration(s['configurations'].get(self.name, []))
    class Factory:
        def __init__(self, name, ordinal):
            self.name, self.ordinal = name, ordinal
        def create(self):
            name = self.name
            counts[name] = counts.get(name, 0) + 1
            events.append(dict(kind='create', name=name))
            if name == 'NULL':
                return None
            body = Processor(name)
            bodies[body] = name + '#' + str(counts[name])
            return body
    for index, name in enumerate(dict.fromkeys(n for n in s['mainFactories'] if n is not None)):
        factories[name] = Factory(name, index)
    for index, name in enumerate(s['processorFactories']):
        factories[name] = Factory(name, index)
    assembler = AlgorithmAssembler()
    def configure(names):
        for index, name in enumerate(names):
            assembler.set_phase(phases[index], None if name is None else factories[name])
    configure(s['mainFactories'])
    assembler.add_processor_configuration(configuration(s['additional']))
    def build():
        start = len(events)
        algorithm = assembler.build(graph)
        return dict(events=events[start:], algorithm=[bodies[p] for p in algorithm])
    first, second = build(), build()
    items, cache, additional = assembler.list, assembler.cache, assembler.additional_processors
    returned = assembler.reset()
    reset_state = dict(returnSelf=returned is assembler, listIdentity=assembler.list is items,
        cacheIdentity=assembler.cache is cache, additionalIdentity=assembler.additional_processors is additional,
        configured=len(assembler.configured_phases), listLength=len(assembler.list), additionalLength=len(additional.list))
    configure(s['resetMainFactories'])
    after_reset = build()
    factory = factories[s['uncachedFactory']]
    cached = assembler.retrieve_processor(factory)
    start = len(events)
    assembler.enable_caching = False
    one, two = assembler.retrieve_processor(factory), assembler.retrieve_processor(factory)
    assembler.enable_caching = True
    after = assembler.retrieve_processor(factory)
    uncached = dict(events=events[start:], bodies=[bodies[one], bodies[two]],
        distinct=one is not two, oldCacheRestored=cached is after)
    first_null = assembler.retrieve_processor(factories['NULL'])
    second_null = assembler.retrieve_processor(factories['NULL'])
    missing = AlgorithmAssembler()
    event_count = len(events)
    rejected = False
    try:
        missing.build(graph)
    except RuntimeError:
        rejected = True
    actual = dict(first=first, second=second, resetState=reset_state, afterReset=after_reset,
        uncached=uncached, cachedNull=first_null is None and second_null is None,
        nullCreates=counts['NULL'], missingRejected=rejected, missingCreatesNothing=len(events) == event_count,
        layoutExecuted=False, suppliedFactoryCallbacks=True)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(p in before and sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual,
        expected=original['observation'], comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Actual source assembler with supplied factory/config callbacks, not phase math: all main creations before configs, ordinal intermediate buckets, repeated cached identity/null, reset and disabled-cache transitions')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
