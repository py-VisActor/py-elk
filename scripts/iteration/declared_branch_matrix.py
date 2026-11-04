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
OLD_ENUM_MAP = 'test-runs/full-native-closure/A/old-enum-map-01/handoff.json'
CONSUMER_LINKS = 'test-runs/full-native-closure/A/old-enum-map-01/consumer-links.json'
STAGED_CLASSIFICATIONS = 'test-runs/full-native-closure/A/old-enum-map-01/staging.json'
FIVE_OWNERS = 'test-runs/full-native-closure/B/missing-owner-dtos-02/handoff.json'
UNZIP_EQUAL = 'test-runs/full-native-closure/B/unzip-equal-owner-01/handoff.json'
EXISTING_ENUM_MAP = 'test-runs/full-native-closure/V/layered-enum-existing-01/findings.json'
ORIENTATION_MAP = 'test-runs/full-native-closure/B/orientation-helpers-01/handoff.json'
CONSUMER_ENUM_MAP = 'test-runs/full-native-closure/A/enum-consumers-01/handoff.json'
NETWORK_SIMPLEX_MAP = 'test-runs/full-native-closure/B/network-simplex-consumer-01/handoff.json'
GREEDY_CONFIG_MAP = 'test-runs/full-native-closure/B/greedy-switch-config-01/handoff.json'
SPLINE_SOFT_MAP = 'test-runs/full-native-closure/B/spline-soft-consumer-01/handoff.json'
POST_WRAPPING_MAP = 'test-runs/full-native-closure/B/postcompaction-wrapping-closure-01/handoff.json'
COMPONENT_GROUP_MAP = 'test-runs/full-native-closure/V/components-order-family-01/handoff.json'
PROMOTION_MAP = 'test-runs/full-native-closure/B/node-promotion-owner-01/handoff.json'
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
    increments = (OLD_ENUM_MAP, CONSUMER_LINKS, STAGED_CLASSIFICATIONS, FIVE_OWNERS, UNZIP_EQUAL, EXISTING_ENUM_MAP, PROMOTION_MAP, ORIENTATION_MAP, CONSUMER_ENUM_MAP, NETWORK_SIMPLEX_MAP, GREEDY_CONFIG_MAP, SPLINE_SOFT_MAP, POST_WRAPPING_MAP, COMPONENT_GROUP_MAP)
    paths.update(increments)
    for filename in increments:
        document = json.loads((ROOT / filename).read_text('utf-8'))
        # Only explicit repository-relative saved evidence bindings. Runtime
        # absolute paths inside original receipts are never followed or searched.
        for _, obj in walk(document):
            if isinstance(obj.get('path'), str) and isinstance(obj.get('sha256'), str):
                path = obj['path']
                if path.startswith('test-runs/') and 'archive' not in obj:
                    paths.add(path)
            if isinstance(obj.get('filesSha256'), dict):
                paths.update(path for path in obj['filesSha256'] if path.startswith('test-runs/'))
    staged = json.loads((ROOT / STAGED_CLASSIFICATIONS).read_text('utf-8'))
    for key in ('sourcePeerReceipt', 'codePeerReceipt'):
        receipt = json.loads((ROOT / staged['managerBoundary'][key]['path']).read_text('utf-8'))
        paths.update(path for path in receipt['filesSha256'] if path.startswith('test-runs/'))
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
    preserved = ROOT / 'test-runs/full-native-closure/A/declared-branches-03'
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


def checked_binding(item):
    actual = binding(item['path'])
    if actual['sha256'] != item['sha256']:
        raise ValueError('Saved evidence binding changed: ' + item['path'])
    return actual


def verify_equal_fallback(witness, source, native):
    conditions = pointer(source, witness['sourceConditionPointer'])
    native_conditions = pointer(native, witness['nativeConditionPointer'])
    expected, actual = pointer(source, witness['sourceReturnPointer']), pointer(native, witness['nativeReturnPointer'])
    fallback = pointer(source, witness['sourceFallbackObservedPointer'])
    if (not equal(conditions, native_conditions)
            or type(conditions.get('incomingCount')) not in (int, float) or conditions['incomingCount'] != 0
            or type(conditions.get('portCount')) not in (int, float) or conditions['portCount'] != 1
            or conditions.get('strategy') != 'EQUAL' or type(expected) not in (int, float)
            or expected != 0 or not equal(expected, actual)
            or fallback != {'name': 'EQUAL', 'ordinal': 2}
            or pointer(source, witness['sourceObserverDelegatesOriginalPointer']) is not True):
        raise ValueError('EQUAL fallback condition/event/result is not witnessed')
    return conditions, expected, actual


def verify_alias_source_row(actual, family, variant):
    if (actual.get('family') != family or actual.get('name') != variant
            or actual.get('className') != 'org.eclipse.elk.alg.layered.p5edges.OrthogonalEdgeRouter'):
        raise ValueError('Source factory alias does not identify this shared orthogonal factory')


def verify_manager_controls(controls):
    by_case = {row['id']: row for row in controls['cases']}
    if by_case['absent']['returned'] is not True or by_case['absent']['done'] is not True:
        raise ValueError('Manager null/default contract failed')
    if any(by_case[key]['returned'] is not False or by_case[key]['done'] is not False for key in ('false', 'zero', 'emptyString', 'emptyList')):
        raise ValueError('Manager nonnull guard boundary failed')


