"""Build finite Layered branch accounting from saved data only.

No pyelk import, subprocess, oracle call or layout execution. Configured class
names and input option occurrence are retained separately from task witnesses.
"""
from __future__ import annotations

import argparse
import ast
import base64
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LAYERED = ROOT / 'src/pyelk/algorithms/layered'
OUT = ROOT / 'docs/iterations/FULL_DECLARED_BRANCH_MATRIX.json'
SOURCE = 'references/next-layered-processor-classes-sources.json'
SUMMARY = 'test-runs/20261104-HOST-19/A/full-layered-summary-01.json'
ARCHIVE = ROOT / 'references/full-native-closure/branches.zip'
MANIFEST = ARCHIVE.with_suffix('.manifest.json')
OPTIONS_ARCHIVE = ROOT / 'references/full-native-closure/options.zip'
OPTIONS_MANIFEST = OPTIONS_ARCHIVE.with_suffix('.manifest.json')
P1_P2_MAP = 'test-runs/full-native-closure/B/p1-p2-runtime-witness-map-01.json'
LOGGED_REPORT = 'test-runs/full-native-closure/B/missing-p1-p2-runtime-01/report.json'
LOGGED_SUITE = 'tests/fixtures/suites/missing-p1-p2-runtime/cases.json'
GREEDY_ONE = {
    'request': 'test-runs/20261104-HOST-11/V/greedy-phase-one-oracle-01/request-original.json',
    'sourceProbe': 'test-runs/20261104-HOST-11/V/greedy-phase-one-oracle-01/probe-original.cjs',
    'sourceRaw': 'test-runs/20261104-HOST-11/V/greedy-phase-one-oracle-01/observation.json',
    'nativeRaw': 'test-runs/20261104-HOST-11/V/greedy-phase-one-comparison-01/comparison.json',
    'nativeChecker': 'tests/fixtures/suites/next-native/compare_greedy_phase.py',
}
SPLINE_PREPARED = {
    'request': 'test-runs/20261104-HOST-17/B/spline-final-caller-request.json',
    'sourceProbe': 'test-runs/20261104-HOST-17/B/spline-final-caller-probe-01.cjs',
    'sourceRaw': 'test-runs/20261104-HOST-17/B/spline-final-caller-original-01/observation.json',
    'nativeRaw': 'test-runs/20261104-HOST-17/B/spline-final-caller-native-01/report.json',
    'nativeChecker': 'test-runs/20261104-HOST-17/B/spline-final-caller-native-01/checker-executed.py',
}
EFFECT_REPORTS = ['option-effects-corrected-observables.json', 'option-effects-second.json',
                  'option-effects-third-local-port-corrected.json', 'option-effects-fourth.json',
                  'option-effects-fifth.json', 'option-effects-sixth.json', 'option-effects-seventh.json']
FAMILY_OPTIONS = {
    'CycleBreakingStrategy': 'org.eclipse.elk.layered.cycleBreaking.strategy',
    'LayeringStrategy': 'org.eclipse.elk.layered.layering.strategy',
    'CrossingMinimizationStrategy': 'org.eclipse.elk.layered.crossingMinimization.strategy',
    'NodePlacementStrategy': 'org.eclipse.elk.layered.nodePlacement.strategy',
    'EdgeRouting': 'org.eclipse.elk.edgeRouting',
}

