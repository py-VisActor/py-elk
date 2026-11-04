"""Offline E16--E19 acceptance accounting; never run a product or an oracle.

Build/check the dedicated checklist from existing byte-bound observations.
Strict checking requires the cited saved evidence; missing files are errors,
not an invitation to read another checkout or to accept an embedded PASS.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path('docs/iterations/E16_E19_ACCEPTANCE.json')
MARKDOWN = Path('docs/iterations/E16_E19_ACCEPTANCE.md')
ARCHIVE = Path('references/full-native-closure/algorithms.zip')
MANIFEST = Path('references/full-native-closure/algorithms.manifest.json')
ALGORITHMS = ('fixed', 'box', 'random', 'mrtree', 'radial', 'force', 'stress',
              'disco', 'sporeOverlap', 'sporeCompaction', 'rectpacking')
OLD_ROOT = 'C:/code/py-visactor/py-elk/'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def pointer(value, path):
    for part in path.lstrip('/').split('/') if path else ():
        key = part.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


class Evidence:
    def __init__(self, *, allow_unsealed=False):
        self.files = {}
        self.allow_unsealed = allow_unsealed
        self.members = {}
        self.direct = None
        self.archive_bytes = None
        self.manifest_bytes = None
        if (ROOT / MANIFEST).exists():
            self.manifest_bytes = (ROOT / MANIFEST).read_bytes()
            manifest = json.loads(self.manifest_bytes)
            require(manifest['schema'] == 'pyelk-algorithm-acceptance-evidence/v1', 'Unknown evidence schema')
            require(manifest['archive']['path'] == ARCHIVE.as_posix(), 'Archive path differs')
            self.archive_bytes = (ROOT / ARCHIVE).read_bytes()
            require(digest(self.archive_bytes) == manifest['archive']['sha256'], 'Archive SHA differs')
            self.members = {x['path']: x for x in manifest['members']}
            self.direct = {x['path']: x for x in manifest['requiredRepositoryFiles']}
            require(len(self.members) == len(manifest['members']), 'Duplicate manifest member')
            require(len(self.direct) == len(manifest['requiredRepositoryFiles'])
                    and self.members.keys().isdisjoint(self.direct), 'Duplicate repository dependency')
            for path in self.direct:
                require(self.path(path) == path and not path.startswith(('test-runs/', '.local/')),
                        'Repository dependency is not a direct tracked path')
            for path in self.members:
                require(self.path(path) == path and path.startswith(('test-runs/', '.local/')),
                        'Archive member is not an explicit ignored evidence path')
            import io
            with zipfile.ZipFile(io.BytesIO(self.archive_bytes)) as z:
                require(len(z.namelist()) == len(self.members) and set(z.namelist()) == self.members.keys(),
                        'Archive member set differs')
                self.archived = {}
                for path, entry in self.members.items():
                    raw = z.read(path)
                    require(len(raw) == entry['bytes'] and digest(raw) == entry['sha256'],
                            'Archive member bytes differ: ' + path)
                    self.archived[path] = raw

    def path(self, value):
        name = str(value).replace('\\', '/')
        # A single, explicit historical execution-root mapping. No implicit
        # absolute-path access, original-workspace fallback or search by basename.
        if name.startswith(OLD_ROOT):
            name = name[len(OLD_ROOT):]
        path = Path(name)
        if path.is_absolute() or ':' in name or '..' in path.parts:
            raise ValueError('Evidence path escapes repository: ' + name)
        return name

    def raw(self, value, expected=None):
        name = self.path(value)
        if name.startswith(('test-runs/', '.local/')) and name not in self.members and not self.allow_unsealed:
            raise ValueError('Ignored evidence is not an explicit archive member: ' + name)
        # Explicit archived members always come from the archive, even when an
        # old test-runs file is present. Other files have one repository path.
        raw = self.archived[name] if name in self.members else (ROOT / name).read_bytes()
        sha = digest(raw)
        if expected is not None and sha != expected:
            raise ValueError('Evidence SHA differs: ' + name)
        self.files[name] = {'path': name, 'sha256': sha, 'bytes': len(raw)}
        return raw

    def json(self, value, expected=None):
        return json.loads(self.raw(value, expected))

    def binding(self, value, expected=None):
        self.raw(value, expected)
        return self.files[self.path(value)]

    def validate_closure(self):
        if self.direct is not None:
            declared = self.members | self.direct
            require(self.files.keys() == declared.keys(), 'Manifest does not describe the exact evidence closure')
            require(all(self.files[path] == entry for path, entry in declared.items()),
                    'Manifest evidence bytes/SHA differ')


def require(condition, message):
    if condition is not True:
        raise ValueError(message)


def make(*, updating_archive=False):
    e = Evidence(allow_unsealed=updating_archive)
    authority = {p: e.binding(p) for p in ('docs/TASKS.md', 'docs/ITERATION_PLAN.md')}
    sources = {}
    for iteration, path in (
        ('E16', 'references/e16-basic-sources.json'),
        ('E17', 'references/e17-tree-sources.json'),
        ('E18', 'references/e18-force-stress-sources.json'),
        ('E19', 'references/e19-packing-sources.json'),
    ):
        packet = e.json(path)
        require(packet['baseline']['workerSha256'] ==
                '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86',
                'Source worker identity differs')
        sources[iteration] = {'binding': e.files[path], 'baseline': packet['baseline'],
                              'components': len(packet['components']),
                              'scope': 'Source provenance only; historical pending/status fields are not current acceptance.'}

    suite_path = 'tests/fixtures/suites/full-native-algorithms/cases.json'
    suite = e.json(suite_path)
    comparison_path = 'test-runs/full-native-01/B/comparison-02.json'
    comparison = e.json(comparison_path)
    comparisons = {row['id']: row for row in comparison['rows']}
    public = {name: [] for name in ALGORITHMS}
    for case in suite['cases']:
        request_path = 'tests/fixtures/suites/full-native-algorithms/' + case['request']
        request = e.json(request_path, case['requestSha256'])
        graph = request['graph']
        if not isinstance(graph, dict):
            continue  # API-invalid graph; no algorithm consumer was selected.
        options = graph.get('layoutOptions', {})
        algorithm = next((options[k] for k in ('org.eclipse.elk.algorithm', 'elk.algorithm', 'algorithm')
                          if k in options), None)
        if isinstance(algorithm, str):
            algorithm = algorithm.rsplit('.', 1)[-1]
        if algorithm not in public:
            continue
        row = comparisons[case['id']]
        bound = {}
        for role, folder, key in (('reference', 'reference', 'referenceSha256'),
                                   ('native', 'native', 'nativeSha256')):
            path = f'test-runs/full-native-01/B/{folder}-01/observations/{case["id"]}.json'
            observation = e.json(path, row[key])
            require(observation['requestSha256'] == case['requestSha256'], 'Request binding differs')
            bound[role] = e.files[path]
        if row['status'] == 'PASS':
            require(row['mandatoryDifferences'] == [] and row['inputPreserved'] is True,
                    'Whole-result assertion differs')
        public[algorithm].append({'id': case['id'], 'status': row['status'],
                                  'comparisonPointer': '/rows/' + str(comparison['rows'].index(row)),
                                  'request': e.files[request_path], **bound,
                                  'maxCoordinateError': row.get('coordinateToleranceDifference', {}).get('maxCoordinateError'),
                                  'inputPreserved': row['inputPreserved']})
    require(all(public.values()), 'An algorithm has no public whole-call witness')

    # Re-evaluate the independent predicates against archived raw observations,
    # rather than adopting the report's top-level passed flag.
    geometry_path = 'test-runs/full-native-closure/B/algorithm-geometry-01.json'
    geometry = e.json(geometry_path)
    e.binding('scripts/algorithm_geometry.py')
    e.binding('tests/validation/test_algorithm_geometry.py')
    spec = importlib.util.spec_from_file_location('acceptance_saved_geometry', ROOT / 'scripts/algorithm_geometry.py')
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    archive = e.binding('references/full-native-closure/options.zip', geometry['archiveSha256'])
    with zipfile.ZipFile(ROOT / archive['path']) as z:
        for row in geometry['rows']:
            raw = z.read(row['bindings']['request']['path'])
            require(digest(raw) == row['bindings']['request']['sha256'], 'Geometry request SHA differs')
            request = json.loads(raw)
            for role in ('source', 'native'):
                raw = z.read(row['bindings'][role]['path'])
                require(digest(raw) == row['bindings'][role]['sha256'], 'Geometry observation SHA differs')
                # The checker returns integer depth keys and tuple rectangles;
                # compare its serialized JSON report shape to the saved report.
                assessed = json.loads(json.dumps(checker.assess(request, json.loads(raw)), allow_nan=False))
                require(equal(assessed, row[role]),
                        'Independent geometry predicate changed: ' + row['id'])
    geometry_counts = {role: dict(Counter(row[role]['status'] for row in geometry['rows']))
                       for role in ('source', 'native')}

    performance_path = 'test-runs/full-native-closure/performance-01/installed/report.json'
    performance = e.json(performance_path)
    profiles = performance['profiles']
    require(len(profiles) == 39, 'Performance profile denominator differs')
    for row in profiles:
        require(len(row['samples']) == 5 and row['workerReused'] is True,
                'Performance samples/PID reuse differ')
        pid = row['warmup']['worker']['pid']
        for sample in row['samples']:
            require(sample['worker']['pid'] == pid and sample['wallSeconds'] >= 0
                    and sample['worker']['workingSetBytes'] > 0
                    and sample['worker']['peakWorkingSetBytes'] >= sample['worker']['workingSetBytes'],
                    'OS resource observations differ')
    convergence = performance['convergenceObservations']
    require(sorted((x['algorithm'], x['limit']) for x in convergence) ==
            [(a, limit) for a in ('force', 'stress') for limit in (1, 25, 150)],
            'Iteration-quality denominator differs')
    for row in convergence:
        require(all(math.isfinite(row['quality'][k]) for k in
                    ('meanEdgeLength', 'maxEdgeLength', 'normalizedGraphStress')),
                'Iteration quality metric unavailable')

    # Preserve old private phase execution scopes, including prepared geometry.
    private_paths = [
        'references/next-native-evidence/mrtree-stage-comparison-01.json',
        'test-runs/20261104-E17-01/V/routing-comparison-01/report.json',
        'references/next-native-evidence/05/e18-force-first-comparison-01.json',
        'references/next-native-evidence/05/e18-stress-first-comparison-01.json',
        'references/next-native-evidence/06/test-runs/20261104-E19-01/V/spore-foundation-comparison-01.json',
        'references/next-native-evidence/06/test-runs/20261104-E19-01/V/spore-import-comparison-02.json',
    ]
    private = []
    for path in private_paths:
        d = e.json(path)
        rows = d.get('rows', d.get('cases', []))
        private.append({'report': e.files[path], 'scope': d.get('scope'),
                        'cases': [{'id': x['id'], 'assertionPointers':
                                   [f'/{"cases" if "cases" in d else "rows"}/{i}'],
                                   'hasActualObservation': 'actual' in x or 'result' in x}
                                  for i, x in enumerate(rows)],
                        'sourceWireParity': d.get('sourceWireParity'),
                        'historicalPrivateNotPublishedExecution': True})
        if 'sourceWireParity' in d:
            require(d['sourceWireParity'] is True, 'Historical numeric differential differs')
        for x in rows:
            if 'comparison' in x:
                require(x['comparison']['differences'] == [], 'Stage differential differs')
            if 'differences' in x:
                require(x['differences'] == [], 'Private object differential differs')
    for path in ('tests/fixtures/suites/next-native/mrtree-stages-request.json',
                 'tests/fixtures/suites/next-native/mrtree-stages-oracle.json',
                 'tests/fixtures/suites/next-native/mrtree-routing-request.json',
                 'tests/fixtures/suites/next-native/mrtree-routing-oracle.json',
                 'tests/fixtures/suites/next-native/spore-foundation-oracle.json',
                 'tests/fixtures/suites/next-native/spore-import-recorded-oracle.json'):
        e.binding(path)

    effects_path = 'test-runs/full-native-closure/A/nonlayered-effects-wrapper-corrected-01.json'
    effects = e.json(effects_path)
    require(len(effects['rows']) == 52, 'Normal non-Layered differential denominator differs')
    effect_rows = []
    for row in effects['rows']:
        require(row['comparison']['passed'] is True, 'Saved whole-call comparison failed')
        for role in ('request', 'reference', 'native'):
            e.binding(row[role]['path'], row[role]['sha256'])
        effect_rows.append({'id': row['id'],
                            'wholeComparisonPointer': f'/rows/{len(effect_rows)}/comparison',
                            'verifiedEffects': [a['option'] for a in row['assertions'] if a['passed'] is True],
                            'unverifiedEffects': [a['option'] for a in row['assertions'] if a['passed'] is not True]})
    ledger = e.json('docs/option-coverage.json')
    ledger_scope = {'summary': ledger['summary'],
                    'nonLayeredOptions': [{'id': x['id'],
                                         'geometry': x['effects']['layoutGeometry'],
                                         'state': x['effects']['runtimeState'],
                                         'assertionIds': [a['id'] for a in x['effects']['assertions']]}
                                        for x in ledger['options'] if any(x['id'].startswith('org.eclipse.elk.' + p)
                                        for p in ('stress.', 'force.', 'mrtree.', 'radial.', 'polyomino.',
                                                  'disco.', 'overlapRemoval.', 'rectpacking.',
                                                  'processingOrder.', 'compaction.'))]}

    repair_paths = ['cycle-termination.json', 'valid-tree-regression.json', 'valid-phase-report.json',
                    'valid-phase-revisit.json', 'valid-phase-deep.json', 'review.json']
    repair = {}
    for name in repair_paths:
        path = 'docs/releases/evidence/runtime-repair/' + name
        repair[name] = e.json(path)
        for case in repair[name].get('cases', []):
            for role in ('request', 'reference', 'native', 'nativeCommand'):
                if isinstance(case.get(role), dict):
                    e.binding(case[role]['path'], case[role]['sha256'])
    cycle_case = repair['cycle-termination.json']['cases'][0]
    source_cycle = e.json(cycle_case['reference']['path'])
    native_cycle = e.json(cycle_case['native']['path'])
    require(source_cycle['outcome'] == native_cycle['outcome'] == 'threw'
            and source_cycle['error']['name'] == 'RangeError'
            and native_cycle['error']['name'] == 'RecursionError', 'Cycle error policies differ')
    for name in ('valid-phase-revisit.json', 'valid-phase-deep.json'):
        require(equal(repair[name]['reference'], repair[name]['native']), 'Legal native regression differs')
        require(repair[name]['referenceRole'] == 'immutable-pre-repair-native-regression',
                'A native-only regression was relabelled as Source')

    lifecycle_path = 'test-runs/20261104-FULL/V/lifecycle-full-01/observation.json'
    lifecycle = e.json(lifecycle_path)
    running = lifecycle['runningTimeout']
    timeout = running['attempts'][running['qualifiedAttempt']]
    cpus = [x['cpuSeconds'] for x in timeout['phaseEvents']]
    require(len(cpus) >= 2 and cpus[-1] > cpus[0] and timeout['pidBefore']['alive'] is True
            and timeout['pidAfter']['alive'] is False
            and timeout['error']['type'] == 'ExecutionTimeoutError'
            and running['inputBeforeSha256'] == running['inputAfterSha256'],
            'Real CPU/PID/timeout/input observations differ')
    require(running['afterRecovery']['jobs'][-1]['state'] == 'returned', 'Timeout recovery differs')
    # Keep precise actual snapshots available; do not reinterpret a private
    # busy-worker negative control as real Force CPU work.
    lifecycle_scope = {'binding': e.files[lifecycle_path], 'schema': lifecycle['schema'],
                       'runningTimeoutFields': list(running),
                       'actualRunningTimeout': {'pointer': '/runningTimeout/attempts/' + str(running['qualifiedAttempt']),
                                                'pid': timeout['pidBefore']['pid'], 'cpuSeconds': cpus,
                                                'error': timeout['error'], 'pidDeadAfter': True,
                                                'inputPreservedSha256': running['inputBeforeSha256'],
                                                'recoveryReturned': True},
                       'crossThreadClosePIDDead': lifecycle['crossThreadClose']['pidAfter']['alive'] is False,
                       'scope': 'Full-native real running CPU/timeout/recovery; queued-timeout and cross-thread-close use their explicitly labelled private busy-host controls.'}

    publication_path = 'test-runs/full-native-closure/V/published-release-audit-01.json'
    publication = e.json(publication_path)
    wheel_path = 'test-runs/full-native-closure/pypi-0.1.0-download-verified/py_visactor_elk-0.1.0-py3-none-any.whl'
    wheel_sha = publication['publishedArtifactsSha256']['py_visactor_elk-0.1.0-py3-none-any.whl']
    wheel = e.binding(wheel_path, wheel_sha)
    with zipfile.ZipFile(io.BytesIO(e.raw(wheel_path, wheel_sha))) as z:
        runtime = {name: digest(z.read(name)) for name in z.namelist() if name.startswith('pyelk/') and not name.endswith('/')}
    require(len(runtime) == 208, 'Published runtime denominator differs')
    for name, sha in runtime.items():
        e.binding('src/' + name, sha)
    published_performance_path = 'docs/changes/20261104-published-mrtree-performance.json'
    published_performance = e.json(published_performance_path)
    require(published_performance['wheelSha256'] == wheel_sha
            and published_performance['runtimeFilesSha256'] == runtime,
            'Published MrTree performance runtime identity differs')
    require(sorted((x['algorithm'], x['nodes']) for x in published_performance['profiles']) ==
            [('mrtree', 8), ('mrtree', 32), ('mrtree', 96)]
            and published_performance['convergenceObservations'] == [],
            'Published performance delta scope differs')
    for profile in published_performance['profiles']:
        require(len(profile['samples']) == 5 and profile['workerReused'] is True
                and len({x['resultSha256'] for x in profile['samples']}) == 1,
                'Published MrTree sample count/stability differs')
        require(all(x['worker']['pid'] == profile['warmup']['worker']['pid']
                    and x['worker']['workingSetBytes'] > 0
                    and x['worker']['peakWorkingSetBytes'] >= x['worker']['workingSetBytes']
                    for x in profile['samples']), 'Published MrTree resource observation differs')
    measured_math = {}
    for algorithm in ALGORITHMS:
        module = 'spore' if algorithm.startswith('spore') else algorithm
        name = 'pyelk/algorithms/' + module + '.py'
        measured = performance['runtimeFilesSha256'][name]
        published = runtime[name]
        if module == 'mrtree':
            require(measured == repair['valid-phase-report.json']['beforeModuleSha256'] and
                    published == repair['valid-phase-report.json']['candidateModuleSha256'],
                    'Measured-to-published MrTree repair relation differs')
        else:
            require(measured == published, 'Measured algorithm math differs from publication: ' + module)
        measured_math[algorithm] = {'measuredModuleSha256': measured, 'publishedModuleSha256': published,
                                    'relation': 'explicit-runtime-repair' if module == 'mrtree' else 'byte-identical'}
    install_summaries = []
    for installed in publication['actualInstallations']:
        summary = e.json(installed['summaryPath'], installed['summarySha256'])
        require(installed['runtimeFiles'] == 208 and installed['imports'] == 196
                and installed['metadata'] == [12, 243, 8]
                and all(c['exitCode'] == 0 for c in installed['commands']), 'Published installation scope differs')
        install_summaries.append({'kind': installed['kind'], 'binding': e.files[installed['summaryPath']],
                                  'commands': installed['commands'], 'mrtreeCycleObserved': installed['mrtreeCycleObserved']})

    former_missing = [
        ('org.eclipse.elk.mrtree.weighting', 'DESCENDANTS'),
        ('org.eclipse.elk.mrtree.weighting', 'CONSTRAINT'),
        ('org.eclipse.elk.mrtree.edgeRoutingMode', 'NONE'),
        *[('org.eclipse.elk.radial.optimizationCriteria', x) for x in
          ('NONE', 'EDGE_LENGTH', 'EDGE_LENGTH_BY_POSITION', 'CROSSING_MINIMIZATION_BY_POSITION')],
    ]
    e17_path = 'test-runs/full-native-closure/B/e17-enum-owner-01/handoff.json'
    e17 = e.json(e17_path)
    require(e17['schema'] == 'pyelk-e17-enum-runtime-handoff/v1' and len(e17['rows']) == 7,
            'Finite E17 witness denominator differs')
    pending_bindings = [e17]
    while pending_bindings:
        item = pending_bindings.pop()
        if isinstance(item, dict):
            if isinstance(item.get('path'), str) and isinstance(item.get('sha256'), str):
                e.binding(item['path'], item['sha256'])
            pending_bindings.extend(item.values())
        elif isinstance(item, list):
            pending_bindings.extend(item)
    branch_witnesses = []
    diagnostics = []
    for row, (option, value) in zip(e17['rows'], former_missing):
        ref = e.json(row['sourceRaw']['path'], row['sourceRaw']['sha256'])
        nat = e.json(row['nativeRaw']['path'], row['nativeRaw']['sha256'])
        require(ref['workerSha256'] == sources['E17']['baseline']['workerSha256'],
                'E17 Source worker differs')
        prepared = e17['sourceConstraintCorrection'] if row['id'] == 'mrtree-constraint' else e17
        require(ref['requestSha256'] == prepared['request']['sha256']
                and ref['probeSha256'] == prepared['probe']['sha256']
                and nat['requestSha256'] == e17['request']['sha256'],
                'E17 prepared request/probe binding differs')
        for name, sha in nat['sourceFilesSha256'].items():
            require(runtime.get('pyelk/' + name) == sha, 'E17 executed module differs from publication: ' + name)
        require(len(nat['sourceFilesSha256']) == 196 and nat['sourceFilesUnchanged'] is True,
                'E17 executed module closure differs')
        ref_result = pointer(ref, row['sourcePointer'])
        nat_result = pointer(nat, row['nativePointer'])
        require(ref_result['outcome'] == nat_result['outcome'] == 'returned', 'E17 prepared task failed')
        a, b = ref_result['value'].copy(), nat_result['value'].copy()
        require(a['id'] == b['id'] == row['id'], 'E17 witness identity differs')
        evaluations_a = a.pop('evaluations', [])
        evaluations_b = b.pop('evaluations', [])
        # Explicit observer-only receiver names differ across implementations.
        # They are not JSON business fields or a numeric-tolerance projection.
        a.pop('called', None)
        b.pop('called', None)
        optimizer_types = b.pop('nativeOptimizerTypes', None)
        require(equal(a, b), 'E17 final geometry/control state differs: ' + row['id'])
        differences = [{'index': i, 'source': x, 'native': y,
                        'absoluteError': abs(x-y), 'sourceULPs': abs(x-y) / math.ulp(x),
                        'relativeError': abs(x-y) / abs(x) if x else None}
                       for i, (x, y) in enumerate(zip(evaluations_a, evaluations_b)) if x != y]
        require(len(evaluations_a) == len(evaluations_b), 'E17 objective count differs')
        if row['id'].startswith('radial-'):
            require(a['observerDelegatesOriginal'] is True, 'E17 observer did not delegate')
            require(a['factoryEvents'] == [{'strategy': value, 'isNull': value == 'NONE'}],
                    'E17 real factory selection differs')
            require(len(evaluations_a) == (0 if value == 'NONE' else 360), 'E17 evaluation count differs')
        else:
            require(a['selected'] == value, 'E17 actual MrTree selection differs')
        minimum = None
        if evaluations_a:
            first = min(range(len(evaluations_a)), key=evaluations_a.__getitem__)
            second = min(range(len(evaluations_b)), key=evaluations_b.__getitem__)
            require(first == second, 'E17 chosen angle index differs')
            ordered = sorted(evaluations_a)
            minimum = {'sourceIndex': first, 'nativeIndex': second,
                       'sourceMinimum': evaluations_a[first],
                       'sourceSecondMinimumGap': ordered[1] - ordered[0]}
        if differences:
            require(row['strictAllNumericComparison']['passed'] is False
                    and row['objectivesExact'] is False, 'E17 diagnostic differences were hidden')
            diagnostics.append({'id': row['id'], 'status': 'diagnostic_numeric_difference',
                                'privateObjectiveScope': True, 'exact': False,
                                'differences': differences, 'maxULPs': max(x['sourceULPs'] for x in differences),
                                'minimum': minimum,
                                'sourceFormulaAnchor': {'path': 'references/e17-tree-sources.json',
                                                        'component': 'R08', 'lines': [64473, 64583],
                                                        'spanSha256': '041cfea7935e5900c92b200385a531ddb83cedaadfb38a499e9f39d44ffcfca5'},
                                'nativeFormulaAnchor': {'path': 'src/pyelk/algorithms/radial.py',
                                                        'symbols': ['EdgeLengthOptimization.evaluate',
                                                                    'EdgeLengthPositionOptimization.evaluate']},
                                'assessment': 'Source/native expression and ordered accumulation match; 1-2 ULP differences are compatible with host binary64 transcendental/sqrt rounding. Saved sums do not uniquely locate the primitive responsible. No evidence of a formula/order defect.',
                                'policy': 'Retain exact=false and every raw scalar difference. No tolerance/profile change, no inference of stable optimizer choices for arbitrary near ties.'})
        branch_witnesses.append({'id': row['id'], 'option': option, 'value': value,
                                 'source': row['sourceRaw'], 'sourcePointer': row['sourcePointer'],
                                 'native': row['nativeRaw'], 'nativePointer': row['nativePointer'],
                                 'sourceFunction': row['sourceFunction'], 'nativeFunction': row['nativeFunction'],
                                 'actualPreparedPhase': True, 'publicWholeAPICall': False,
                                 'finalGeometryAndControlStateExact': True,
                                 'objectiveCount': len(evaluations_a), 'objectivesExact': not differences,
                                 'optimizerTypes': optimizer_types, 'minimum': minimum,
                                 'status': 'witnessed_scoped_with_numeric_diagnostic' if differences else 'witnessed_scoped'})
    require(len(diagnostics) == 2 and sum(len(x['differences']) for x in diagnostics) == 11,
            'E17 raw diagnostic denominator differs')
    diagnostic_path = 'test-runs/full-native-closure/B/e17-enum-owner-01/objective-ulp-diagnosis.json'
    independent_diagnostic = e.json(diagnostic_path)
    for observed, independent in zip(diagnostics, independent_diagnostic['rows']):
        require(observed['id'] == independent['id']
                and len(observed['differences']) == independent['exactDifferences']
                and observed['maxULPs'] == independent['maximumUlpDistance'],
                'Independent ULP diagnosis differs')
    radial_policy = e.binding('docs/decisions/0016-radial-private-objective-observations.md')
    gaps = []

    def criterion(identifier, iteration, condition, status, evidence, conclusion, limitations=()):
        return {'id': identifier, 'iteration': iteration, 'condition': condition, 'status': status,
                'evidence': evidence, 'conclusion': conclusion, 'limitations': list(limitations)}

    criteria = [
        criterion('E16-provenance-metadata', 'E16', 'Three separate implementations/provenance/metadata/applicable options', 'met_scoped',
                  ['source:E16', 'B151', 'optionLedger', 'publishedPayload'],
                  'Fixed, Box and Random each have a fixed Source inventory, distinct public calls, typed parser/accounting and actual published runtime modules.',
                  ['Registered/parsed options are not full effect coverage; frozen ledger preserves all unverified options.']),
        criterion('E16-fixed', 'E16', 'Given geometry, transfer, options, inputs/errors, coordinates', 'met_scoped',
                  ['B151:fixed', 'nonLayered52', 'publishedPayload'],
                  'Fixed supplied geometry, sizes/minimum/ports/labels/bends/junctions and missing-section Source error have individual calls. No claim that Source error paths are successful geometry.'),
        criterion('E16-box', 'E16', 'Packing and independent options/positions', 'met_scoped',
                  ['B151:box', 'nonLayered52', 'independentGeometry'],
                  'Four packing modes, priority/interactive/expansion/minimum cases and independent SIMPLE/GROUP_DEC containment/nonoverlap predicates exist.'),
        criterion('E16-random', 'E16', 'Random stream, coordinates/seed, input and entropy boundaries', 'met_scoped',
                  ['B151:random', 'nonLayered52', 'source:E16'],
                  'Seeded and negative-seed/edge/port paths have deterministic coordinate witnesses; unseeded case remains NONDETERMINISTIC_OBSERVATION.',
                  ['No V8 entropy trajectory equality or nonoverlap guarantee.']),
        criterion('E16-performance', 'E16', 'Per-algorithm performance evidence', 'met_scoped',
                  ['performance39'], 'Each of the three has actual n8/32/96, warm1/formal5 wall/OS CPU/memory observations.',
                  ['Windows CPython3.13 only, pre-MrTree-repair 0.1 payload; no all-platform or universal resource bound.']),
        criterion('E17-tree-semantics', 'E17', 'Forests/roots/levels/subtrees/directions/non-tree input', 'met_scoped',
                  ['B151:mrtree', 'MrTree-stage9', 'MrTree-routing3', 'MrTreeRepair', 'independentGeometry'],
                  'Zero/one/many roots, DFS/BFS cycle/parallel inputs, depth/subtree state, asymmetric directions and prepared routing have saved assertions. Cyclic sibling path now fails promptly under an explicit native policy; legal revisit/deep chain remain valid.',
                  ['Source RangeError and native RecursionError are different and are not declared exception parity.', 'Independent depth-band predicate applies to a simple unique-rooted tree with compaction=false.']),
        criterion('E17-radial-semantics', 'E17', 'Circular/radial geometry and non-tree semantics', 'met_scoped',
                  ['B151:radial', 'nonLayered52', 'independentGeometry'],
                  'Default and explicit radius have independent depth-ring/minimum-increment predicates; compactor/sorter/wedge/rotation cases retain their Source outcomes.',
                  ['WEDGE/POLAR/rotation has an upstream nonfinite wire observation, not valid finite geometry PASS.', 'No assertion of radial rectangle nonoverlap or an exactly depth*radius formula.']),
        criterion('E17-declared-branches', 'E17', 'All declared branch differentials', 'met_scoped_with_numeric_diagnostics',
                  ['B151', 'nonLayered52', 'MrTree-stage9', 'MrTree-routing3', 'source:E17', 'E17FiniteBranches'],
                  'Seven formerly unmapped values now have actual prepared phase/factory/evaluate witnesses, supplementing the existing public calls. Final geometry/control/chosen offset match exactly.',
                  ['These seven are actual private prepared phases, not seven new public whole-API calls.',
                   'Two length objectives retain 11 exact scalar differences (maximum2ULP). Source/native expression/accumulation order matches; precise libm primitive cause is not proven. No profile/tolerance upgrade.']),
        criterion('E18-initialization-iteration', 'E18', 'Initial values/seed/iterations/convergence/termination', 'met_scoped',
                  ['B151:force', 'B151:stress', 'forceStressPrivate', 'nonLayered52', 'performance39', 'hostLifecycle'],
                  'Both Force models, supplied interactive coordinates, seeded initialization, Stress X/Y/fixed/edge-length/epsilon and iteration limits have real calls/effect assertions. Force/Stress iteration1/25/150 quality and real host CPU timeout/recovery are measured.',
                  ['An epsilon causal final-geometry assertion does not reveal the exact inner-loop termination iteration.', 'No Force monotone-stress claim or unconstrained-input termination theorem.']),
        criterion('E18-numeric-quality', 'E18', 'Pointwise error/resources and independently decided numeric profiles', 'met_scoped',
                  ['B151:force', 'B151:stress', 'forceStressPrivate', 'nonLayered52', 'performance39'],
                  'Saved whole-result pointwise differences and strict effect pointers remain separate; existing coordinate1e-6/1e-9 policy was not widened. Quality includes overlaps/edge lengths/normalized graph stress and actual worker resources.',
                  ['Force repulsion strict effect parity remains unverified where a small floating difference exists; not silently promoted.', 'Normalized shortest-path stress is a descriptive metric, not every algorithm objective.']),
        criterion('E19-separate-providers', 'E19', 'Four algorithms separately accepted with actual dependencies indexed', 'met_scoped',
                  ['source:E19', 'B151:disco', 'B151:sporeOverlap', 'B151:sporeCompaction', 'B151:rectpacking', 'publishedPayload'],
                  'Each has its own real public calls/performance rows/module; Source index records shared triangulation, polyomino, typed state, generic margin and optional underlying-provider dependencies.'),
        criterion('E19-disco', 'E19', 'Components/shapes/input positions/constraints/quality', 'met_scoped',
                  ['B151:disco', 'nonLayered52', 'independentGeometry', 'source:E19'],
                  'Inter-component leaf-rectangle separation and component-spacing effects are witnessed; component interior layout is preserved unless a real underlying algorithm is explicitly invoked.',
                  ['Interlocking component bounding boxes may overlap; no false bbox-separation or packing-optimality requirement.']),
        criterion('E19-sporeOverlap', 'E19', 'Overlap removal, initial positions, objective/constraints', 'met_scoped',
                  ['B151:sporeOverlap', 'nonLayered52', 'SporePrivateObjects', 'independentGeometry'],
                  'Real initially overlapping geometry, cost/update/transfer object assertions and scanline-enabled independent no-overlap/containment predicates exist.',
                  ['Scanline-disabled observation is NOT_ASSESSED by that independent predicate; no all-option overlap theorem.']),
        criterion('E19-sporeCompaction', 'E19', 'Compaction, initial positions, objective/constraints/quality', 'met_scoped',
                  ['B151:sporeCompaction', 'nonLayered52', 'SporePrivateObjects', 'performance39'],
                  'Distinct contraction provider, original/working-coordinate and numeric objective transitions plus actual public effects/performance are saved.',
                  ['ShrinkTree is not an overlap-removal guarantee; no demand for universal area decrease or global optimum.']),
        criterion('E19-rectpacking', 'E19', 'Packing strategies/objectives/constraints/quality', 'met_scoped',
                  ['B151:rectpacking', 'nonLayered52', 'independentGeometry', 'source:E19'],
                  'Real packing provider, strategy/target-width/optimization effects and independent COMPACTION/SIMPLE containment/nonoverlap predicates exist.',
                  ['NONE placement is not asserted nonoverlapping, no packing-optimality claim.']),
        criterion('cross-release-boundary', 'E16-E19', 'Current deliverable, host lifecycle and actual payload identity', 'met_scoped',
                  ['publishedPayload', 'MrTreeRepair', 'hostLifecycle'],
                  'Actual uploaded/downloaded 0.1.0 wheel runtime208 equals current src; actual Windows wheel/sdist and Linux wheel observations bind imports196/metadata12,243,8 and real20node calls.',
                  ['Historical source/native/performance runs retain their executed source hashes and are not relabelled as published-package reruns.', 'E12 publication is complete separately; E20/E21 all-branch acceptance is not implied.']),
    ]
    if not updating_archive:
        e.validate_closure()
    return {'schema': 'pyelk-e16-e19-acceptance/v1', 'authority': authority,
            'scope': 'Finite explicit TASKS M7-01..04 and ITERATION_PLAN E16..E19 conditions only.',
            'iterations': [{'id': n, 'status': 'met_scoped_with_numeric_diagnostics' if n == 'E17' else 'met_scoped',
                            'algorithmDenominator': list(group)} for n, group in
                           [('E16', ALGORITHMS[:3]), ('E17', ALGORITHMS[3:5]),
                            ('E18', ALGORITHMS[5:7]), ('E19', ALGORITHMS[7:])]],
            'criteria': criteria, 'minimumRemainingGaps': gaps,
            'E17FiniteBranches': {'handoff': e.files[e17_path], 'rows': branch_witnesses,
                                 'diagnostics': diagnostics,
                                 'independentULPReport': e.files[diagnostic_path],
                                 'numericObservationDecision': radial_policy,
                                 'firstConstraintSourcePreparationErrorRetained': True,
                                 'sourceConstraintCorrection': e17['sourceConstraintCorrection'],
                                 'sourceCalls': 8, 'nativeCalls': 7,
                                 'rawInternalScalarExactForAllCases': False,
                                 'oldMatricesReexecuted': False},
            'sourceProvenance': sources,
            'public151': {'report': e.files[comparison_path], 'allCounts': comparison['counts'],
                          'algorithms': public, 'executedBaseline': '0.0.1a0 public native; historical hashes retained'},
            'nonLayered52': {'report': e.files[effects_path], 'rows': effect_rows,
                             'scope': '52 returned Source calls; whole comparison uses established geometry tolerance; failed strict effects remain unverified.'},
            'independentGeometry': {'report': e.files[geometry_path], 'counts': geometry_counts,
                                    'observations': 28, 'rows': geometry['rows'],
                                    'savedRawReevaluated': True, 'layoutExecutions': 0},
            'performance39': {'report': e.files[performance_path], 'executedWheelSha256': performance['wheelSha256'],
                              'executedPlatform': performance['platform'], 'executedPython': performance['python'],
                              'profiles': [{'algorithm': x['algorithm'], 'nodes': x['nodes'],
                                            'options': x['options'], 'statistics': x['statistics'],
                                            'quality': x['quality'], 'sampleCount': len(x['samples'])} for x in profiles],
                              'formalSamples': 195, 'warmups': 39, 'iterationQuality': convergence,
                              'algorithmModuleRelationToPublishedPayload': measured_math,
                              'isPublishedRuntimeRerun': False},
            'publishedMrTreePerformanceDelta': {'report': e.files[published_performance_path],
                                               'wheelSha256': wheel_sha, 'runtime208Exact': True,
                                               'warmups': 3, 'formalSamples': 15,
                                               'profiles': [{'algorithm': x['algorithm'], 'nodes': x['nodes'],
                                                             'statistics': x['statistics'], 'quality': x['quality']}
                                                            for x in published_performance['profiles']],
                                               'otherAlgorithmsReexecuted': False,
                                               'iterationQualityReexecuted': False},
            'privateAssertions': private, 'optionLedger': ledger_scope,
            'MrTreeRepair': {'bindings': [e.files['docs/releases/evidence/runtime-repair/' + p] for p in repair_paths],
                             'sourceError': 'RangeError', 'nativeError': 'RecursionError',
                             'exactSourceExceptionParity': False, 'newOracleCapture': False},
            'hostLifecycle': lifecycle_scope,
            'publishedPayload': {'audit': e.files[publication_path], 'wheel': wheel,
                                 'runtimeCount': 208, 'runtimeByteEqualityRechecked': True,
                                 'sourceCommit': publication['sourceCommit'], 'installations': install_summaries,
                                 'releaseURL': publication['releaseURL']},
            'allE16E19UnconditionallyComplete': False, 'e20E21Complete': False,
            'newExecutions': {'layout': 0, 'source': 0, 'performance': 0, 'platform': 0, 'install': 0},
            'pathPolicy': {'executionRootMap': {OLD_ROOT.rstrip('/'): '.'},
                           'missingEvidence': 'fail', 'implicitWorkspaceFallback': False},
            'evidenceStorage': ({'archive': {'path': ARCHIVE.as_posix(), 'sha256': digest(e.archive_bytes)},
                                 'manifest': {'path': MANIFEST.as_posix(), 'sha256': digest(e.manifest_bytes)},
                                 'archivedIgnoredFiles': len(e.members),
                                 'directRepositoryFiles': len(e.files) - len(e.members),
                                 'resolver': 'Only explicit manifest members use the archive; tracked dependencies use the current repository path and SHA. No workspace fallback.'}
                                if e.archive_bytes is not None else None),
            'evidence': sorted(e.files.values(), key=lambda x: x['path'])}


def seal_evidence():
    current = make(updating_archive=True)
    evidence = Evidence(allow_unsealed=True)
    archived = [x for x in current['evidence'] if x['path'].startswith(('test-runs/', '.local/'))]
    direct = [x for x in current['evidence'] if x not in archived]
    import io
    content = io.BytesIO()
    with zipfile.ZipFile(content, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for row in archived:
            raw = evidence.raw(row['path'], row['sha256'])
            info = zipfile.ZipInfo(row['path'], (2026, 11, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, raw, compresslevel=9)
    raw_zip = content.getvalue()
    manifest = {'schema': 'pyelk-algorithm-acceptance-evidence/v1',
                'scope': 'Only files actually read by E16_E19_ACCEPTANCE; original bytes and historical paths unchanged.',
                'archive': {'path': ARCHIVE.as_posix(), 'sha256': digest(raw_zip), 'bytes': len(raw_zip)},
                'members': archived, 'requiredRepositoryFiles': direct,
                'originalExecutionRootMap': {OLD_ROOT.rstrip('/'): '.'},
                'sourceSnapshotsCopied': False, 'missingOrUnlistedEvidence': 'fail',
                'productsExecuted': 0}
    (ROOT / ARCHIVE).write_bytes(raw_zip)
    (ROOT / MANIFEST).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n',
                                 encoding='utf-8', newline='\n')


def markdown(d):
    lines = ['# E16–E19 明示退出条件核对', '',
             '这是既有保存材料的离线核对，不改变机器计划、选项账本或发布状态。', '',
             '| 批次 | 独立算法 | 结论 |', '| --- | --- | --- |']
    for x in d['iterations']:
        lines.append(f'| {x["id"]} | {", ".join(x["algorithmDenominator"])} | {x["status"]} |')
    lines += ['', '“met_scoped”表示明示能力已有真实、限定输入/数值政策的证据；不表示无限输入或所有选项值已穷尽。',
             'E17 原七个有限声明缺项已由新的真实 prepared phase/factory/evaluate 见证补齐；两个长度目标保留内部数值诊断，不宣称全标量 exact。', '',
              '| 条件 | 状态 | 证据及范围 |', '| --- | --- | --- |']
    for x in d['criteria']:
        lines.append(f'| {x["id"]}: {x["condition"]} | {x["status"]} | {x["conclusion"]} ' +
                     ' '.join(x['limitations']) + ' |')
    lines += ['', '## 必要剩余项', '', '| 选项 | 值 | 状态 |', '| --- | --- | --- |']
    for x in d['minimumRemainingGaps']:
        lines.append(f'| `{x["option"]}` | `{x["value"]}` | {x["status"]} |')
    lines += ['', '本次明示有限见证缺项为0；这不等于243选项或无限输入组合完成。新增七个是私有准备对象中的实际 Source/native phase，不能冒称七次公共API整调用。',
              'EDGE_LENGTH 内部9个目标值最大2ULP，BY_POSITION内部2值最大1ULP；全部最终节点/控制状态和所选角度index exact。原数组差异仍 exact=false，不调容差/不升profile。',
              '两个实现公式和顺序一致，但保存的总和不足以唯一定位三角函数还是sqrt的宿主舍入；EDGE_LENGTH最优/次优仅隔2.84e-14，不外推任意近似平局稳定。', '',
              '数值边界决定见 [ADR0016](../decisions/0016-radial-private-objective-observations.md)；既有严格失败不被改成标量通过。', '',
              '## 新补证与边界', '',
              '- 原39个性能配置：195次正式、39次预热，另6次 Force/Stress 迭代质量观察；实际 Windows/CPython3.13，旧执行字节不回绑发布包。随后仅发布版 MrTree 追加3配置/15正式/3预热，其 wheel SHA 及208运行字节严格等实际发布包；其余36配置的算法字节未变，未重跑。',
              '- 独立几何14个请求、Source/native各14：20个 PASS、8个 NOT_ASSESSED，无已适用谓词失败；本工具重新从冻结 options.zip 的原始 JSON 求值。',
              '- MrTree 源 RangeError/旧候选不终止保留。active-path 修复明确返回 native RecursionError；合法8node、重复child返回后再访及1500深链回归独立保存。',
              '- Force/Stress 逐点差异、严格效果与既有坐标容差分开；Force repulsion 的严格效果未证保持原状。Stress epsilon 已有因果几何变化，不凭耗时猜具体终止迭代。',
              '- SPOrE 原始/工作位置、cost/update/transfer 准备对象和真实整调用互不混称；SporeCompaction 无移除全部重叠的承诺，DisCo 不要求 interlocking 组件包围盒互不交叠。',
              '- 发布 wheel 的208运行文件逐字节对当前 src 重核；Windows wheel/sdist 和实际 GitHub Linux wheel 安装范围分别保留。发布成功只关闭独立 E12，不关闭 E20/E21。', '',
              '## 复核方式', '',
              '`python scripts/iteration/e16_e19_acceptance.py --check --root-map C:/code/py-visactor/py-elk=.`', '',
              '纯读保存证据及独立几何求值，不导入 pyelk、不运行 Source/布局/安装/性能。严格核对需要 JSON 内引用的保存文件；缺失/SHA错误直接失败，不借原工作区隐式外援。',
              '所需 ignored 原材料原字节位于 `references/full-native-closure/algorithms.zip`，成员及SHA由同目录 `algorithms.manifest.json` 明列；已跟踪文件仍直接读当前repo并核SHA。archive成员即使原test-runs存在也只从zip读，不依赖旧工作区。', '',
              f'完整证据路径/SHA、逐算法调用、精确 JSONPointer、条件结论见 [{OUTPUT.name}]({OUTPUT.name})。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--seal-evidence', action='store_true', help='Incrementally seal the exact evidence closure, then rebuild this checklist')
    parser.add_argument('--root-map', action='append', default=[], help='Explicit historical root mapping; only the documented original-root=. mapping is accepted')
    args = parser.parse_args()
    if sum((args.build, args.check, args.seal_evidence)) != 1:
        parser.error('choose exactly one of --build, --check or --seal-evidence')
    if any(x.replace('\\', '/') != OLD_ROOT.rstrip('/') + '=.' for x in args.root_map):
        parser.error('only the documented original execution root to current repository mapping is accepted')
    if args.seal_evidence:
        seal_evidence()
    else:
        require((ROOT / MANIFEST).is_file(), 'Portable evidence manifest is required')
    result = make()
    text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    md = markdown(result)
    if args.build or args.seal_evidence:
        (ROOT / OUTPUT).write_text(text, encoding='utf-8', newline='\n')
        (ROOT / MARKDOWN).write_text(md, encoding='utf-8', newline='\n')
    else:
        require((ROOT / OUTPUT).read_text(encoding='utf-8') == text, 'Acceptance JSON differs')
        require((ROOT / MARKDOWN).read_text(encoding='utf-8') == md, 'Acceptance Markdown differs')
    print(json.dumps({'schema': result['schema'], 'evidenceFiles': len(result['evidence']),
                      'statuses': {x['id']: x['status'] for x in result['iterations']},
                      'finiteGaps': len(result['minimumRemainingGaps']), 'productsExecuted': 0}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