def add_current_increment(rows, supplemental):
    core = {row['id']: row for row in rows}
    enums = {row['id']: row for row in supplemental}
    owners = read(FIVE_OWNERS)
    owner_bindings = {key: checked_binding(owners[key]) for key in ('request', 'sourceRaw', 'sourceProbe', 'nativeChecker')}
    source = read(owners['sourceRaw']['path'])
    if source['probeSha256'] != owners['sourceProbe']['sha256'] or source['requestSha256'] != owners['request']['sha256']:
        raise ValueError('Five-owner Source acquisition does not bind request/probe')
    for witness in owners['witnesses']:
        native_binding = checked_binding(witness['nativeReport'])
        native = read(witness['nativeReport']['path'])
        expected, actual = pointer(source, witness['sourcePointer']), pointer(native, witness['nativePointer'])
        if not equal(expected, actual):
            raise ValueError('Actual owner.process state differs: ' + witness['id'])
        before, after = pointer(source, witness['sourceBeforePointer']), pointer(source, witness['sourceAfterPointer'])
        if equal(before, after):
            raise ValueError('Missing nontrivial owner state transition: ' + witness['id'])
        row = core[witness['id']]
        row['witnesses'].append({'id': witness['id'] + ':direct-owner-state', 'kind': 'object-state-assertion',
            'evidenceMap': binding(FIVE_OWNERS), 'bindings': dict(owner_bindings, native=native_binding),
            'referencePointer': witness['sourcePointer'], 'nativePointer': witness['nativePointer'],
            'strictStateEqual': True, 'nontrivialBeforeAfterChange': True,
            'sourceFunction': witness['sourceFunction'], 'nativeFunction': witness['nativeFunction'],
            'scope': 'Actual original and native owner.process on prepared objects, with complete before/after/monitor state. No public whole caller or extra branch claim.'})
        row['status'] = 'witnessed_scoped'
        row.pop('remainingClassification', None); row.pop('minimalRemainingWitness', None)

    # Original observations are authoritative. The old handoff stores both
    # pointer locations and exact selected DTOs, all independently rechecked.
    old = read(OLD_ENUM_MAP)
    for path, digest in old['filesSha256'].items():
        if binding(path)['sha256'] != digest:
            raise ValueError('Old enum evidence dependency changed: ' + path)
    for witness in old['rows']:
        refs = {key: checked_binding(value) for key, value in witness['bindings'].items()}
        ref, native = read(witness['bindings']['reference']['path']), read(witness['bindings']['native']['path'])
        expected, actual = pointer(ref, witness['sourcePointer']), pointer(native, witness['nativePointer'])
        if not equal(expected, actual) or not equal(expected, witness['expected']) or not equal(actual, witness['actual']):
            raise ValueError('Old enum actual saved state differs: ' + witness['id'])
        if ref.get('probeSha256') and ref['probeSha256'] != refs['sourceProbe']['sha256']:
            raise ValueError('Old enum Source probe differs')
        if ref.get('requestSha256') and 'request' in refs and ref['requestSha256'] != refs['request']['sha256']:
            raise ValueError('Old enum Source request differs')
        row = enums[witness['id']]
        row['witnesses'].append({'id': witness['id'] + ':saved-object-state', 'kind': 'object-state-assertion',
            'evidenceMap': binding(OLD_ENUM_MAP), 'bindings': refs,
            'sourcePointer': witness['sourcePointer'], 'nativePointer': witness['nativePointer'],
            'sourceCall': witness['sourceCall'], 'expected': expected, 'actual': actual,
            'strictStateEqual': True, 'historicalRuntimeReboundToCurrentModule': False,
            'scope': witness['scope']})
        row['status'] = 'witnessed_scoped'

    final = read(UNZIP_EQUAL)
    final_bindings = {key: checked_binding(value) for key, value in final['bindings'].items()}
    ref, native = read(final['bindings']['sourceRaw']['path']), read(final['bindings']['nativeRaw']['path'])
    if ref['probeSha256'] != final['bindings']['sourceProbe']['sha256'] or ref['requestSha256'] != final['bindings']['request']['sha256']:
        raise ValueError('Unzip/EQUAL Source acquisition binding differs')
    for witness in final['witnesses']:
        if witness['id'].startswith('factory:'):
            pairs = [(witness['sourceBeforePointer'], witness['nativeBeforePointer']),
                     (witness['sourceAfterPointer'], witness['nativeAfterPointer'])]
            assertions = []
            for ref_pointer, native_pointer in pairs:
                expected, actual = pointer(ref, ref_pointer), pointer(native, native_pointer)
                if not equal(expected, actual):
                    raise ValueError('Actual unzip state differs')
                assertions.append({'sourcePointer': ref_pointer, 'nativePointer': native_pointer,
                                   'expected': expected, 'actual': actual, 'passed': True})
            if equal(assertions[0]['expected'], assertions[1]['expected']):
                raise ValueError('Unzip has no layer state change')
            row = core[witness['id']]
            row['witnesses'].append({'id': 'unzip-real-layer-state', 'kind': 'object-state-assertion',
                'evidenceMap': binding(UNZIP_EQUAL), 'bindings': final_bindings, 'assertions': assertions,
                'monitorIgnoredBySource': True, 'sourceFunction': witness['sourceFunction'],
                'scope': 'Actual unzip process transforms one six-node layer into alternating three-node layers. No monitor task invented; prepared objects, not public layout.'})
            row['status'] = 'witnessed_scoped'
        else:
            conditions, expected, actual = verify_equal_fallback(witness, ref, native)
            row = enums[witness['id']]
            row['witnesses'].append({'id': 'equal-actual-no-incoming-fallback', 'kind': 'direct-helper-condition-and-result',
                'evidenceMap': binding(UNZIP_EQUAL), 'bindings': final_bindings,
                'sourceConditionPointer': witness['sourceConditionPointer'], 'nativeConditionPointer': witness['nativeConditionPointer'],
                'sourceReturnPointer': witness['sourceReturnPointer'], 'nativeReturnPointer': witness['nativeReturnPointer'],
                'sourceFallbackObservedPointer': witness['sourceFallbackObservedPointer'],
                'conditions': conditions, 'expected': expected, 'actual': actual, 'passed': True,
                'scope': 'Actual zero-incoming helper fallback delegates original returnValue(EQUAL), returning0. Role-specific names and Source-only observer are not claimed raw-identical.'})
            row['status'] = 'witnessed_scoped'

    links = read(CONSUMER_LINKS)
    high = core['factory:IntermediateProcessorStrategy:HIGH_DEGREE_NODE_LAYER_PROCESSOR']
    for entry in links['highDegree']:
        document = json.loads(option_blob(entry['report']['path']))
        assertion = pointer(document, entry['assertionPointer'])
        values = {}
        refs = {}
        for key in ('reference', 'native', 'baselineReference', 'baselineNative'):
            refs[key], raw = option_binding(entry[key])
            projected = [pointer(raw, p) for p in entry['pointers']]
            values[key] = projected[0] if 'pointer' in assertion['effectTest'] else projected
        verify_causal_values(values['reference'], values['native'], values['baselineReference'], values['baselineNative'], assertion)
        high['witnesses'].append({'id': entry['id'], 'kind': 'causal-consumer-chain', 'evidenceMap': binding(CONSUMER_LINKS),
            'bindings': refs, 'report': entry['report'], 'assertionPointer': entry['assertionPointer'],
            'expected': values['reference'], 'actual': values['native'], 'passed': True,
            'noDirectTrace': True, 'scope': entry['scope']})
    if not links['highDegree']:
        raise ValueError('HighDegree has no actual causal-output witness')
    high['status'] = 'causal_consumer_chain_scoped'; high['noDirectTrace'] = True

    staged = read(STAGED_CLASSIFICATIONS)
    source_rows = read('tests/fixtures/suites/next-native/layered-processor-classes-oracle.json')['observation']['rows']
    for alias in staged['aliasClassifications']:
        checked_binding(alias['reference'])
        actual = pointer({'observation': {'rows': source_rows}}, alias['referencePointer'])
        row = core[alias['id']]
        verify_alias_source_row(actual, row['family'], row['variant'])
        row['status'] = 'shared_body_alias_verified'
        row['aliasEvidence'] = alias
        row['limitations'] = [line for line in row['limitations'] if not line.startswith('Both factories share a body.')]
        row['limitations'].append('Actual Source factory construction verifies the shared-body alias; separate public alias selection is not asserted and no second routing mathematics exists.')
        row['independentMathematicsClaimed'] = False
        row['nativeJsonContractSatisfied'] = True
    manager = staged['managerBoundary']
    for key in ('sourcePeerReceipt', 'codePeerReceipt', 'actualNativeFalseyErrorControls'):
        checked_binding(manager[key])
    source_receipt = read(manager['sourcePeerReceipt']['path'])
    source_text = []
    for path, digest in source_receipt['filesSha256'].items():
        if not path.startswith('test-runs/'):
            continue
        if binding(path)['sha256'] != digest:
            raise ValueError('Manager fixed Source proposal differs')
        for _, span in walk(read(path)):
            if 'sourceBytesBase64' in span and 'sha256' in span:
                raw = base64.b64decode(span['sourceBytesBase64'], validate=True)
                if sha(raw) != span['sha256']:
                    raise ValueError('Manager fixed Source bytes differ')
                source_text.append(raw.decode('utf-8'))
    if 'throwClassCastExceptionUnlessNull' not in '\n'.join(source_text):
        raise ValueError('Compiled null-only manager cast is not present')
    controls = read(manager['actualNativeFalseyErrorControls']['path'])
    verify_manager_controls(controls)
    for row_id in manager['ids']:
        row = core[row_id]
        row['status'] = 'source_raw_unconstructible_boundary'
        row['normalRuntimeMathPass'] = False
        row['nativeJsonContractSatisfied'] = True
        row['nativeJsonContractScope'] = 'Default/null manager accepted; unsupported nonnull internal manager values rejected. No successful arbitrary manager callback feature.'
        row['boundaryEvidence'] = manager
        row['sourceRuntimeFailureClaimed'] = False
    for row in rows:
        row['objectStateWitnessCount'] = sum(w['kind'] == 'object-state-assertion' for w in row['witnesses'])
        if row['status'] != 'no_runtime_witness':
            row.pop('remainingClassification', None); row.pop('minimalRemainingWitness', None)