# Literal source task names. Prefixes are used only for the two source tasks
# which interpolate an actual strategy, not to approximate arbitrary names.
TASKS = {
    'DIRECTION_PREPROCESSOR': 'Graph transformation (TO_INPUT_DIRECTION)',
    'DIRECTION_POSTPROCESSOR': 'Graph transformation (TO_INTERNAL_LTR)',
    'COMMENT_PREPROCESSOR': 'Comment pre-processing',
    'COMMENT_POSTPROCESSOR': 'Comment post-processing',
    'COMMENT_NODE_MARGIN_CALCULATOR': 'Node margin calculation',
    'EDGE_AND_LAYER_CONSTRAINT_EDGE_REVERSER': 'Edge and layer constraint edge reversal',
    'PARTITION_PREPROCESSOR': 'Partition preprocessing',
    'PARTITION_MIDPROCESSOR': 'Partition midprocessing',
    'PARTITION_POSTPROCESSOR': 'Partition postprocessing',
    'LABEL_DUMMY_INSERTER': 'Label dummy insertions',
    'LABEL_DUMMY_REMOVER': 'Label dummy removal',
    'LABEL_DUMMY_SWITCHER': 'Label dummy switching',
    'SELF_LOOP_PREPROCESSOR': 'Self-Loop pre-processing',
    'SELF_LOOP_POSTPROCESSOR': 'Self-Loop post-processing',
    'SELF_LOOP_PORT_RESTORER': 'Self-Loop ordering',
    'SELF_LOOP_ROUTER': 'Self-Loop routing',
    'LAYER_CONSTRAINT_PREPROCESSOR': 'Layer constraint preprocessing',
    'LAYER_CONSTRAINT_POSTPROCESSOR': 'Layer constraint postprocessing',
    'HIERARCHICAL_PORT_CONSTRAINT_PROCESSOR': 'Hierarchical port constraint processing',
    'HIERARCHICAL_PORT_DUMMY_SIZE_PROCESSOR': 'Hierarchical port dummy size processing',
    'HIERARCHICAL_PORT_POSITION_PROCESSOR': 'Hierarchical port position processing',
    'HIERARCHICAL_PORT_ORTHOGONAL_EDGE_ROUTER': 'Orthogonally routing hierarchical port edges',
    'HIERARCHICAL_NODE_RESIZER': 'Resize child graph to fit parent.',
    'NODE_PROMOTION': 'Node promotion heuristic',
    'SEMI_INTERACTIVE_CROSSMIN_PROCESSOR': 'Semi-Interactive Crossing Minimization Processor',
    'BREAKING_POINT_INSERTER': 'Breaking Point Insertion',
    'BREAKING_POINT_PROCESSOR': 'Breaking Point Processor',
    'BREAKING_POINT_REMOVER': 'Breaking Point Removing',
    'LONG_EDGE_SPLITTER': 'Edge splitting', 'LONG_EDGE_JOINER': 'Edge joining',
    'PORT_SIDE_PROCESSOR': 'Port side processing', 'PORT_LIST_SORTER': 'Port order processing',
    'INVERTED_PORT_PROCESSOR': 'Inverted port preprocessing',
    'SORT_BY_INPUT_ORDER_OF_MODEL': 'Sort By Input Model ',
    'NORTH_SOUTH_PORT_PREPROCESSOR': 'Odd port side processing',
    'NORTH_SOUTH_PORT_POSTPROCESSOR': 'Odd port side processing',
    'ONE_SIDED_GREEDY_SWITCH': 'Minimize Crossings ONE_SIDED_GREEDY_SWITCH',
    'TWO_SIDED_GREEDY_SWITCH': 'Minimize Crossings TWO_SIDED_GREEDY_SWITCH',
    'SINGLE_EDGE_GRAPH_WRAPPER': 'Path-Like Graph Wrapping',
    'IN_LAYER_CONSTRAINT_PROCESSOR': 'Layer constraint edge reversal',
    'LABEL_AND_NODE_SIZE_PROCESSOR': 'Node and Port Label Placement and Node Sizing',
    'INNERMOST_NODE_MARGIN_CALCULATOR': 'Node margin calculation',
    'END_LABEL_PREPROCESSOR': 'End label pre-processing',
    'END_LABEL_POSTPROCESSOR': 'End label post-processing',
    'END_LABEL_SORTER': 'Sort end labels', 'LABEL_SIDE_SELECTOR': 'Label side selection (',
    'HYPEREDGE_DUMMY_MERGER': 'Hyperedge merging',
    'NODE_PLACEMENT_REPEATER': 'Node placement repeater',
    'LAYER_SIZE_AND_GRAPH_HEIGHT_CALCULATOR': 'Layer size calculation',
    'CONSTRAINTS_POSTPROCESSOR': 'Constraints Postprocessor',
    'HYPERNODE_PROCESSOR': 'Hypernodes processing',
    'HORIZONTAL_COMPACTOR': 'Horizontal Compaction',
    'REVERSED_EDGE_RESTORER': 'Restoring reversed edges',
    'CENTER_LABEL_MANAGEMENT_PROCESSOR': 'Label management',
    'END_NODE_PORT_LABEL_MANAGEMENT_PROCESSOR': 'Label management',
}
PHASE_TASKS = {
    ('CycleBreakingStrategy', 'GREEDY'): 'Greedy cycle removal',
    ('CycleBreakingStrategy', 'DEPTH_FIRST'): 'Depth-first cycle removal',
    ('CycleBreakingStrategy', 'INTERACTIVE'): 'Interactive cycle breaking',
    ('CycleBreakingStrategy', 'MODEL_ORDER'): 'Model order cycle breaking',
    ('CycleBreakingStrategy', 'GREEDY_MODEL_ORDER'): 'Greedy cycle removal',
    ('CycleBreakingStrategy', 'SCC_CONNECTIVITY'): 'Model order cycle breaking',
    ('CycleBreakingStrategy', 'SCC_NODE_TYPE'): 'Model order cycle breaking',
    ('CycleBreakingStrategy', 'DFS_NODE_ORDER'): 'Depth-first cycle removal',
    ('CycleBreakingStrategy', 'BFS_NODE_ORDER'): 'Breadth-first cycle removal',
    ('LayeringStrategy', 'NETWORK_SIMPLEX'): 'Network simplex layering',
    ('LayeringStrategy', 'LONGEST_PATH'): 'Longest path layering',
    ('LayeringStrategy', 'LONGEST_PATH_SOURCE'): 'Longest path to source layering',
    ('LayeringStrategy', 'COFFMAN_GRAHAM'): 'Coffman-Graham Layering',
    ('LayeringStrategy', 'INTERACTIVE'): 'Interactive node layering',
    ('LayeringStrategy', 'MIN_WIDTH'): 'MinWidth layering',
    ('LayeringStrategy', 'STRETCH_WIDTH'): 'StretchWidth layering',
    ('LayeringStrategy', 'BF_MODEL_ORDER'): 'Breadth first model order layering',
    ('LayeringStrategy', 'DF_MODEL_ORDER'): 'Depth first model order layering',
    ('CrossingMinimizationStrategy', 'LAYER_SWEEP'): 'Minimize Crossings BARYCENTER',
    ('CrossingMinimizationStrategy', 'MEDIAN_LAYER_SWEEP'): 'Minimize Crossings MEDIAN',
    ('CrossingMinimizationStrategy', 'INTERACTIVE'): 'Interactive crossing minimization',
    ('CrossingMinimizationStrategy', 'NONE'): 'No crossing minimization',
    ('NodePlacementStrategy', 'SIMPLE'): 'Simple node placement',
    ('NodePlacementStrategy', 'INTERACTIVE'): 'Interactive node placement',
    ('NodePlacementStrategy', 'LINEAR_SEGMENTS'): 'Linear segments node placement',
    ('NodePlacementStrategy', 'BRANDES_KOEPF'): 'Brandes & Koepf node placement',
    ('NodePlacementStrategy', 'NETWORK_SIMPLEX'): 'Network simplex node placement',
    ('EdgeRouting', 'UNDEFINED'): 'Orthogonal edge routing',
    ('EdgeRouting', 'ORTHOGONAL'): 'Orthogonal edge routing',
    ('EdgeRouting', 'POLYLINE'): 'Polyline edge routing',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=None)
def blob(path):
    if path.startswith('test-runs/'):
        manifest = json.loads(MANIFEST.read_text('utf-8'))
        if sha(ARCHIVE.read_bytes()) != manifest['archiveSha256']:
            raise ValueError('Branch archive digest differs')
        expected = manifest['members'][path]
        with zipfile.ZipFile(ARCHIVE) as archive:
            data = archive.read(path)
        if sha(data) != expected:
            raise ValueError('Branch archive member differs: ' + path)
        return data
    return (ROOT / path).read_bytes()


