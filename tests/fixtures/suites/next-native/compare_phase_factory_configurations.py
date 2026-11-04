"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; real default configuration callbacks."""
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
    from pyelk.algorithms.layered.graph import LGraph
    from pyelk.algorithms.layered import phase_factories as f
    from pyelk.algorithms.layered.layout_configuration import LayeredPhase
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('phase-factory-configurations-probe.cjs'))
    registry = f.FactoryRegistry()
    phases = tuple(LayeredPhase)
    main_phases = [registry.phase(p, name).create() for p, name in zip(phases[:4],
        ('GREEDY', 'NETWORK_SIMPLEX', 'LAYER_SWEEP', 'BRANDES_KOEPF'))]
    main_phases.append(registry.edge_routing('ORTHOGONAL').create())
    enums = tuple(f.IntermediateProcessorStrategy)
    def configuration_view(config):
        return None if config is None else [None if bucket is None else
            [value.name for value in enums if value in bucket] for bucket in config.list]
    observations = []
    for item in json.loads(request.read_bytes())['cases']:
        graph = LGraph(None, None, None)
        if item['flags'] is not None:
            graph.properties['GRAPH_PROPERTIES'] = set(item['flags'])
        graph.properties['FEEDBACK_EDGES'] = item['feedback']
        results = []
        for processor in main_phases:
            reads = []
            saved = f.read_layered_scalar
            def traced(holder, native_key, owner_symbol, *args, **kwargs):
                if holder is graph and native_key == 'FEEDBACK_EDGES':
                    reads.append(True)
                return saved(holder, native_key, owner_symbol, *args, **kwargs)
            f.read_layered_scalar = traced
            try:
                a = processor.get_layout_processor_configuration(graph)
                b = processor.get_layout_processor_configuration(graph)
            finally:
                f.read_layered_scalar = saved
            results.append(dict(configuration=configuration_view(a), sameConfiguration=a is b,
                bucketsIndependent=None if a is None else all(v is not b.list[i] for i, v in enumerate(a.list)),
                feedbackReads=len(reads)))
        observations.append(dict(id=item['id'], phases=results,
            graphPropertiesPresent='GRAPH_PROPERTIES' in graph.properties))
    undefined = registry.edge_routing('UNDEFINED')
    ortho = registry.edge_routing('ORTHOGONAL')
    polyline = registry.edge_routing('POLYLINE')
    actual = dict(cases=observations, edgeFactoryIdentity=dict(
        sameUndefined=undefined is registry.edge_routing('UNDEFINED'),
        undefinedVsOrthoDistinct=undefined is not ortho, orthoVsPolylineDistinct=ortho is not polyline),
        sourceObjectApi=True, phaseMathExecuted=False, layoutExecuted=False)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(p in before and sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual,
        expected=original['observation'], comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        checkerSha256=sha(Path(__file__)), phaseMathExecuted=False, layoutExecuted=False,
        scope='Actual five default phase constructors/configuration callbacks and EdgeRouterFactory identity, no phase mathematics',
        fullValidation=False)
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