def add_existing_enum_scope(supplemental):
    by_id = {row['id']: row for row in supplemental}
    findings = read(EXISTING_ENUM_MAP)
    for entry in findings['rows']:
        refs = {key: checked_binding(entry[key]) for key in ('request', 'source', 'native', 'sourceProbe', 'nativeChecker') if key in entry}
        source, native = read(entry['source']['path']), read(entry['native']['path'])
        row = by_id[entry['id']]
        if entry['status'] in ('existing_direct_helper_witness', 'existing_actual_transformer_state_witness'):
            expected, actual = pointer(source, entry['sourcePointer']), pointer(native, entry['nativePointer'])
            if not equal(expected, actual):
                raise ValueError('Existing enum helper/transformer state differs')
            probe_digest = source.get('probeSha256')
            if probe_digest is None and entry['status'] == 'existing_direct_helper_witness':
                wrapper = read('tests/fixtures/suites/next-native/ports-helper-oracle.json')
                if wrapper['observationSha256'] != entry['source']['sha256']:
                    raise ValueError('Port primitive wrapper does not bind the saved Source bytes')
                probe_digest = wrapper['probeSha256']
            if probe_digest != entry['sourceProbe']['sha256'] or source.get('requestSha256') != entry['request']['sha256']:
                raise ValueError('Existing enum Source request/probe binding differs')
            if entry.get('requestPointer') and pointer(read(entry['request']['path']), entry['requestPointer']).get('direction') != row['variant']:
                raise ValueError('Direction helper did not receive this typed value')
            row['witnesses'].append({'id': entry['id'] + ':existing-helper-or-transformer', 'kind': 'object-state-assertion',
                'evidenceMap': binding(EXISTING_ENUM_MAP), 'bindings': refs,
                'sourcePointer': entry['sourcePointer'], 'nativePointer': entry['nativePointer'],
                'expected': expected, 'actual': actual, 'strictStateEqual': True,
                'graphDirectionResolutionClaimed': False, 'historicalRuntimeReboundToCurrentModule': False,
                'scope': entry['scope']})
            row['status'] = 'witnessed_scoped'
        elif entry['status'] == 'existing_actual_consumer_state_without_helper_return_trace':
            assertions = []
            for src_key, native_key in [('sourceBeforePointer', 'nativeBeforePointer'), ('sourceAfterPointer', 'nativeAfterPointer')]:
                expected, actual = pointer(source, entry[src_key]), pointer(native, entry[native_key])
                if not equal(expected, actual):
                    raise ValueError('Actual reference-point consumer state differs')
                assertions.append({'sourcePointer': entry[src_key], 'nativePointer': entry[native_key],
                                   'expected': expected, 'actual': actual, 'passed': True})
            if pointer(read(entry['request']['path']), entry['requestPointer']) != row['variant']:
                raise ValueError('Actual consumer did not receive this reference point')
            row['witnesses'].append({'id': entry['id'] + ':consumer-state', 'kind': 'consumer-state-without-helper-return-trace',
                'evidenceMap': binding(EXISTING_ENUM_MAP), 'bindings': refs, 'assertions': assertions,
                'independentReferencePointVectorWitness': False, 'causalAlternateValueComparison': False,
                'scope': entry['scope']})
            row['status'] = 'consumer_state_scoped'
        else:
            # A directly constructed ALTERNATING body does not prove that the
            # Source configuration selector read ALTERNATING instead of NONE.
            row['relatedBodyEvidence'] = {'evidenceMap': binding(EXISTING_ENUM_MAP), 'bindings': refs, 'scope': entry['scope']}
            row['enumConfigurationRouteClaimed'] = False


def promotion_projection(value):
    # Original recursion and native explicit frames expose different helper
    # invocation boundaries. Keep raw counts; compare all other actual state.
    projected = json.loads(json.dumps(value))
    projected['counts'].pop('promote', None)
    projected['counts'].pop('newLayeringModel', None)
    return projected