def read(path):
    return json.loads(blob(path))


def binding(path):
    result = {'path': path, 'sha256': sha(blob(path))}
    if path.startswith('test-runs/'):
        result.update(archive=ARCHIVE.relative_to(ROOT).as_posix(), member=path)
    return result


def seal_archive():
    """Explicit one-time packaging; never used by ordinary build/check."""
    summary = json.loads((ROOT / SUMMARY).read_text('utf-8'))
    paths = [SUMMARY]
    for row in summary['cases']:
        if row.get('matched'):
            base = 'test-runs/20261104-HOST-19/A/' + row['batch'] + '/' + row['id'] + '/'
            paths.extend(base + name for name in ('reference.json', 'candidate.json', 'comparison.json'))
    members = {}
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            raw = (ROOT / path).read_bytes()
            info = zipfile.ZipInfo(path, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
            members[path] = sha(raw)
    MANIFEST.write_text(json.dumps({'schema': 'pyelk-declared-branch-archive/v1',
                                   'archive': ARCHIVE.relative_to(ROOT).as_posix(),
                                   'archiveSha256': sha(ARCHIVE.read_bytes()),
                                   'members': members}, indent=2) + '\n', 'utf-8')


def extend_archive():
    """Add only explicit saved observations; preserve prior member bytes."""
    with zipfile.ZipFile(ARCHIVE) as archive:
        data = {name: archive.read(name) for name in archive.namelist()}
    before = sha(ARCHIVE.read_bytes())
    evidence = json.loads((ROOT / P1_P2_MAP).read_text('utf-8'))
    paths = {P1_P2_MAP, LOGGED_REPORT, *SPLINE_PREPARED.values(), *GREEDY_ONE.values()}
    for row in json.loads((ROOT / LOGGED_REPORT).read_text('utf-8'))['rows']:
        paths.update(x['path'] for x in row['bindings'].values())
    logged_directory = ROOT / LOGGED_REPORT.rsplit('/', 1)[0]
    paths.update(p.relative_to(ROOT).as_posix() for p in logged_directory.rglob('*') if p.is_file())
    for row in evidence['strongPreparedWitnesses'] + evidence['publicSelectionAssociationsNotDirectTrace']:
        paths.update(x['path'] for x in row['bindings'].values() if x['path'].startswith('test-runs/'))
    for path in paths:
        raw = (ROOT / path).read_bytes()
        if path in data and data[path] != raw:
            raise ValueError('Refusing to replace a historical member: ' + path)
        data[path] = raw
    preserved = ROOT / 'test-runs/full-native-closure/A/declared-branches-02'
    for source in (ARCHIVE, MANIFEST):
        destination = preserved / ('before-increment-' + source.name)
        if not destination.exists():
            destination.write_bytes(source.read_bytes())
    with zipfile.ZipFile(ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path, raw in sorted(data.items()):
            info = zipfile.ZipInfo(path, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    MANIFEST.write_text(json.dumps({'schema': 'pyelk-declared-branch-archive/v1',
                                   'archive': ARCHIVE.relative_to(ROOT).as_posix(),
                                   'archiveSha256': sha(ARCHIVE.read_bytes()),
                                   'previousArchiveSha256': before,
                                   'members': {path: sha(raw) for path, raw in sorted(data.items())}}, indent=2) + '\n', 'utf-8')


def equal(left, right):
    """JSON value equality: booleans are not numbers; number encodings agree."""
    if type(left) in (int, float) and type(right) in (int, float):
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(equal(a, b) for a, b in zip(left, right))
    return left == right


def pointer(value, path):
    if path == '':
        return value
    for part in path[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def verify_state_projections(assertions, source, native):
    projections = []
    for assertion in assertions:
        expected, actual = pointer(source, assertion['sourcePointer']), pointer(native, assertion['nativePointer'])
        if not equal(expected, actual) or not equal(expected, assertion['expected']) or not equal(actual, assertion['actual']):
            raise ValueError('Prepared Source/native state does not agree')
        projections.append(dict(assertion, strictEqual=True))
    return projections


def verify_causal_values(expected, actual, source_before, native_before, assertion):
    if not (equal(expected, actual) and equal(expected, assertion['expected']) and equal(actual, assertion['actual'])
            and equal(source_before, native_before) and not equal(source_before, expected)):
        raise ValueError('Enum causal effect does not reproduce')


@lru_cache(maxsize=None)
def option_blob(path):
    manifest = json.loads(OPTIONS_MANIFEST.read_text('utf-8'))
    if sha(OPTIONS_ARCHIVE.read_bytes()) != manifest['archive']['sha256']:
        raise ValueError('Changed options evidence archive')
    entry = next(x for x in manifest['files'] if x['path'] == path)
    if entry['storage'] == 'archive':
        with zipfile.ZipFile(OPTIONS_ARCHIVE) as archive:
            data = archive.read(path)
    else:
        data = (ROOT / path).read_bytes()
    if sha(data) != entry['sha256']:
        raise ValueError('Changed options evidence member: ' + path)
    return data


def option_binding(item):
    path = item['path']
    if PureWindowsPath(path).is_absolute():
        original = json.loads(OPTIONS_MANIFEST.read_text('utf-8'))['originalExecutionRoot']
        path = PureWindowsPath(path).relative_to(PureWindowsPath(original)).as_posix()
    raw = option_blob(path)
    if sha(raw) != item['sha256']:
        raise ValueError('Effect row binding differs: ' + path)
    return {'path': path, 'sha256': sha(raw), 'archive': OPTIONS_ARCHIVE.relative_to(ROOT).as_posix(), 'member': path}, json.loads(raw)


def add_prepared(rows):
    by_id = {row['id']: row for row in rows}
    mapping = read(P1_P2_MAP)
    for entry in mapping['strongPreparedWitnesses']:
        bindings = entry['bindings']
        for item in bindings.values():
            if binding(item['path'])['sha256'] != item['sha256']:
                raise ValueError('Prepared evidence binding differs')
        source, native = read(bindings['sourceRaw']['path']), read(bindings['nativeRaw']['path'])
        if source['requestSha256'] != bindings['request']['sha256'] or source['probeSha256'] != bindings['sourceProbe']['sha256']:
            raise ValueError('Prepared original request/probe differs')
        projections = verify_state_projections(entry['stateProjections'], source, native)
        row = by_id[entry['id']]
        row['witnesses'].append({'id': entry['id'] + ':historical-object', 'kind': 'object-state-assertion',
                                 'evidenceMap': binding(P1_P2_MAP), 'bindings': {k: binding(v['path']) for k, v in bindings.items()},
                                 'assertions': projections, 'sourceFunction': entry['sourceFunction'],
                                 'sourceCall': entry['sourceCall'], 'nativeCalls': entry['nativeCalls'],
                                 'historicalNativeModuleSha256': entry['historicalNativeModuleSha256'],
                                 'historicalRuntimeReboundToCurrentModule': False,
                                 'scope': 'Historical real owner.process and actual state; not a fresh current-module execution.'})
        row['status'] = 'witnessed_scoped'
    for entry in mapping['publicSelectionAssociationsNotDirectTrace']:
        for item in entry['bindings'].values():
            if binding(item['path'])['sha256'] != item['sha256']:
                raise ValueError('Public strategy association binding differs')
        by_id[entry['id']]['publicSelectionAssociations'] = [entry]
    source, native = read(SPLINE_PREPARED['sourceRaw']), read(SPLINE_PREPARED['nativeRaw'])
    if (source['requestSha256'] != binding(SPLINE_PREPARED['request'])['sha256']
            or source['probeSha256'] != binding(SPLINE_PREPARED['sourceProbe'])['sha256']
            or source.get('actualProcess86Executed') is not True or source.get('actualProcess11Executed') is not True
            or not equal(source['value'], native['actual'])):
        raise ValueError('Actual P5-to-Final prepared state does not agree')
    for row_id in ('factory:EdgeRouting:SPLINES', 'factory:IntermediateProcessorStrategy:FINAL_SPLINE_BENDPOINTS_CALCULATOR'):
        row = by_id[row_id]
        row['witnesses'].append({'id': 'historical-spline-p5-to-final', 'kind': 'object-state-assertion',
                                 'bindings': {k: binding(v) for k, v in SPLINE_PREPARED.items()},
                                 'referencePointer': '/value', 'nativePointer': '/actual',
                                 'strictStateEqual': True, 'caseCount': len(source['value']['cases']),
                                 'historicalRuntimeReboundToCurrentModule': False,
                                 'scope': 'Actual Source process86→process11 and native P5→Final, supplied prepared graph; no public monitor invented.'})
        row['status'] = 'witnessed_scoped'
    source, native = read(GREEDY_ONE['sourceRaw']), read(GREEDY_ONE['nativeRaw'])
    if (source['requestSha256'] != binding(GREEDY_ONE['request'])['sha256']
            or source['probeSha256'] != binding(GREEDY_ONE['sourceProbe'])['sha256']
            or source['observation'].get('crossingPhaseExecuted') is not True
            or source['observation'].get('strategy') != 'ONE_SIDED_GREEDY_SWITCH'
            or not equal(source['observation'], native['actual'])):
        raise ValueError('Actual ONE_SIDED phase state does not agree')
    row = by_id['factory:IntermediateProcessorStrategy:ONE_SIDED_GREEDY_SWITCH']
    row['witnesses'].append({'id': 'historical-greedy-one-phase', 'kind': 'object-state-assertion',
        'bindings': {k: binding(v) for k, v in GREEDY_ONE.items()},
        'referencePointer': '/observation', 'nativePointer': '/actual', 'strictStateEqual': True,
        'historicalRuntimeReboundToCurrentModule': False,
        'scope': 'Actual Source process76/controller and native phase: counts, sweep, ports, order, RNG and named ONE_SIDED monitor; prepared graph, not a public full layout.'})
    row['status'] = 'witnessed_scoped'


def add_logged_selection(rows):
    by_id = {row['id']: row for row in rows}
    suite = {row['id']: row for row in read(LOGGED_SUITE)['cases']}
    for entry in read(LOGGED_REPORT)['rows']:
        for item in entry['bindings'].values():
            if binding(item['path'])['sha256'] != item['sha256']:
                raise ValueError('Logged strategy raw binding differs')
        source = read(entry['bindings']['source']['path']); native = read(entry['bindings']['native']['path'])
        definition = suite[entry['id']]
        request = 'tests/fixtures/suites/missing-p1-p2-runtime/' + definition['request']
        if binding(request)['sha256'] != definition['requestSha256'] or source['requestSha256'] != definition['requestSha256']:
            raise ValueError('Logged strategy request differs')
        for family, selected in [('CycleBreakingStrategy', entry['p1']), ('LayeringStrategy', entry['p2'])]:
            row = by_id['factory:' + family + ':' + selected]
            if source.get('outcome') != 'returned' or native.get('outcome') != 'returned':
                row.setdefault('observedSourceErrors', []).append({'id': entry['id'],
                    'reference': binding(entry['bindings']['source']['path']), 'native': binding(entry['bindings']['native']['path']),
                    'sourceError': source.get('error'), 'nativeError': native.get('error'),
                    'scope': 'Logging-enabled call threw before returned task tree; no normal branch execution inferred.'})
                continue
            expected = PHASE_TASKS[(family, selected)]
            found = None
            for _, class_names, children in contexts(source):
                if row['className'] in class_names:
                    found = next(((path, task) for path, task in children if task == expected), None)
                    if found:
                        break
            if not found or pointer(native, found[0] + '/name') != expected:
                raise ValueError('Logged actual selected task is absent or differs')
            if not any(row['className'] in class_names for _, class_names, _ in contexts(native)):
                raise ValueError('Native configured class is absent')
            row['witnesses'].append({'id': entry['id'], 'kind': 'actual-task', 'identityBasis': 'configured-class-and-task',
                'request': binding(request), 'reference': binding(entry['bindings']['source']['path']),
                'native': binding(entry['bindings']['native']['path']), 'referencePointer': found[0] + '/name',
                'nativePointer': found[0] + '/name', 'expected': expected, 'actual': expected, 'passed': True,
                'scope': 'New authorized logged public call: actual configured Source/native class and named task, not input-tag inference. No additional math claim.'})
            row['actualTaskCaseCount'] += 1
            row['status'] = 'witnessed_scoped'


def add_effects(rows):
    index = {row['id']: row for row in rows}
    def enum_rows(request, option):
        short = 'elk.' + option.removeprefix('org.eclipse.elk.')
        values = {options[key] for _, obj in walk(request.get('graph', {}))
                  if isinstance((options := obj.get('layoutOptions')), dict)
                  for key in (option, short) if key in options and type(options[key]) is str}
        selected = [index.get('option:' + option + ':' + value) for value in values]
        return [row for row in selected if row is not None] if len(values) == 1 else []
    for filename in EFFECT_REPORTS:
        path = 'test-runs/full-native-closure/A/' + filename
        report = json.loads(option_blob(path))
        cases = {row['id']: row for row in report['rows']}
        for entry in report['rows']:
            if entry.get('comparison', {}).get('passed') is not True:
                continue
            for assertion_index, assertion in enumerate(entry.get('assertions', [])):
                effect = assertion.get('effectTest', {})
                if assertion.get('passed') is not True or effect.get('passed') is not True or effect.get('kind') != 'changed':
                    continue
                option = assertion['option']
                request_binding, request = option_binding(entry['request'])
                possible = enum_rows(request, option)
                if not possible:
                    continue
                ref_binding, reference = option_binding(entry['reference']); native_binding, native = option_binding(entry['native'])
                baseline = cases[entry['baseline']]
                before_request_binding, before_request = option_binding(baseline['request'])
                before_ref_binding, before_ref = option_binding(baseline['reference']); before_native_binding, before_native = option_binding(baseline['native'])
                paths = assertion['referencePointers']
                scalar = 'pointer' in effect
                def project(data):
                    values = [pointer(data, p) for p in paths]
                    return values[0] if scalar else values
                expected, actual, source_before, native_before = map(project, (reference, native, before_ref, before_native))
                verify_causal_values(expected, actual, source_before, native_before, assertion)
                targets = [(row, 'variant') for row in possible]
                targets += [(row, 'baseline') for row in enum_rows(before_request, option) if row not in possible]
                for row, role in targets:
                    row['witnesses'].append({'id': entry['id'], 'kind': 'causal-geometry',
                        'report': {'path': path, 'sha256': sha(option_blob(path)), 'archive': OPTIONS_ARCHIVE.relative_to(ROOT).as_posix(), 'member': path},
                        'assertionPointer': '/rows/' + str(report['rows'].index(entry)) + '/assertions/' + str(assertion_index),
                        'request': request_binding, 'reference': ref_binding, 'native': native_binding,
                        'baselineRequest': before_request_binding, 'causalPairRoleForThisEnum': role,
                        'baselineReference': before_ref_binding, 'baselineNative': before_native_binding,
                        'valuePointers': paths, 'projection': 'scalar' if scalar else 'ordered-list',
                        'sourceBeforeSha256': sha(json.dumps(source_before, sort_keys=True).encode()),
                        'expected': expected, 'actual': actual, 'passed': True,
                        'scope': 'Explicit baseline or variant value participates in this verified causal public pair; a baseline no-op selection is not an executed mathematics claim.'})
                    row['status'] = 'witnessed_scoped'


def add_named_strategies(rows, cases):
    patterns = {
        'org.eclipse.elk.layered.edgeLabels.sideSelection': lambda value: 'Label side selection (' + value + ')',
        'org.eclipse.elk.layered.considerModelOrder.strategy': lambda value: 'Sort By Input Model ' + value,
        'org.eclipse.elk.layered.crossingMinimization.greedySwitch.type': lambda value: 'Minimize Crossings ' + value + '_GREEDY_SWITCH',
    }
    for row in rows:
        if row['optionId'] not in patterns:
            continue
        expected = patterns[row['optionId']](row['variant'])
        for case in cases:
            ref = read(case['reference']['path']); native = read(case['native']['path'])
            observed = next(((path, obj) for path, obj in walk(ref.get('result', {}).get('logging', {}), '/result/logging')
                             if obj.get('name') == expected), None)
            if observed and pointer(native, observed[0] + '/name') == expected:
                row['witnesses'].append({'id': case['id'], 'kind': 'actual-task-strategy-named',
                    'request': case['request'], 'reference': case['reference'], 'native': case['native'],
                    'referencePointer': observed[0] + '/name', 'nativePointer': observed[0] + '/name',
                    'expected': expected, 'actual': expected, 'passed': True,
                    'scope': 'Actual Source task explicitly names this strategy; not inferred from the input option.'})
                row['status'] = 'witnessed_scoped'
                break


def literal(path, name):
    tree = ast.parse((ROOT / path).read_text('utf-8'))
    return next(ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == name for t in n.targets))


def walk(value, pointer=''):
    if isinstance(value, dict):
        yield pointer, value
        for key, child in value.items():
            yield from walk(child, pointer + '/' + str(key).replace('~', '~0').replace('/', '~1'))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, pointer + '/' + str(index))


def contexts(observation):
    result = []
    for pointer, obj in walk(observation.get('result', {}).get('logging', {}), '/result/logging'):
        logs = obj.get('logs', [])
        classes = [s.split(': ', 1)[1] for s in logs
                   if isinstance(s, str) and re.match(r'^\s+Slot \d+: ', s)]
        if classes or obj.get('children'):
            children = [(pointer + '/children/' + str(i), c.get('name'))
                        for i, c in enumerate(obj.get('children', [])) if isinstance(c, dict)]
            result.append((pointer, classes, children))
    return result


def implementation_index():
    symbols = {}
    for path in sorted(LAYERED.glob('*.py')):
        relative = path.relative_to(ROOT).as_posix()
        for node in ast.parse(path.read_text('utf-8')).body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                symbols.setdefault(node.name, []).append(dict(binding(relative), symbol=node.name, line=node.lineno))
    factory = ast.parse((LAYERED / 'phase_factories.py').read_text('utf-8'))
    bodies = {}
    for node in ast.walk(factory):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '_function_processor':
            if len(node.args) >= 3 and all(isinstance(a, ast.Constant) for a in node.args[:3]):
                name, module, symbol = (a.value for a in node.args[:3])
                bodies[name] = [x for x in symbols.get(symbol, []) if x['path'].endswith('/' + module + '.py')]
    bodies['OrthogonalEdgeRouter'] = symbols['orthogonal_edge_router']
    return symbols, bodies


def saved_cases():
    summary = read(SUMMARY)
    suite_path = 'tests/fixtures/suites/full-native-layered/cases.json'
    definitions = {row['id']: row for row in read(suite_path)['cases']}
    out = []
    for row in summary['cases']:
        if not row.get('matched'):
            continue
        base = 'test-runs/20261104-HOST-19/A/' + row['batch'] + '/' + row['id'] + '/'
        paths = {key: base + filename for key, filename in
                 [('reference', 'reference.json'), ('native', 'candidate.json'), ('comparison', 'comparison.json')]}
        for key, digest_key in [('reference', 'referenceSha256'), ('native', 'candidateSha256'), ('comparison', 'comparisonSha256')]:
            if sha(blob(paths[key])) != row[digest_key]:
                raise ValueError('Changed historical evidence: ' + paths[key])
        ref, native = read(paths['reference']), read(paths['native'])
        if ref.get('outcome') != 'returned' or native.get('outcome') != 'returned':
            raise ValueError('Normal-case summary disagrees with raw observations')
        request = 'tests/fixtures/suites/full-native-layered/' + definitions[row['id']]['request']
        if binding(request)['sha256'] != row['requestSha256']:
            raise ValueError('Request differs from saved execution: ' + row['id'])
        out.append({'id': row['id'], 'request': binding(request), 'reference': binding(paths['reference']),
                    'native': binding(paths['native']), 'comparison': binding(paths['comparison']),
                    'requestSha256': row['requestSha256'], 'referenceContexts': contexts(ref),
                    'nativeContexts': contexts(native), 'wholeOutputMatched': True})
    return out


def match_task(name, pattern):
    return name == pattern or (pattern.endswith((' ', '(')) and isinstance(name, str) and name.startswith(pattern))


def build():
    classes = literal('src/pyelk/algorithms/layered/processor_class_names.py', 'FACTORY_PROCESSOR_CLASS_NAMES')
    if len(classes) != 90:
        raise ValueError('Factory denominator changed; review the finite contract')
    packet = read(SOURCE)
    for span in packet['factorySpans'] + packet['classDeclarations']:
        raw = base64.b64decode(span['sourceBytesBase64'], validate=True)
        if sha(raw) != span['sha256']:
            raise ValueError('Fixed Source byte span no longer matches: ' + span.get('symbol', span.get('constructor', '?')))
    original = packet['actualObservation']
    if binding(original['path'])['sha256'] != original['sha256']:
        raise ValueError('Changed actual factory observation')
    source_rows = read(original['path'])['observation']['rows']
    if {(r['family'], r['name']): r['className'] for r in source_rows} != classes:
        raise ValueError('Current factory identities disagree with fixed Source observation')
    decls = {x['className']: x for x in packet['classDeclarations']}
    symbols, bodies = implementation_index()
    cases = saved_cases()
    rows = []
    for (family, name), fq in sorted(classes.items()):
        ctor = fq.rsplit('.', 1)[1]
        implementation = bodies.get(ctor) or symbols.get(ctor, [])
        if ctor == 'GraphTransformer':
            implementation = [x for x in implementation if '/directions_general.py' in x['path']]
        if not implementation:
            raise ValueError('Missing implementation anchor: ' + ctor)
        pattern = TASKS.get(name) if family == 'IntermediateProcessorStrategy' else PHASE_TASKS.get((family, name))
        observed, configured = [], []
        for case in cases:
            for context, class_names, children in case['referenceContexts']:
                is_configured = fq in class_names
                # Hierarchical scheduler emits actual task children without a
                # flat slot inventory. A globally unique literal task remains
                # an execution observation; ambiguous shared tasks need slots.
                uses = sum(p == pattern for p in TASKS.values()) + sum(p == pattern for p in PHASE_TASKS.values()) if pattern else 0
                if not is_configured and uses != 1:
                    continue
                candidates = [x for x in case['nativeContexts'] if x[0] == context
                              and (not is_configured or fq in x[1])]
                if not candidates:
                    continue
                entry = {key: case[key] for key in ('id', 'request', 'reference', 'native', 'comparison', 'requestSha256')}
                entry.update(kind='configured-only', contextPointer=context, className=fq)
                if is_configured:
                    configured.append(entry)
                if not pattern:
                    continue
                ref_tasks = [(p, task) for p, task in children if match_task(task, pattern)]
                native_tasks = candidates[0][2]
                # Where two processors have the same monitor name, require at
                # least as many actual tasks as configured factories bearing it.
                same_task_factories = {other_fq for (other_family, other_name), other_fq in classes.items()
                                       if other_family == 'IntermediateProcessorStrategy'
                                       and TASKS.get(other_name) == pattern and other_fq in class_names}
                if len(ref_tasks) < len(same_task_factories):
                    continue
                if len(same_task_factories) > 1:
                    # Source scheduler processes the configured slot order.
                    # Bind pre/post (or the two margin processors) to separate
                    # actual task occurrences, not the same first occurrence.
                    ordered = [item for item in class_names if item in same_task_factories]
                    if len(ordered) != len(same_task_factories):
                        continue
                    ref_tasks = [ref_tasks[ordered.index(fq)]]
                for pointer, task in ref_tasks:
                    if (pointer, task) not in native_tasks:
                        continue
                    observed.append(dict(entry, kind='actual-task', identityBasis='configured-class-and-task' if is_configured else 'unique-literal-task', referencePointer=pointer + '/name',
                                         nativePointer=pointer + '/name', expected=task, actual=task, passed=True))
                    break
        row = {'id': 'factory:' + family + ':' + name, 'family': family, 'variant': name,
               'className': fq, 'optionId': FAMILY_OPTIONS.get(family),
               'sourceEvidence': [dict(binding(SOURCE), locator='classDeclarations:' + ctor,
                                      startLine=decls[fq]['startLine'], endLine=decls[fq]['endLine'],
                                      scope='fixed-worker factory/class identity; not a claim that every body branch ran'),
                                  dict(binding(original['path']), locator='/observation/rows/' + str(next(i for i, r in enumerate(source_rows) if r['family'] == family and r['name'] == name)))],
               'implementation': implementation, 'taskPattern': pattern,
               'witnesses': observed[:3], 'actualTaskCaseCount': len({x['id'] for x in observed}),
               'configuredCases': configured[:3], 'configuredCaseCount': len({x['id'] for x in configured}),
               'status': 'witnessed_scoped' if observed else 'configured_only' if configured else 'no_runtime_witness',
               'limitations': ['Task entry and matched whole output establish a finite consumer witness, not all internal conditions.']}
        if family == 'EdgeRouting' and name in ('UNDEFINED', 'ORTHOGONAL'):
            row['status'] = 'body_witnessed_factory_alias_unresolved' if observed else row['status']
            row['limitations'].append('Both factories share a body. Logs identify the body, not which alias factory was used.')
        if name in ('HIGH_DEGREE_NODE_LAYER_PROCESSOR', 'FINAL_SPLINE_BENDPOINTS_CALCULATOR'):
            row['limitations'].append('Body does not name its monitor; logging-enabled stock Source can fail during log export. No invented task witness.')
        if 'LABEL_MANAGEMENT_PROCESSOR' in name:
            row['limitations'].append('Selection requires the actual labels.labelManager property; nonnull raw managers fail the compiled Source cast. Null-only leaf controls are not successful public selection.')
        rows.append(row)
    add_prepared(rows)
    add_logged_selection(rows)
    for row in rows:
        row['objectStateWitnessCount'] = sum(w['kind'] == 'object-state-assertion' for w in row['witnesses'])
        if row['status'] != 'no_runtime_witness':
            continue
        if 'LABEL_MANAGEMENT_PROCESSOR' in row['variant']:
            category = 'upstream-nonnull-raw-manager-unavailable'
            action = 'Retain compiled Source null-only cast boundary; no successful nonnull raw callback can be manufactured.'
        elif row.get('observedSourceErrors'):
            category = 'normal-unlogged-public-return-plus-logged-upstream-error'
            action = 'If a direct body witness is required, one actual owner.process state or function-entry observation is enough; do not replay the 81 strategy matrix.'
        elif row['variant'] in ('HIGH_DEGREE_NODE_LAYER_PROCESSOR', 'ALTERNATING_LAYER_UNZIPPER'):
            category = 'normal-unlogged-output-exists-body-not-isolated'
            action = 'Reuse saved Source output/effects first; only a direct body-state observation remains if those cannot isolate the consumer.'
        else:
            category = 'no-current-direct-body-observation'
            action = 'One applicable actual object-state or public function-entry witness; no known missing implementation inferred.'
        row['remainingClassification'] = category
        row['minimalRemainingWitness'] = action
    counts = dict(Counter(x['status'] for x in rows))
    supplemental = []
    # Finite predeclared selectors only. A value mention is an occurrence, not
    # proof of selection/effect. Existing option-role ledger remains separate.
    declarations = literal('src/pyelk/options/_generic_data.py', 'SCALAR_DECLARATIONS')
    excluded = set(FAMILY_OPTIONS.values())
    for option, kind, default, targets, members in declarations:
        if option in excluded or not members:
            continue
        if option.startswith('org.eclipse.elk.layered.') or option in ('org.eclipse.elk.direction', 'org.eclipse.elk.portConstraints', 'org.eclipse.elk.port.side'):
            for member in members:
                supplemental.append({'id': 'option:' + option + ':' + member, 'family': 'declared-option-enum',
                                     'optionId': option, 'variant': member, 'status': 'not_mapped_in_core_first_version',
                                     'sourceEvidence': [dict(binding('src/pyelk/options/_generic_data.py'), locator=option)],
                                     'witnesses': [], 'limitations': ['Explicit finite enum denominator; requires variant-specific accounting, not input-occurrence inference.']})
    add_effects(supplemental)
    add_named_strategies(supplemental, cases)
    return {'schema': 'pyelk-declared-branch-matrix/v1', 'scope': 'finite-factory-and-existing-evidence-increment',
            'workerSha256': packet['workerSha256'], 'productExecutionCount': 0, 'sourceExecutionCount': 0,
            'denominator': {'coreFactories': 90, 'intermediate': 59, 'P1': 9, 'P2': 9, 'P3': 4, 'P4': 5, 'P5Factories': 4,
                            'P5DistinctBodies': 3, 'supplementalEnumRows': len(supplemental)},
            'summary': {'coreStatuses': counts, 'normalSavedCasesRead': len(cases),
                        'supplementalStatuses': dict(Counter(x['status'] for x in supplemental)),
                        'unwitnessedCoreIds': [r['id'] for r in rows if r['status'] in ('configured_only', 'no_runtime_witness')]},
            'inputs': [binding(SUMMARY), binding(SOURCE), binding('src/pyelk/algorithms/layered/phase_factories.py'),
                       binding('tests/fixtures/suites/full-native-layered/cases.json'),
                       binding(P1_P2_MAP), binding(OPTIONS_MANIFEST.relative_to(ROOT).as_posix()),
                       binding(LOGGED_REPORT), binding(LOGGED_SUITE),
                       binding(MANIFEST.relative_to(ROOT).as_posix())],
            'interpretation': ['No missing implementation is inferred from a missing witness.',
                               'Literal Source/native tasks or original owner.process with strict raw state projections elevate core rows; unique hierarchy tasks need no flat slot log.',
                               'Configured slots, enum membership and class names alone never elevate runtime witness status.',
                               'Historical observations retain their original engine/version and source bindings; current anchors do not rebind old executions.',
                               'Supplemental causal rows require successful raw paired pointer projections and a genuine before/after change; a passed report flag alone is insufficient.',
                               'Supplemental rows are a separate finite accounting backlog, not claims of missing code or a demand for all option combinations.'],
            'rows': rows, 'supplementalRows': supplemental}


def markdown(data):
    lines = ['# Layered 声明分支证据矩阵', '',
             '首版固定 90 个工厂：59 个中间处理器、P1/P2 各 9、P3 4、P4 5、P5 4。P5 的 UNDEFINED 与 ORTHOGONAL 共用同一数学实现。', '',
             '本次仅离线读取既存记录；没有运行布局、Source 或旧测试。任务名称必须同时出现在原版与候选的同一日志上下文：平面流程结合对应工厂类，层级流程只接受全局唯一任务名；共享任务按真实配置槽顺序绑定不同事件。配置槽、输入提及和类存在各自不能证明运行分支。', '',
             '## 核心计数', '', '| 状态 | 行数 |', '|---|---:|']
    lines += ['| ' + k + ' | ' + str(v) + ' |' for k, v in data['summary']['coreStatuses'].items()]
    lines += ['', '## 核心逐行', '', '| 工厂 | 状态 | 真任务见证数 | 首个案例 | 实现 |', '|---|---|---:|---|---|']
    for row in data['rows']:
        first = row['witnesses'][0]['id'] if row['witnesses'] else '—'
        impl = row['implementation'][0]
        lines.append('| ' + row['family'] + '.' + row['variant'] + ' | ' + row['status'] + ' | ' + str(row['actualTaskCaseCount']) + ' | ' + first + ' | ' + impl['path'].split('/')[-1] + ':' + str(impl['line']) + ' |')
    lines += ['', '## 解释与后续', '',
              '未找到任务见证不等于未实现。本版扫描既有 72 例中的 66 个正常返回匹配结果，合入 4 个 P1/P2 实际 owner.process 对象见证、2 个 Spline→Final 准备图及 ONE_SIDED 真阶段状态；另合入新授权 7 个日志调用中的 5 个正常对，具名任务证明 8 个策略行。另两对 Source/native 同为 NPE，无结果树，不升级其中 4 个策略。历史执行保其原模块 SHA，不重绑当前模块。另 16 条 P1/P2 公开返回关联单列，不凭输入策略升级。', '',
              '`body_witnessed_factory_alias_unresolved` 只证明共享正交路由体，不声称区分两个工厂别名。无任务名的 FinalSpline / HighDegree 需要已有对象或因果输出证据；不为它们补造日志。两个 LabelManagement 工厂的实际非空 raw-manager 选择受原版 cast 限制，需区分 API 可构造性与回调数学。', '',
              '附加枚举层逐项保留有限分母：' + str(data['summary']['supplementalStatuses'].get('witnessed_scoped', 0)) + ' 行已有真实因果几何或明确命名任务见证，其余仍未映射。不能用同一通用任务加输入提及替代内部分支证据；不要求数值无限取值或所有选项组合。JSON 保留完整路径、SHA、JSONPointer、静态锚及限制。', '',
              '## 附加枚举有限缺项', '', '| 选项 | 已证值 | 尚无本表见证的值 |', '|---|---|---|']
    grouped = {}
    for row in data['supplementalRows']:
        grouped.setdefault(row['optionId'], []).append(row)
    for option, rows in grouped.items():
        lines.append('| ' + option + ' | ' + ', '.join(r['variant'] for r in rows if r['status'] == 'witnessed_scoped') + ' | ' + ', '.join(r['variant'] for r in rows if r['status'] != 'witnessed_scoped') + ' |')
    lines += ['',
              '## 核心尚无直接见证', '', '| 工厂 | 明确分类 | 最小后续动作 |', '|---|---|---|']
    for row in data['rows']:
        if row['status'] == 'no_runtime_witness':
            lines.append('| ' + row['family'] + '.' + row['variant'] + ' | ' + row['remainingClassification'] + ' | ' + row['minimalRemainingWitness'] + ' |')
    lines += ['',
              '## 干净检出复核', '',
              '`python scripts/iteration/declared_branch_matrix.py --check` 仅读取版本化源码、请求和 `references/full-native-closure/branches.zip` 的精确成员；SHA 与清单逐个核对，不回退本机 ignored 路径。原始观察字节不改写。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--check', action='store_true', help='Recompute saved accounting and require exact tracked JSON/Markdown')
    parser.add_argument('--seal-archive', action='store_true', help='One-time exact-byte archive creation from existing captures')
    parser.add_argument('--extend-archive', action='store_true', help='Package the explicit saved P1/P2 and spline evidence increment')
    args = parser.parse_args()
    if args.seal_archive:
        seal_archive()
    if args.extend_archive:
        extend_archive()
    data = build()
    json_text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    md_text = markdown(data)
    if args.check:
        if args.out.read_text('utf-8') != json_text or args.out.with_suffix('.md').read_text('utf-8') != md_text:
            raise ValueError('Declared branch matrix differs from saved-data recomputation')
        print(json.dumps({'passed': True, **data['summary']}, ensure_ascii=False))
        return
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json_text, 'utf-8')
    args.out.with_suffix('.md').write_text(md_text, 'utf-8')
    print(json.dumps(data['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