def add_promotion_scope(supplemental):
    by_id = {row['id']: row for row in supplemental}
    report = read(PROMOTION_MAP)
    common = {key: checked_binding(report[key]) for key in ('request', 'sourceProbe', 'nativeChecker', 'sourceRaw')}
    source = read(report['sourceRaw']['path'])
    if source['requestSha256'] != report['request']['sha256'] or source['probeSha256'] != report['sourceProbe']['sha256']:
        raise ValueError('Promotion Source acquisition binding differs')
    for entry in report['ownerWitnesses']:
        native_binding = checked_binding(entry['nativeReport'])
        native = read(entry['nativeReport']['path'])
        expected_raw, actual_raw = pointer(source, entry['sourcePointer']), pointer(native, entry['nativePointer'])
        expected, actual = promotion_projection(expected_raw), promotion_projection(actual_raw)
        variant = by_id[entry['id']]['variant']
        if not equal(expected, actual) or expected.get('selectedProperty') != variant or expected.get('outcome') != 'returned':
            raise ValueError('Promotion selected enum / shared actual state differs')
        if not expected.get('events') or expected.get('finalStrategy') != entry['finalActualStrategy']:
            raise ValueError('Promotion has no actual helper/final strategy state')
        row = by_id[entry['id']]
        row['witnesses'].append({'id': entry['id'] + ':owner-state', 'kind': 'object-state-assertion',
            'evidenceMap': binding(PROMOTION_MAP), 'bindings': dict(common, native=native_binding),
            'sourcePointer': entry['sourcePointer'], 'nativePointer': entry['nativePointer'],
            'expected': expected, 'actual': actual, 'strictSharedStateEqual': True,
            'rawHelperCountParityClaimed': False, 'excludedRawCountFields': ['promote', 'newLayeringModel'],
            'scope': 'Actual NodePromotion owner and prepare/magic/model/continuation state for this selected enum; raw recursion/frame counts preserved separately.',
            'unexercisedLeaves': report['unexercisedLeaves']})
        row['status'] = 'witnessed_scoped'
    none = report['noneSchedulerWitness']
    for key in ('sourceDefaultDeclaration', 'sourceSchedulerGuard'):
        raw = base64.b64decode(none[key]['bytesBase64'], validate=True)
        if sha(raw) != none[key]['sha256']:
            raise ValueError('Promotion NONE Source declaration/guard bytes differ')
    request = read(none['request']['path']); checked_binding(none['request'])
    option = 'org.eclipse.elk.layered.layering.nodePromotion.strategy'
    if request.get('constructor', {}).get('defaultLayoutOptions') or request.get('layoutArguments', {}).get('layoutOptions'):
        raise ValueError('NONE default witness has unaccounted global overrides')
    if any(option in obj.get('layoutOptions', {}) or 'elk.layered.layering.nodePromotion.strategy' in obj.get('layoutOptions', {}) for _, obj in walk(request)):
        raise ValueError('NONE historical default witness is not an absent property')
    refs = {}
    for role in ('source', 'native'):
        refs[role] = checked_binding(none[role]['raw'])
        actual = read(none[role]['raw']['path'])
        values = [obj.get('name') for _, obj in walk(actual.get('result', {}).get('logging', {}))]
        slots = [name for _, classes, _ in contexts(actual) for name in classes]
        if actual.get('outcome') != 'returned' or not slots or any('NodePromotion' in name for name in slots) or 'Node promotion heuristic' in values:
            raise ValueError('NONE actual successful scheduler exclusion is absent')
    checked_binding(none['nativeScheduler'])
    row = by_id[none['id']]
    row['witnesses'].append({'id': 'promotion-none-actual-scheduler-exclusion', 'kind': 'intentional-scheduler-exclusion',
        'evidenceMap': binding(PROMOTION_MAP), 'bindings': dict(refs, request=checked_binding(none['request'])),
        'sourceDefaultDeclaration': none['sourceDefaultDeclaration'], 'sourceSchedulerGuard': none['sourceSchedulerGuard'],
        'nativeScheduler': none['nativeScheduler'], 'newOwnerProcessCalled': False,
        'scope': 'Actual nonempty complete public layout excludes NodePromotion slots/tasks under the actual absent-property NONE default. Direct process(NONE) is not asserted to be a no-op.'})
    row['status'] = 'scheduler_exclusion_scoped'


def add_orientation_scope(supplemental):
    by_id = {row['id']: row for row in supplemental}
    report = read(ORIENTATION_MAP)
    common = {key: checked_binding(report[key]) for key in (
        'request', 'probe', 'sourceCommand', 'firstNativeCommand',
        'rotationCorrectedCommand', 'firstNativeChecker', 'rotationCorrectedChecker')}
    for entry in report['rows']:
        refs = dict(common, source=checked_binding(entry['sourceRaw']), native=checked_binding(entry['nativeRaw']))
        source, native = read(entry['sourceRaw']['path']), read(entry['nativeRaw']['path'])
        expected, actual = pointer(source, entry['sourcePointer']), pointer(native, entry['nativePointer'])
        if source.get('requestSha256') != common['request']['sha256'] or source.get('probeSha256') != common['probe']['sha256']:
            raise ValueError('Orientation Source acquisition binding differs')
        if not equal(expected, actual) or expected.get('id') != entry['id'] or expected.get('outcome') != 'returned' or not equal(expected.get('value'), entry['actualValue']):
            raise ValueError('Orientation actual helper/configuration state differs')
        value = expected['value']
        configuration = entry['kind'] == 'actual-phase-independent-configuration-state'
        resolver = entry['id'].startswith('UNDEFINED-')
        if configuration and (value['beforeP4HasFactory'] is not (value['selected'] == 'ALTERNATING') or value['slot'] != 3):
            raise ValueError('Unzip configuration did not preserve actual selection')
        if resolver and (value['before'] != 'UNDEFINED' or value['after'] != 'UNDEFINED' or value['result'] not in ('RIGHT', 'DOWN')):
            raise ValueError('Undefined resolver return/persistence contract differs')
        if entry['id'].startswith('reference-') and value['newVector'] is not True:
            raise ValueError('Reference-point helper did not return a new vector')
        for branch_id in entry['optionBranchIds']:
            row = by_id[branch_id]
            row['witnesses'].append({'id': entry['id'] + ':actual-orientation-state',
                'kind': 'configuration-state-assertion' if configuration else 'object-state-assertion',
                'evidenceMap': binding(ORIENTATION_MAP), 'bindings': refs,
                'sourceFunction': entry['sourceFunction'], 'nativeFunction': entry['nativeFunction'],
                'sourcePointer': entry['sourcePointer'], 'nativePointer': entry['nativePointer'],
                'expected': expected, 'actual': actual, 'strictStateEqual': True,
                'ownerProcessExecuted': entry['kind'] == 'actual-owner-body-and-state',
                'resolverReturnWitness': resolver, 'resolvedDirectionPersistenceClaimed': False,
                'publicLayoutExecuted': False, 'historicalRuntimeReboundToCurrentModule': False,
                'scope': ('Actual before-P4 configuration factory presence/absence only; no owner.process execution in this observation.' if configuration else
                          'Actual GraphTransformer LEFT/ROTATION working-graph state.' if entry['kind'] == 'actual-owner-body-and-state' else
                          'Actual helper return and identity state only; UNDEFINED resolution leaves the graph property unchanged.'),
                'limits': report['limits']})
            row['status'] = 'configuration_state_scoped' if configuration else 'witnessed_scoped'
            if configuration:
                row['enumConfigurationRouteClaimed'] = True
                row['ownerExecutionFromConfigurationWitnessClaimed'] = False


def add_consumer_enum_scope(supplemental):
    by_id = {row['id']: row for row in supplemental}
    report = read(CONSUMER_ENUM_MAP)
    for entry in report['rows']:
        refs = {key: checked_binding(value) for key, value in entry['bindings'].items()}
        source, native = read(refs['reference']['path']), read(refs['native']['path'])
        expected, actual = pointer(source, entry['sourcePointer']), pointer(native, entry['nativePointer'])
        if not equal(expected, actual) or not equal(expected, entry['expected']) or not equal(actual, entry['actual']):
            raise ValueError('Existing enum consumer actual state differs')
        if source.get('requestSha256') != refs['request']['sha256']:
            raise ValueError('Existing enum consumer request binding differs')
        probe_digest = source.get('probeSha256')
        if probe_digest is None and entry['id'].startswith('option:org.eclipse.elk.layered.portSortingStrategy:'):
            wrapper_path = 'tests/fixtures/suites/next-native/ports-order-oracle.json'
            wrapper = read(wrapper_path)
            if wrapper['observationSha256'] != refs['reference']['sha256']:
                raise ValueError('Existing port-order wrapper does not bind Source bytes')
            probe_digest = wrapper['probeSha256']
            refs['sourceWrapper'] = binding(wrapper_path)
        if probe_digest != refs['sourceProbe']['sha256'] or entry['publicRawSelectorBranchClaimed'] is not False:
            raise ValueError('Existing enum consumer probe/scope binding differs')
        row = by_id[entry['id']]
        row['witnesses'].append({'id': entry['id'] + ':existing-consumer-state', 'kind': 'object-state-assertion',
            'evidenceMap': binding(CONSUMER_ENUM_MAP), 'bindings': refs,
            'sourcePointer': entry['sourcePointer'], 'nativePointer': entry['nativePointer'],
            'expected': expected, 'actual': actual, 'strictStateEqual': True,
            'publicRawSelectorBranchClaimed': False, 'historicalRuntimeReboundToCurrentModule': False,
            'scope': entry['scope']})
        row['status'] = 'witnessed_scoped'


def network_simplex_projection(value):
    projected = json.loads(json.dumps(value))
    for event in projected['events']:
        event.pop('className', None)
    return projected


def add_network_simplex_scope(supplemental):
    by_id = {row['id']: row for row in supplemental}
    report = read(NETWORK_SIMPLEX_MAP)
    common = {key: checked_binding(report[key]) for key in (
        'request', 'sourceProbe', 'firstNativeChecker', 'recomputeCorrectedChecker',
        'runner', 'sourceCommand', 'nativePilotCommand', 'nativeRemainingCommand', 'nativeCorrectedRecomputeCommand')}
    for entry in report['rows']:
        refs = dict(common, source=checked_binding(entry['sourceRaw']), native=checked_binding(entry['nativeRaw']))
        source, native = read(entry['sourceRaw']['path']), read(entry['nativeRaw']['path'])
        if source.get('requestSha256') != common['request']['sha256'] or source.get('probeSha256') != common['sourceProbe']['sha256']:
            raise ValueError('Network simplex Source acquisition binding differs')
        source_raw, native_raw = pointer(source, entry['sourcePointer']), pointer(native, entry['nativePointer'])
        expected, actual = network_simplex_projection(source_raw), network_simplex_projection(native_raw)
        if not equal(expected, actual) or expected.get('id') != entry['caseId'] or expected.get('outcome') != 'returned':
            raise ValueError('Network simplex actual consumer state differs')
        if not equal(source_raw['events'], entry['sourceEvents']) or not equal(native_raw['events'], entry['nativeEvents']):
            raise ValueError('Network simplex actual event binding differs')
        row = by_id[entry['id']]
        if entry['caseId'].startswith('recompute-'):
            calls = expected['events'][:2]
            if [event.get('helper') for event in calls] != ['factory', 'placer.process'] or any(event.get('strategy') != row['variant'] for event in calls):
                raise ValueError('Repeater did not delegate the actual selected strategy')
        elif not any(event.get('helper') == 'isFlexibleNode' and event.get('flexibility') == row['variant'] for event in expected['events']):
            raise ValueError('Flexibility enum was not read by the actual consumer')
        row['witnesses'].append({'id': entry['caseId'] + ':network-simplex-consumer', 'kind': 'object-state-assertion',
            'evidenceMap': binding(NETWORK_SIMPLEX_MAP), 'bindings': refs,
            'sourceFunction': entry['sourceFunction'], 'nativeFunction': entry['nativeFunction'],
            'sourcePointer': entry['sourcePointer'], 'nativePointer': entry['nativePointer'],
            'expected': expected, 'actual': actual, 'strictSemanticStateEqual': True,
            'rawStrictEqual': equal(source_raw, native_raw),
            'excludedCrossHostFields': ['events[*].className'],
            'rawSourceClassNames': [event.get('className') for event in source_raw['events'] if 'className' in event],
            'rawNativeClassNames': [event.get('className') for event in native_raw['events'] if 'className' in event],
            'scope': 'Actual prepared NetworkSimplexPlacer flexibility/solver or Repeater factory and original placer.process; no full public selector or height-expansion claim.',
            'limits': report['limits'], 'historicalRuntimeReboundToCurrentModule': False})
        row['status'] = 'witnessed_scoped'



def validate_source_binding(source, refs):
    if source.get('requestSha256') != refs['request']['sha256'] or source.get('probeSha256') != refs['sourceProbe']['sha256']:
        raise ValueError('Final consumer Source acquisition binding differs')


def add_final_config_and_spline(supplemental):
    by_id = {row['id']: row for row in supplemental}
    for filename in (GREEDY_CONFIG_MAP, SPLINE_SOFT_MAP):
        report = read(filename)
        refs = {key: checked_binding(report[key]) for key in (
            'request', 'sourceProbe', 'nativeChecker', 'sourceRaw', 'nativeRaw', 'sourceCommand', 'nativeCommand')}
        source, native = read(refs['sourceRaw']['path']), read(refs['nativeRaw']['path'])
        validate_source_binding(source, refs)
        for entry in report['rows']:
            expected, actual = pointer(source, entry['sourcePointer']), pointer(native, entry['nativePointer'])
            if not equal(expected, actual):
                raise ValueError('Final consumer actual configuration/spline state differs')
            configuration = filename == GREEDY_CONFIG_MAP
            if configuration:
                if expected.get('outcome') != 'returned' or not equal(expected['root'], entry['actualRoot']) or not equal(expected['nested'], entry['actualNested']):
                    raise ValueError('Greedy root/nested configuration state differs')
            elif pointer(expected, entry['actualFinalModePointer']) != 'CONSERVATIVE_SOFT' or pointer(expected, entry['actualModeReadsPointer']) != ['CONSERVATIVE_SOFT', 'CONSERVATIVE_SOFT']:
                raise ValueError('Actual P5/Final did not read CONSERVATIVE_SOFT')
            row = by_id[entry['id']]
            row['witnesses'].append({'id': entry['id'] + ':actual-final-consumer',
                'kind': 'configuration-state-assertion' if configuration else 'object-state-assertion',
                'evidenceMap': binding(filename), 'bindings': refs,
                'sourceFunction': entry['sourceFunction'], 'nativeFunction': entry['nativeFunction'],
                'sourcePointer': entry['sourcePointer'], 'nativePointer': entry['nativePointer'],
                'expected': expected, 'actual': actual, 'strictStateEqual': True,
                'ownerExecutionFromConfigurationWitnessClaimed': False,
                'scope': 'Actual activation and configuration factory presence for root/nested graph; not execution of the greedy body.' if configuration else 'Actual P5+Final prepared graph and two stored SOFT mode reads, full segment/control state; no public JSON layout or spline obstacle guarantee.',
                'limits': report['limits'], 'historicalRuntimeReboundToCurrentModule': False})
            row['status'] = 'configuration_state_scoped' if configuration else 'witnessed_scoped'


def component_geometry_projection(value):
    # Source/native enum identity bucket order is an explicit ADR0010 boundary.
    # Preserve raw split/groups/list order; compare only actual geometry by ID.
    nodes = value['nodes']
    if len({node['id'] for node in nodes}) != len(nodes):
        raise ValueError('Component geometry has duplicate stable node IDs')
    return {'size': value['size'], 'nodes': sorted(nodes, key=lambda node: node['id'])}


def add_component_group_scope(supplemental):
    by_id = {row['id']: row for row in supplemental}
    report = read(COMPONENT_GROUP_MAP)
    common = {key: checked_binding(report[key]) for key in ('sourceProbe', 'nativeChecker', 'prepare', 'sourceCommand', 'nativeCommand')}
    adapters = [checked_binding(entry) for entry in report['historicalAdapters']]
    consumers = [checked_binding(entry) for entry in report['currentConsumers']]
    for entry in report['rows']:
        refs = {key: checked_binding(entry[key]) for key in ('request', 'reference', 'native')}
        source, native = read(refs['reference']['path']), read(refs['native']['path'])
        expected_raw, actual_raw = pointer(source, entry['referencePointer']), pointer(native, entry['nativePointer'])
        if not equal(expected_raw, entry['referenceValue']) or not equal(actual_raw, entry['nativeValue']):
            raise ValueError('Component/group actual state binding differs')
        identity_boundary = entry['status'] == 'helper_state_scoped_with_identity_order_diagnostic'
        expected = component_geometry_projection(expected_raw) if identity_boundary else expected_raw
        actual = component_geometry_projection(actual_raw) if identity_boundary else actual_raw
        if not equal(expected, actual):
            raise ValueError('Component/group actual scoped state differs')
        if refs['reference']['path'].endswith('components-order-family-01/source-02.json'):
            validate_source_binding(source, {'request': refs['request'], 'sourceProbe': common['sourceProbe']})
        row = by_id['option:' + entry['optionId'] + ':' + entry['variant']]
        exclusion = entry['status'] == 'scheduler_exclusion_scoped'
        if exclusion and (expected['strategy'] != 'NONE' or expected['strategyReads'] != ['NONE'] or expected['sorterScheduled'] is not False):
            raise ValueError('Actual model-order NONE scheduler exclusion differs')
        witness = {'id': row['id'] + ':actual-component-group-state',
            'kind': 'identity-order-boundary-state' if identity_boundary else 'scheduler-exclusion-state' if exclusion else 'object-state-assertion',
            'evidenceMap': binding(COMPONENT_GROUP_MAP), 'bindings': refs, 'newCaptureBindings': common,
            'historicalAdapters': adapters, 'currentConsumers': consumers,
            'referencePointer': entry['referencePointer'], 'nativePointer': entry['nativePointer'],
            'expected': expected, 'actual': actual, 'strictScopedStateEqual': True,
            'rawStrictEqual': equal(expected_raw, actual_raw), 'scope': entry['scope'],
            'limits': report['limitations'], 'historicalRuntimeReboundToCurrentModule': False}
        if identity_boundary:
            if equal(expected_raw, actual_raw) or entry['rawStrictPassed'] is not False or entry['rawDifferenceCount'] != 23:
                raise ValueError('Original identity-order diagnostic was lost')
            witness.update(rawReference=expected_raw, rawNative=actual_raw, rawDifferenceCount=23,
                           projection='Only graph size and actual nodes sorted by stable ID; split/group bucket and list order remain raw diagnostic, not parity.')
        row['witnesses'].append(witness)
        row['status'] = 'identity_order_boundary_scoped' if identity_boundary else 'scheduler_exclusion_scoped' if exclusion else 'witnessed_scoped'


def add_postcompaction_wrapping_scope(supplemental):
    by_id = {row['id']: row for row in supplemental}
    report = read(POST_WRAPPING_MAP)
    boundary = report['oldManualJsonReflectionFailure']
    old_source = read(checked_binding(boundary['sourceRaw'])['path'])
    old_native = read(checked_binding(boundary['nativeRaw'])['path'])
    if old_source.get('outcome') != 'threw' or old_native.get('outcome') != 'threw' or not equal(old_source.get('error'), boundary['error']) or old_native.get('error', {}).get('message') != boundary['error']['message']:
        raise ValueError('Historical public MANUAL reflection failure was lost')
    for span in report['sourceRouteSupportSpans']:
        if sha(base64.b64decode(span['base64'], validate=True)) != span['sha256']:
            raise ValueError('Postcompaction/wrapping Source route bytes differ')
    typed_refs = {key: checked_binding(report[key]) for key in ('newRequest', 'newSourceProbe', 'newNativeChecker', 'newSourceCommand', 'newNativeCommand')}
    for entry in report['rows']:
        row = by_id[entry['id']]
        witness = {'id': entry['id'] + ':post-wrapping-state', 'kind': entry['kind'], 'evidenceMap': binding(POST_WRAPPING_MAP),
                   'internalEnumTraceClaimed': False, 'causalGeometryDifferenceClaimed': False,
                   'historicalRuntimeReboundToCurrentModule': False, 'limits': report['claimLimits']}
        kind = entry['kind']
        if kind == 'source-route-state':
            refs = {key: checked_binding(entry[key]) for key in ('request', 'sourceRaw', 'nativeRaw', 'comparisonReport')}
            source, native = read(refs['sourceRaw']['path']), read(refs['nativeRaw']['path'])
            if source.get('outcome') != 'returned' or native.get('outcome') != 'returned' or pointer(source, entry['sourceInputValuePointer']) != row['variant'] or pointer(native, entry['nativeInputValuePointer']) != row['variant']:
                raise ValueError('Actual public route selected value/outcome differs')
            assertions = []
            for geometry in entry['geometryState']:
                expected, actual = pointer(source, geometry['pointer']), pointer(native, geometry['pointer'])
                if not equal(expected, actual) or not equal(expected, geometry['value']):
                    raise ValueError('Postcompaction/wrapping actual public geometry differs')
                assertions.append({'pointer': geometry['pointer'], 'expected': expected, 'actual': actual})
            for role, raw in (('source', source), ('native', native)):
                tasks = entry[role + 'Tasks']
                if not tasks or any(not equal(pointer(raw, item['pointer']), item['value']) for item in tasks):
                    raise ValueError('Actual postcompaction/wrapping task differs')
            if not entry['sourceActualSlots'] or any(pointer(source, item['pointer']) != item['value'] for item in entry['sourceActualSlots']):
                raise ValueError('Actual public configured slot differs')
            module = entry['relevantNativeModule']
            current = binding(module['file'])
            if current['sha256'] != module['currentSha256'] or module['currentSha256'] != module['historicalExecutionSha256']:
                raise ValueError('Historical route implementation bytes differ')
            witness.update(bindings=refs, assertions=assertions, sourceTasks=entry['sourceTasks'], nativeTasks=entry['nativeTasks'],
                           sourceActualSlots=entry['sourceActualSlots'], nativeModule=current,
                           historicalNativeVersion=entry['historicalNativeVersion'], scope=entry['scope'])
            row['status'] = 'source_route_state_scoped'
        elif kind == 'actual-public-scheduler-exclusion-with-source-default-route':
            refs = {'request': checked_binding(entry['request'])}
            request = read(entry['request']['path'])
            option = row['optionId']
            if any(any(key in obj.get('layoutOptions', {}) for key in (option, 'elk.' + option.removeprefix('org.eclipse.elk.'))) for _, obj in walk(request)):
                raise ValueError('Wrapping OFF witness is not absent-property default')
            for observation in entry['observations']:
                refs[observation['role']] = checked_binding(observation['raw'])
                raw = read(observation['raw']['path'])
                if raw.get('outcome') != 'returned' or not raw['result'].get('children'):
                    raise ValueError('Wrapping OFF has no actual nonempty return')
                for item in observation['tasks'] + observation['slots']:
                    if pointer(raw, item['pointer']) != item['value'] or 'wrapping' in item['value'].lower() or 'wrapper' in item['value'].lower():
                        raise ValueError('Wrapping OFF actual exclusion differs')
                task_names = [obj.get('name') for _, obj in walk(raw['result'].get('logging', {})) if isinstance(obj.get('name'), str)]
                slot_names = [name for _, classes, _ in contexts(raw) for name in classes]
                if not slot_names or any('wrapping' in name.lower() or 'wrapper' in name.lower() for name in task_names + slot_names):
                    raise ValueError('Wrapping OFF raw scheduler contains a wrapping processor')
            witness.update(bindings=refs, sourceDefault=entry['sourceDefault'], scope='Actual default OFF public scheduler exclusion plus fixed Source declaration/selector; no forced process(OFF) no-op.')
            row['status'] = 'scheduler_exclusion_scoped'
        elif kind in ('actual-owner-helper-delegation-and-state', 'actual-manual-calculator-original-owner-consumer'):
            refs = dict(typed_refs, source=checked_binding(entry['sourceRaw']), native=checked_binding(entry['nativeRaw']))
            source, native = read(entry['sourceRaw']['path']), read(entry['nativeRaw']['path'])
            validate_source_binding(source, {'request': refs['newRequest'], 'sourceProbe': refs['newSourceProbe']})
            src_pointers = entry.get('sourcePointers', [entry.get('sourcePointer')])
            nat_pointers = entry.get('nativePointers', [entry.get('nativePointer')])
            assertions = []
            for src_pointer, native_pointer in zip(src_pointers, nat_pointers, strict=True):
                expected, actual = pointer(source, src_pointer), pointer(native, native_pointer)
                if not equal(expected, actual):
                    raise ValueError('Actual typed MANUAL/validify owner state differs')
                assertions.append({'sourcePointer': src_pointer, 'nativePointer': native_pointer, 'expected': expected, 'actual': actual})
            if kind == 'actual-owner-helper-delegation-and-state':
                actual = assertions[0]['actual']
                if not equal(actual['events'], entry['actualEvents']) or not equal(actual['before'], entry['before']) or not equal(actual['after'], entry['after']):
                    raise ValueError('Actual validify helper/performCuts state differs')
            else:
                if any(item['actual'].get('helper') != 'manual' or item['actual'].get('result') != [2, 4] for item in assertions):
                    raise ValueError('Actual MANUAL calculator return differs')
            witness.update(bindings=refs, assertions=assertions, scope='Typed prepared MANUAL calculator -> actual chosen validify -> original performCuts body, full layer/endpoint state; not public raw reflection support.',
                           oldManualPublicFailure=report['oldManualJsonReflectionFailure'])
            row['status'] = 'witnessed_scoped'
        else:
            raise ValueError('Unknown final postcompaction/wrapping witness kind')
        row['witnesses'].append(witness)



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
                                     'optionId': option, 'variant': member, 'status': 'no_variant_witness',
                                     'sourceEvidence': [dict(binding('src/pyelk/options/_generic_data.py'), locator=option)],
                                     'witnesses': [], 'limitations': ['Explicit finite enum denominator; requires variant-specific accounting, not input-occurrence inference.']})
    add_effects(supplemental)
    add_named_strategies(supplemental, cases)
    add_current_increment(rows, supplemental)
    add_existing_enum_scope(supplemental)
    add_promotion_scope(supplemental)
    add_orientation_scope(supplemental)
    add_consumer_enum_scope(supplemental)
    add_network_simplex_scope(supplemental)
    add_final_config_and_spline(supplemental)
    add_postcompaction_wrapping_scope(supplemental)
    add_component_group_scope(supplemental)
    counts = dict(Counter(x['status'] for x in rows))
    return {'schema': 'pyelk-declared-branch-matrix/v1', 'scope': 'finite-factory-and-existing-evidence-increment',
            'workerSha256': packet['workerSha256'], 'productExecutionCount': 0, 'sourceExecutionCount': 0,
            'denominator': {'coreFactories': 90, 'intermediate': 59, 'P1': 9, 'P2': 9, 'P3': 4, 'P4': 5, 'P5Factories': 4,
                            'P5DistinctBodies': 3, 'supplementalEnumRows': len(supplemental)},
            'summary': {'coreStatuses': counts, 'normalSavedCasesRead': len(cases),
                        'supplementalStatuses': dict(Counter(x['status'] for x in supplemental)),
                        'coreRowsAccountedForWithinStatedScope': all(row['status'] != 'no_runtime_witness' for row in rows),
                        'allDeclaredEnumBranchesAccepted': all(row['status'] == 'witnessed_scoped' for row in supplemental),
                        'allDeclaredEnumRowsAccountedForWithinStatedScope': all(row['status'] != 'no_variant_witness' for row in supplemental),
                        'unwitnessedEnumIds': [row['id'] for row in supplemental if row['status'] == 'no_variant_witness'],
                        'fullRawEnumParityClaimed': False,
                        'normalMathematicsBoundaryRows': [row['id'] for row in rows if row.get('normalRuntimeMathPass') is False],
                        'coreNoDirectTraceRows': [row['id'] for row in rows if row.get('noDirectTrace') is True],
                        'unwitnessedCoreIds': [r['id'] for r in rows if r['status'] in ('configured_only', 'no_runtime_witness')]},
            'inputs': [binding(SUMMARY), binding(SOURCE), binding('src/pyelk/algorithms/layered/phase_factories.py'),
                       binding('tests/fixtures/suites/full-native-layered/cases.json'),
                       binding(P1_P2_MAP), binding(OPTIONS_MANIFEST.relative_to(ROOT).as_posix()),
                       binding(LOGGED_REPORT), binding(LOGGED_SUITE),
                       binding(OLD_ENUM_MAP), binding(CONSUMER_LINKS), binding(STAGED_CLASSIFICATIONS),
                       binding(FIVE_OWNERS), binding(UNZIP_EQUAL),
                       binding(EXISTING_ENUM_MAP),
                       binding(PROMOTION_MAP), binding(ORIENTATION_MAP), binding(CONSUMER_ENUM_MAP), binding(NETWORK_SIMPLEX_MAP),
                       binding(GREEDY_CONFIG_MAP), binding(SPLINE_SOFT_MAP), binding(POST_WRAPPING_MAP), binding(COMPONENT_GROUP_MAP),
                       binding(MANIFEST.relative_to(ROOT).as_posix())],
            'interpretation': ['No missing implementation is inferred from a missing witness.',
                               'Literal Source/native tasks or original owner.process with strict raw state projections elevate core rows; unique hierarchy tasks need no flat slot log.',
                               'Configured slots, enum membership and class names alone never elevate runtime witness status.',
                               'Historical observations retain their original engine/version and source bindings; current anchors do not rebind old executions.',
                               'Shared-body factory aliases do not create duplicate mathematics. Source raw-unconstructible manager boundaries are contract evidence, never normal mathematics PASS.',
                               'HighDegree has a true causal public output witness but retains noDirectTrace; raw role-specific unzip/EQUAL observer structures are not falsely called equal.',
                               'Supplemental causal rows require successful raw paired pointer projections and a genuine before/after change; a passed report flag alone is insufficient.',
                               'All supplemental rows now have an exact declared scope; direct-only parity remains false because configuration, route/state, scheduler exclusions and ADR0010 identity ordering are distinct evidence kinds.',
                               'Typed MANUAL wrapping does not remove the archived public JSON reflection boundary. Supplemental accounting does not prove every internal leaf or all option combinations.'],
            'rows': rows, 'supplementalRows': supplemental}


def markdown(data):
    lines = ['# Layered declared-branch evidence matrix', '',
             'Finite core denominator: 59 intermediate factories, P1 9, P2 9, P3 4, P4 5, and P5 4 factories / 3 distinct bodies. UNDEFINED and ORTHOGONAL share the actual orthogonal body.', '',
             'This generator reads saved data only. No product, Source process or old suite is executed. Configured slots and input occurrence alone never establish runtime consumption.', '',
             '## Core accounting', '', '| Status | Rows |', '|---|---:|']
    lines += ['| ' + key + ' | ' + str(value) + ' |' for key, value in data['summary']['coreStatuses'].items()]
    lines += ['', '85 rows have actual task or owner/helper-state witnesses. HighDegree has a verified causal public output witness and explicitly retains noDirectTrace. Two Source-constructed orthogonal aliases share one already witnessed body. Two label-manager rows satisfy the fixed Native JSON/null-only boundary; they are not normal mathematics PASS or arbitrary callback support.', '',
              'Core accounting does not close every internal conditional branch. The supplemental finite enum denominator is independent: ' + str(data['denominator']['supplementalEnumRows']) + ' rows, ' + str(data['summary']['supplementalStatuses'].get('witnessed_scoped', 0)) + ' scoped witnesses. Every row now has an explicit finite scope or identity boundary. The direct-only allDeclaredEnumBranchesAccepted flag remains false: configuration, route/state, exclusion and identity boundary evidence are deliberately not reclassified as direct mathematics/raw parity. No all-option Cartesian-product claim is made.', '',
              '## Core rows', '', '| Factory | Status | Actual task cases | Object states | First witness | Implementation |', '|---|---|---:|---:|---|---|']
    for row in data['rows']:
        first = row['witnesses'][0]['id'] if row['witnesses'] else '(boundary / alias evidence)'
        impl = row['implementation'][0]
        lines.append('| ' + row['family'] + '.' + row['variant'] + ' | ' + row['status'] + ' | ' + str(row['actualTaskCaseCount']) + ' | ' + str(row['objectStateWitnessCount']) + ' | ' + first + ' | ' + impl['path'].split('/')[-1] + ':' + str(impl['line']) + ' |')
    lines += ['', '## Scope and retained failures', '',
              'Historical primitive, prepared-phase and public observations retain their own original runtime/module hashes. Current implementation anchors do not rebind historical executions. Raw failed probes and the logged Source/native NPE pairs remain archived, even where later direct owner-state observations establish a normal branch witness.', '',
              'Unzip now has real before/after layer-array evidence: one six-node layer becomes two alternating three-node layers. Its monitor is unused by Source. EQUAL has a genuine zero-incoming helper fallback event that delegates the original return function and yields0. Role-specific callable names and the Source-only observer are not declared raw-identical.', '',
              'The 31 older enum rows were rechecked against actual original DTOs and saved native DTOs, not a pass flag. BK selects the exact original02/03 raw case after the historical observer correction; the first native geometry is unchanged. Port-side witnesses concern actual produced side/anchor state in the approved primitive scope, not every importer target.', '',
              'The current family increment adds actual LEFT/ROTATION transformer state; CENTER/TOP_LEFT helper vectors; UNDEFINED resolver returns RIGHT/DOWN without persisting the resolved direction; and NONE/ALTERNATING before-P4 configuration factory exclusion/inclusion. The latter two rows are configuration-state scope, not owner execution. Existing ALTERNATING body execution remains separately bound. Nine older port-sorting, layer-constraint and model-order DTOs add actual helper/body states, with VM enum-adapter and supplied-layering limitations retained. Nine NetworkSimplex consumer DTOs add actual flexibility/solver and Repeater factory-to-placer calls. Only event className is excluded across hosts; all selected strategies, calls, geometry and property state remain strict. Raw first failures and class-name differences remain archived, and physical height expansion is not claimed. None implies whole public selector coverage. Promotion NONE is an intentional real scheduler exclusion under the bound Source default/guard, not a forced process(NONE) no-op. Promotion recursive/frame helper counts remain raw and are not equated; IMPROVED retry and NODECOUNT terminal cap remain unexercised leaves.', '',
              '## Supplemental enum values', '', '| Option | Direct helper/body/effect witness | Configuration / route / exclusion / identity-boundary scope | No variant witness in this table |', '|---|---|---|---|']
    grouped = {}
    for row in data['supplementalRows']:
        grouped.setdefault(row['optionId'], []).append(row)
    for option, rows in grouped.items():
        lines.append('| ' + option + ' | ' + ', '.join(row['variant'] for row in rows if row['status'] == 'witnessed_scoped') + ' | ' + ', '.join(row['variant'] + ' (' + row['status'] + ')' for row in rows if row['status'] in ('consumer_state_scoped', 'scheduler_exclusion_scoped', 'configuration_state_scoped', 'source_route_state_scoped', 'identity_order_boundary_scoped')) + ' | ' + ', '.join(row['variant'] for row in rows if row['status'] == 'no_variant_witness') + ' |')
    lines += ['', '## Remaining finite work', '',
              'There is no unclassified core factory row. HighDegree lacks a direct body trace but has an actual scoped option effect; manager callback restrictions are an upstream compiled/JSON boundary, not a missing successful raw callback. Shared aliases do not require duplicate mathematics.', '',
              'There are no unclassified rows in the declared 121-value enum denominator. Seven Greedy/Unzip rows prove actual configuration state, three NONE/OFF rows prove actual scheduler exclusion, and seven compaction/wrapping rows bind fixed Source selectors to successful public tasks and full geometry state without inventing an internal enum trace or causal difference. Component NONE retains its original 23 raw identity-bucket-order differences under ADR0010; only actual geometry by stable node ID is equal. This is a documented identity-order boundary, not normal raw parity. MANUAL has real typed calculator/performCuts evidence, while the historical public JSON reflective-value failure remains archived; no new public raw support is claimed. Promotion retry/cap leaves and other internal conditions retain the existing limited-sample caveats. No additional mandatory enum mapping remains in this finite table.', '',
              '## Portable offline check', '',
              '`python scripts/iteration/declared_branch_matrix.py --check` reads tracked source/request inputs and exact members of branches.zip / options.zip, checks bound hashes and recomputes states, causal projections and accounting. It never falls back to a local ignored directory. Raw observation bytes remain unchanged.', '']
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
