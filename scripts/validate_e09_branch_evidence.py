"""Map finite E09 declarations to actual portable observations, never saved PASS.

The runtime gate first independently validates all three receipts in the same
call. This pure map then recomputes each branch's concrete observation predicate.
Missing actual witnesses remain pending. No candidate code is imported here.
"""
from __future__ import annotations
import argparse
import base64
import copy
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
import struct
import sys

from layout_checks import ROOT, load, geometry
from validate_e04_runtime import embedded_json, exact
from validate_e09_sources import BRANCH_MATRIX, validate_branch_matrix

MAP = 'references/e09-branch-evidence-map.json'
INSTALLED = 'references/e09-installed-check.json'
COVERAGE = 'references/e09-coverage-installed.json'
P = 'org.eclipse.elk.'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':'))


def decode(capture):
    raw = base64.b64decode(capture['observationBytesBase64'], validate=True)
    fingerprint = hashlib.sha256(raw).hexdigest()
    require(fingerprint == capture['observationSha256'], 'Branch observation bytes differ')
    return embedded_json(raw), fingerprint


def equal(a, b):
    return canonical(a) == canonical(b)


def pointer(value, path):
    for part in path.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if type(value) is list else value[part]
    return value


def monitors(tree):
    if type(tree) is dict and 'name' in tree:
        yield tree
        for child in tree.get('children', []):
            yield from monitors(child)


def selector(request, option):
    global_options = request['layoutArguments'].get('layoutOptions', request['constructor'].get('defaultLayoutOptions', {}))
    for options in (request['graph'].get('layoutOptions', {}), global_options):
        for key in (P + option, 'elk.' + option):
            if key in options:
                return key, options[key]
    return None, None


def premises(request):
    from e07_geometry_premise import premises as independent
    request = copy.deepcopy(request)
    for flag in ('logging', 'measureExecutionTime'):
        request['layoutArguments'].pop(flag, None)
    if type(request['graph']) is dict:
        request['graph'].pop('logging', None)
    return independent(request)


def graph_traits(request):
    graph = request['graph']; nodes = graph.get('children', []); edges = graph.get('edges', [])
    pairs = [(edge['sources'][0], edge['targets'][0]) for edge in edges]
    outgoing = {node['id']: set() for node in nodes}; incoming = {node['id']: set() for node in nodes}
    for source, target in pairs:
        outgoing[source].add(target); incoming[target].add(source)
    gray = set(); black = set()
    def cycle(node):
        if node in gray: return True
        if node in black: return False
        gray.add(node)
        if any(cycle(child) for child in outgoing[node]): return True
        gray.remove(node); black.add(node); return False
    cyclic = any(cycle(node) for node in outgoing)
    remaining = set(outgoing); count = 0
    while remaining:
        count += 1; stack = [next(iter(remaining))]
        while stack:
            node = stack.pop()
            if node in remaining:
                remaining.remove(node); stack.extend(outgoing[node] | incoming[node])
    def nonself_cycle():
        for source,target in pairs:
            if source == target: continue
            pending = [target]; seen = set()
            while pending:
                node = pending.pop()
                if node == source: return True
                if node in seen: continue
                seen.add(node); pending.extend(b for a,b in pairs if a == node and a != b)
        return False
    return {'nodes': nodes, 'edges': edges, 'pairs': pairs, 'components': count, 'nonselfCycle': nonself_cycle(),
            'cyclic': cyclic, 'loop': any(a == b for a, b in pairs), 'parallel': len(set(pairs)) != len(pairs),
            'fork': any(len(values) > 1 for values in outgoing.values()),
            'join': any(len(values) > 1 for values in incoming.values())}


def original_skip(traits):
    """A direct edge with a longer alternative DAG path forces original rank gap."""
    if traits['cyclic']: return False
    for source, target in traits['pairs']:
        pending = [(source, 0)]; visited = set()
        while pending:
            node, length = pending.pop()
            if node == target and length >= 2: return True
            if node in visited: continue
            visited.add(node)
            pending.extend((b, length+1) for a,b in traits['pairs'] if a == node and not (node == source and b == target))
    return False


PUBLIC_IDS = {
    ('domain-bounds', 'nodes-9-rejected'): ['nodes-9'], ('domain-bounds', 'edges-29-rejected'): ['edges-29'],
    ('domain-bounds', 'over-1000000-rejected'): ['measure-over', 'spacing-over', 'padding-over'],
    ('domain-bounds', 'seed-zero-rejected'): ['seed-zero'],
    ('domain-bounds', 'seed-negative-boundary'): ['seed-negative-boundary'],
    ('domain-bounds', 'seed-positive-boundary'): ['seed-positive-boundary'],
    ('domain-rejections', 'ports'): ['ports'], ('domain-rejections', 'labels'): ['labels'],
    ('domain-rejections', 'compound'): ['compound'], ('domain-rejections', 'edge-local-options'): ['edge-local-options'],
    ('domain-rejections', 'child-options-except-padding'): ['child-local-options'],
    ('domain-rejections', 'hyperedges'): ['hyperedge'], ('domain-rejections', 'root-endpoint'): ['root-endpoint'],
    ('domain-rejections', 'legacy-properties'): ['legacy-properties'], ('domain-rejections', '$H'): ['reference-hash'],
    ('domain-rejections', 'nonstring-id'): ['nonstring-id'],
    ('domain-existing-geometry', 'root-x-y-width-height'): ['root-x', 'root-y', 'root-width', 'root-height'],
    ('domain-existing-geometry', 'child-x-y'): ['child-x', 'child-y'],
    ('domain-existing-geometry', 'edge-sections'): ['edge-sections'],
    ('domain-existing-geometry', 'edge-junctionPoints'): ['edge-junctionPoints'],
    ('domain-existing-geometry', 'edge-bendPoints'): ['edge-bendPoints'],
    ('domain-existing-geometry', 'edge-startPoint-endPoint'): ['edge-startPoint', 'edge-endPoint'],
    ('domain-existing-geometry', 'edge-sourcePoint-targetPoint'): ['edge-sourcePoint', 'edge-targetPoint'],
    ('domain-existing-geometry', 'edge-container'): ['edge-container'],
    ('domain-child-padding', 'object-rejected'): ['padding-object', 'child-padding-object'],
    ('domain-child-padding', 'other-local-option-rejected'): ['child-local-options'],
    ('diagnostic-flags', 'non-bool-rejected'): [flag + '-' + kind for flag in ('logging', 'measureExecutionTime')
                                              for kind in ('zero', 'one', 'text', 'null')],
}

LIFECYCLE_GROUPS = {
    ('api-registry', 'explicit-layered'): 'registry', ('api-registry', 'canonical-alias-dedup'): 'registry',
    ('api-worker-options', 'workerUrl-rejected'): 'registry',
    ('api-closed', 'last-trace-cleared'): 'registry/closedTrace',
    ('lifecycle-fifo', 'max-pending-1-to-64'): 'capacity',
    ('lifecycle-timeout', 'includes-queue'): 'queuedTimeout',
    ('lifecycle-timeout', 'running-killed'): 'runningTimeout',
    ('lifecycle-timeout', 'slot-recovers'): 'runningTimeout',
    ('lifecycle-cancel-close', 'close-running-and-queued'): 'crossThreadClose',
    ('lifecycle-cancel-close', 'close-idempotent'): 'crossThreadClose',
    ('lifecycle-cancel-close', 'close-from-other-thread'): 'crossThreadClose',
    ('lifecycle-errors', 'protocol-error'): 'faults', ('lifecycle-errors', 'internal-import-error'): 'faults',
    ('lifecycle-errors', 'spawn-failure'): 'faults',
}

API_FIELDS = {
    'api-registry': '/lifecycle/metadata', 'api-metadata': '/lifecycle/metadata',
    'api-algorithm-errors': '/lifecycle/publicErrors', 'api-closed': '/lifecycle/metadata',
    'api-worker-options': '/lifecycle/publicErrors/constructorWorker',
    'lifecycle-fifo': '/lifecycle/fifoRecoveryClose', 'lifecycle-cancel-close': '/lifecycle/queue',
    'lifecycle-timeout': '/lifecycle/resourceActions/timeout',
    'lifecycle-loop-trace': '/lifecycle/overlapAndLoop', 'lifecycle-errors': '/lifecycle/resourceActions',
}


def route(declaration, branch):
    key = declaration, branch
    if key == ('option-scope', 'unselected-constructor-not-parsed'):
        return {'role': 'api', 'kind': 'api-observation',
                'pointer': '/lifecycle/publicErrors/emptyCallReplacesBadConstructor',
                'assertion': 'Source-bound public_errors_probe calls default elk.algorithm=V_UNKNOWN with explicit layoutOptions={} and returns real geometry'}
    if key in PUBLIC_IDS:
        return {'role': 'newcoverage', 'kind': 'host-public', 'publicCaseIds': PUBLIC_IDS[key],
                'fields': ['inputBefore', 'constructorBefore', 'argumentsBefore', 'outcome', 'error/result',
                           'inputAfter', 'constructorAfter', 'argumentsAfter']}
    if declaration.startswith('option-') and branch == 'invalid-value' or key == ('option-scope', 'same-scope-alias-conflict'):
        return {'role': 'newcoverage', 'kind': 'host-public-selector', 'fields': ['publicCases[].inputBefore/layoutOptions',
                'publicCases[].error/name', 'publicCases[].error/code', 'publicCases[].error/path']}
    if key in LIFECYCLE_GROUPS:
        return {'role': 'newcoverage', 'kind': 'lifecycle-probe', 'pointer': '/' + LIFECYCLE_GROUPS[key],
                'assertion': 'e09_host_lifecycle_probe.validate_lifecycle_observation + concrete branch predicate'}
    if declaration in API_FIELDS:
        return {'role': 'api', 'kind': 'api-observation', 'pointer': API_FIELDS[declaration],
                'assertion': 'validate_e08_api.validate_native_observation + concrete branch predicate'}
    if declaration in ('diagnostic-clock', 'diagnostic-collect', 'diagnostic-monitor-state', 'diagnostic-number-adapter', 'diagnostic-boundaries'):
        field = ('numberAdapter' if declaration == 'diagnostic-number-adapter' else
                 'kernelBoundaries' if declaration == 'diagnostic-boundaries' else 'monitorPrimitives')
        return {'role': 'newcoverage', 'kind': 'host-primitive', 'pointer': '/' + field,
                'assertion': 'validate_e09_coverage.validate_host_observation + concrete branch predicate'}
    roles = ['newcoverage'] if declaration.startswith('diagnostic-') else ['geometry', 'newcoverage']
    return {'roles': roles, 'kind': 'layout-observation', 'fields': ['original request', 'result', 'inputBefore/inputAfter',
            'constructorBefore/constructorAfter', 'argumentsBefore/argumentsAfter'],
            'assertion': declaration + '/' + branch}


def expected_mapping(root=ROOT):
    matrix = load(Path(root) / BRANCH_MATRIX)
    validation = validate_branch_matrix(matrix, root)
    require(validation['passed'] is True, 'Branch declarations are invalid: ' + str(validation['errors']))
    return {'schema': 'py-elk-e09-branch-evidence-map/v1', 'scope': 'E09-ADR0008-revision1',
            'matrix': BRANCH_MATRIX, 'requiredBranchCount': 219,
            'receiptPaths': {'geometry': INSTALLED, 'api': INSTALLED + '#/apiRuntime', 'newcoverage': COVERAGE},
            'rows': [{'declarationId': row['id'], 'branch': branch, 'evidence': route(row['id'], branch)}
                     for row in matrix['rows'] for branch in row['branches']],
            'runtimeAccepted': False, 'meaning': 'Frozen observation predicates; actual witnesses/pending go to separate runtime output.'}


def unchanged(observation, request):
    return all(equal(observation.get(stem + suffix, request[key]) if suffix == 'Before' else observation[stem + suffix], request[key]) for stem, key in
               (('input', 'graph'), ('constructor', 'constructor'), ('arguments', 'layoutArguments'))
               for suffix in ('Before', 'After'))


def layout_match(declaration, branch, request, observation):
    if observation.get('outcome') != 'returned' or not unchanged(observation, request): return False
    result = observation['result']; graph = request['graph']; arguments = request['layoutArguments']
    p = premises(request)
    if p is None: return False
    options = p['options']; traits = graph_traits(request); nodes = traits['nodes']; edges = traits['edges']
    tree = result.get('logging', {}); flat = list(monitors(tree)); logs = [message for node in flat for message in node.get('logs', [])]
    logging = arguments.get('logging', False); timing = arguments.get('measureExecutionTime', False)
    if declaration.startswith('option-') and declaration != 'option-scope':
        option = declaration[len('option-'):]; key, value = selector(request, option)
        if branch == 'default': return key is None
        if branch == 'full-id': return key == P + option
        if branch == 'elk-alias': return key == 'elk.' + option
        return branch == 'valid-value' and key is not None
    if declaration == 'option-scope':
        constructor = request['constructor']; global_options = arguments.get('layoutOptions', constructor.get('defaultLayoutOptions', {}))
        return {'constructor-selected': 'defaultLayoutOptions' in constructor and 'layoutOptions' not in arguments,
                'call-replaces': bool(constructor.get('defaultLayoutOptions')) and bool(arguments.get('layoutOptions')),
                'call-empty-replaces': bool(constructor.get('defaultLayoutOptions')) and arguments.get('layoutOptions') == {},
                'root-local-overrides': any(key in graph.get('layoutOptions', {}) and value != graph['layoutOptions'][key]
                                          for key, value in global_options.items()),
                'unselected-constructor-not-parsed': bool(constructor.get('defaultLayoutOptions')) and arguments.get('layoutOptions') == {}}.get(branch, False)
    if declaration == 'domain-bounds':
        return {'nodes-0': len(nodes) == 0, 'nodes-8': len(nodes) == 8, 'edges-28': len(edges) == 28,
                'measure-0': any(node[key] == 0 for node in nodes for key in ('width', 'height')),
                'measure-1000000': any(node[key] == 1000000 for node in nodes for key in ('width', 'height'))}.get(branch, False)
    if declaration == 'domain-topology':
        identifier = graph.get('id', '')
        return {'empty': not nodes, 'singleton': len(nodes) == 1 and not edges,
                'chain': len(nodes) > 1 and len(edges) == len(nodes)-1 and not traits['cyclic'] and not traits['fork'] and not traits['join'],
                'fork': traits['fork'], 'join': traits['join'],
                'diamond': len(nodes) == 4 and len(edges) == 4 and traits['components'] == 1 and traits['fork'] and traits['join'] and not traits['cyclic'],
                'long-edge': any('n(long_edge)_' in message for message in logs) or original_skip(traits),
                'cycle': traits['nonselfCycle'], 'self-loop': traits['loop'], 'parallel': traits['parallel'],
                'disconnected': traits['components'] > 1, 'mixed': traits['loop'] and traits['parallel'] and traits['nonselfCycle']}.get(branch, False)
    if declaration == 'domain-directions':
        _, value = selector(request, 'direction')
        return (value is None or value == 'UNDEFINED') if branch == 'UNDEFINED' else options['direction'] == branch
    if declaration == 'domain-components':
        _, raw = selector(request, 'separateConnectedComponents')
        return {'separate-true': traits['components'] > 1 and options['separateConnectedComponents'] is True,
                'separate-false': traits['components'] > 1 and options['separateConnectedComponents'] is False,
                'string-false': type(raw) is str and raw.lower() == 'false',
                'zero-spacing': traits['components'] > 1 and options['spacing.componentComponent'] == 0,
                'unequal-eight-isolates': len(nodes) == 8 and not edges and len({(n['width'], n['height']) for n in nodes}) > 1}.get(branch, False)
    if declaration == 'domain-child-padding':
        values = [node.get('layoutOptions', {}).get(key) for node in nodes for key in ('elk.padding', P+'padding')
                  if key in node.get('layoutOptions', {})]
        if not values: return False
        if branch == 'four-side-string': return all(type(value) is str for value in values)
        if branch == 'zero': return any(all(float(item.split('=')[1]) == 0 for item in value.strip('[]').split(',')) for value in values)
        if branch == 'asymmetric': return any(len({float(item.split('=')[1]) for item in value.strip('[]').split(',')}) > 1 for value in values)
    if declaration == 'diagnostic-flags':
        if branch == 'omitted': return 'logging' not in arguments and 'measureExecutionTime' not in arguments
        pairs = {'false-false': (False, False), 'true-false': (True, False), 'false-true': (False, True), 'true-true': (True, True)}
        return branch in pairs and (logging, timing) == pairs[branch] and ('logging' in result) == (logging or timing)
    if declaration == 'diagnostic-root-cleanup':
        return {'absent': 'logging' not in graph, 'null': 'logging' in graph and graph['logging'] is None,
                'business-object': type(graph.get('logging')) is dict,
                'disabled-deletes-root-logging': 'logging' in graph and not logging and not timing and 'logging' not in result,
                'enabled-rebuilds-root-logging': 'logging' in graph and (logging or timing) and bool(flat) and not equal(graph['logging'], tree),
                'nested-node-edge-business-logging-preserved': any('logging' in n for n in nodes) and any('logging' in e for e in edges)
                    and all(equal(before.get('logging'), after.get('logging')) for before, after in zip(nodes+edges, result.get('children',[])+result.get('edges',[])))
                    and equal(graph.get('business'), result.get('business')),
                'root-business-executionTime-preserved': 'executionTime' in graph and equal(graph['executionTime'], result.get('executionTime'))}.get(branch, False)
    if declaration == 'diagnostic-tree':
        if not flat: return False
        names = [node['name'] for node in flat]
        return {'empty-root-only': not nodes and names == ['Recursive Graph Layout'],
                'single-component-no-wrapper': bool(nodes) and traits['components'] == 1 and 'Layered layout' in names and 'Component Layout' not in names,
                'separated-component-wrappers': traits['components'] > 1 and options['separateConnectedComponents'] and names.count('Component Layout') == traits['components'],
                'combined-components-no-wrapper': traits['components'] > 1 and not options['separateConnectedComponents'] and 'Component Layout' not in names,
                'simplex-per-private-component': traits['components'] > 1 and not options['separateConnectedComponents'] and names.count('Network simplex') == traits['components'],
                'self-loop-extra-phases': traits['loop'] and 'Self-Loop pre-processing' in names and 'Self-Loop post-processing' in names,
                'nonright-pre-post': options['direction'] != 'RIGHT' and 'Graph transformation (TO_INPUT_DIRECTION)' in names and 'Graph transformation (TO_INTERNAL_LTR)' in names,
                'duplicate-crossing-phase-order': any(node.get('children') and [c['name'] for c in node['children']].count('Minimize Crossings BARYCENTER') == 1 and
                    [c['name'] for c in node['children']].count('Minimize Crossings TWO_SIDED_GREEDY_SWITCH') == 1 for node in flat)}.get(branch, False)
    if declaration == 'diagnostic-live-text':
        checks = {'module-count': lambda: any(x.startswith('ELK Layered uses the following ') for x in logs),
                  'module-slot-order': lambda: any('Slot 00: org.eclipse.elk.alg.layered.' in x for x in logs),
                  'four-BK-layout-sizes': lambda: all(any(x.startswith(name+' size is ') for x in logs) for name in ('RIGHTDOWN','RIGHTUP','LEFTDOWN','LEFTUP')),
                  'first-invalid-pair': lambda: any(x.startswith('bk node placement breaks on ') for x in logs),
                  'feasibility': lambda: any(' is feasible: ' in x for x in logs),
                  'chosen-layout': lambda: any(x.startswith('Chosen node placement: ') for x in logs),
                  'blocks': lambda: any(x.startswith('Blocks: {') for x in logs),
                  'classes': lambda: any(x.startswith('Classes: {') for x in logs),
                  'marked-first-successful-add': lambda: any(x.startswith('Marked edges: [') and x != 'Marked edges: []' for x in logs)}
        return checks[branch]()
    if declaration == 'diagnostic-identities':
        return {'original-root-node-id': any('n_'+str(graph['id'])+'.'+str(n['id']) in x for n in nodes for x in logs),
                'long-edge-dummy-layer-index': any('n(long_edge)_' in x for x in logs),
                'port-local-index': any(re.search(r' \d+\[n(?:\(long_edge\))?_.+?\] -> \d+\[n(?:\(long_edge\))?_', x) for x in logs if x.startswith('Marked edges: [')),
                'edge-origin-id': any('e_'+str(graph['id'])+'.'+str(e['id'])+' ' in x for e in edges for x in logs),
                'no-address-or-trace-id': bool(logs) and all('traceId' not in x and 'object at 0x' not in x for x in logs)}.get(branch, False)
    if declaration == 'input-preservation':
        if branch in ('request', 'constructor', 'arguments'): return True
        if branch == 'business-types': return 'business' in graph and equal(graph['business'], result.get('business'))
        if branch == 'original-identities': return [n['id'] for n in nodes] == [n['id'] for n in result.get('children',[])] and [e['id'] for e in edges] == [e['id'] for e in result.get('edges',[])]
        if branch == 'independent-output': return not equal(graph, result) and unchanged(observation, request)
    return False


def api_match(declaration, branch, observation, root):
    data = observation['lifecycle']; metadata = data['metadata']; errors = data['publicErrors']
    default = metadata['default']; closing = data['fifoRecoveryClose']; actions = data['resourceActions']
    if declaration == 'option-scope' and branch == 'unselected-constructor-not-parsed':
        from validate_e08_api import NATIVE_REQUEST
        request = load(Path(root)/NATIVE_REQUEST)
        return geometry(request['smallRequest'], {'outcome':'returned','result':errors['emptyCallReplacesBadConstructor']}, request['smallGeometryPolicy'])['passed']
    if declaration == 'api-registry':
        if branch == 'default-layered': return [r['id'] for r in default['algorithms']] == [P+'layered']
        if branch == 'empty-metadata-only': return metadata['algorithmsEmpty']['algorithms'] == [] and metadata['algorithmsEmpty']['categories'] == [] and len(metadata['algorithmsEmpty']['options']) == 9 and metadata['emptyLayoutError']['code'] == 'ALGORITHM_NOT_REGISTERED'
    if declaration == 'api-metadata':
        counts = {'algorithms-1': ('algorithms',1), 'options-9': ('options',9), 'categories-1': ('categories',1)}
        if branch in counts:
            key, count = counts[branch]; return len(default[key]) == count
        if branch == 'fresh-independent-values': return all(equal(default[key], default[key+'AfterMutation']) for key in ('algorithms','options','categories')) and equal(metadata['defaultAfterEmpty'], default['algorithms'])
        if branch == 'full-reference-12-243-8-retained': return [len(load(Path(root)/('references/metadata/'+key+'.json'))) for key in ('algorithms','options','categories')] == [12,243,8] and len(default['algorithms']) == 1
    if declaration == 'api-algorithm-errors':
        return {'unknown': errors['constructorUnknown']['code'] == 'UNKNOWN_ALGORITHM',
                'known-unimplemented': errors['constructorUnsupported']['code'] == 'UNSUPPORTED_ALGORITHM',
                'invalid-type': errors['constructorContainer']['code'] == 'INVALID_OPTION_VALUE',
                'selected-global-before-local': errors['globalUnknownLocalValid']['code'] == 'UNKNOWN_ALGORITHM' and errors['globalUnsupportedLocalValid']['code'] == 'UNSUPPORTED_ALGORITHM',
                'empty-call-replaces-default': type(errors['emptyCallReplacesBadConstructor']) is dict and len(errors['emptyCallReplacesBadConstructor'].get('children',[])) > 0}.get(branch, False)
    if declaration == 'api-closed':
        if branch == 'three-metadata-queries': return len(metadata['closedErrors']) == 3 and all(e['code'] == 'RESOURCE_CLOSED' for e in metadata['closedErrors'].values())
        if branch == 'layout': return closing['closedError']['code'] == 'RESOURCE_CLOSED' and closing['closed']['state'] == 'closed'
        # A published nonempty trace followed by close needs the dedicated probe.
        return False
    if declaration == 'api-worker-options': return branch == 'workerFactory-rejected' and errors['constructorWorker']['code'] == 'UNSUPPORTED_WORKER' and errors['constructorWorker']['path'] == '/constructor/workerFactory'
    if declaration == 'lifecycle-fifo':
        jobs = closing['fifo']['jobs']
        if branch == 'single-running-slot': return len(jobs) == 2 and jobs[0]['finished_at'] <= jobs[1]['started_at']
        if branch == 'queue-count-includes-running': return data['queue']['queued']['pending'] == 2 and len(data['queue']['queued']['queued']) == 1
        if branch == 'independent-overlapping-instances': return len({p['pid'] for p in data['overlapAndLoop']['overlap']['osPids']}) == 2 and data['overlapAndLoop']['overlap']['tasksDone'] == [False,False]
    if declaration == 'lifecycle-cancel-close':
        if branch == 'queued-cancel-no-spawn':
            queued = data['queue']; job = next(j for j in queued['afterFirstReturn']['jobs'] if j['job_id'] == queued['queuedJobId'])
            return job['state'] == 'cancelled' and job['pid'] is None and job['started_at'] is None and job['reaped'] is True
        if branch == 'running-cancel-reaped': return data['cpuCancel']['pidBeforeCancel']['pid'] == data['cpuCancel']['pidAfterCancel']['pid'] and any(j['state'] == 'cancelled' and j['reaped'] is True for j in data['cpuCancel']['afterCancel']['jobs'])
    if declaration == 'lifecycle-timeout':
        if branch == 'includes-spawn': return actions['timeout']['timeoutSeconds'] == 0.001 and actions['timeout']['elapsedSeconds'] >= 0.001 and actions['timeout']['error']['code'] == 'EXECUTION_TIMEOUT'
        if branch == 'slot-recovers': return data['cpuCancel']['afterRecovery']['pending'] == 0 and type(data['cpuCancel']['recoveryResult']) is dict
    if declaration == 'lifecycle-loop-trace':
        loops = data['overlapAndLoop']['crossLoop']
        return {'idle-cross-loop-allowed': type(loops['otherLoopResult']) is dict and type(loops['originalLoopResult']) is dict,
                'active-cross-loop-rejected': loops['running']['pending'] > 0 and loops['error']['code'] == 'EVENT_LOOP_CONFLICT',
                'latest-submission-trace-only': data['queue']['lastTrace'] == [] and bool(closing['traceAfterCallerMutation']),
                'failure-clears-trace': closing['traceAfterFailure'] == [] and closing['validationError']['code'] == 'UNKNOWN_ENDPOINT'}.get(branch, False)
    if declaration == 'lifecycle-errors':
        if branch == 'worker-crash': return actions['externalCrash']['error']['type'] == 'WorkerExecutionError' and actions['externalCrash']['osPidBefore']['pid'] == actions['externalCrash']['osPidAfter']['pid'] and actions['externalCrash']['lastTrace'] == []
        if branch == 'validation-error-fields': return closing['validationError']['type'] == 'ModelValidationError' and closing['validationError']['code'] == 'UNKNOWN_ENDPOINT' and closing['validationError']['path'] == '/edges/0/targets/0'
    return False


def primitive_match(declaration, branch, observation, root):
    p = observation['monitorPrimitives']
    if declaration == 'diagnostic-clock':
        clocks = p['clocks']
        formulas = all(type(tick) is int for c in clocks for tick in c['ticks']) and all(c['tree']['executionTime'] == float((c['ticks'][1]-c['ticks'][0])*1000)*1e-9 for c in clocks)
        if branch == 'integer-wall-ms': return p['defaultClock']['timeNs'] == [1000999999,1002000000] and p['defaultClock']['reads'] == 2 and p['defaultClock']['tree']['executionTime'] == float(((1002000000//1000000)-(1000999999//1000000))*1000)*1e-9
        if branch in ('delta-times-1000-times-1e-9','float-multiplication-order'): return formulas and any(c['tree']['executionTime'] == float(7000)*1e-9 for c in clocks)
        if branch == 'zero-delta': return any(c['ticks'][0] == c['ticks'][1] and c['tree']['executionTime'] == 0 for c in clocks)
        if branch == 'negative-delta-unclamped': return any(c['ticks'][1] < c['ticks'][0] and c['tree']['executionTime'] < 0 for c in clocks)
        if branch == 'disabled-no-clock-reads': return len(p['disabledClocks']) == 2 and all(c['reads'] == [] for c in p['disabledClocks'])
        if branch == 'per-tree-isolation': return p['isolation']['one']['executionTime'] == float(2000)*1e-9 and p['isolation']['two']['executionTime'] == float(7000)*1e-9
    if declaration == 'diagnostic-monitor-state':
        state = p['state']
        return {'repeat-begin-returns-false': state['firstBegin'] is True and state['repeatBegin'] is False and state['repeatDoneAfter']['name'] == 'original',
                'closed-begin-errors': state['closedBeginError'] == {'name':'RuntimeError','message':'The task is already done.'},
                'closed-subtask-null': state['closedSubTask'] is None and state['runningAfterDone'] is False,
                'done-before-begin-errors': state['doneBeforeBeginError'] == {'name':'RuntimeError','message':'The task has not begun yet.'},
                'repeat-done-idempotent': equal(state['repeatDoneBefore'], state['repeatDoneAfter'])}.get(branch, False)
    if declaration == 'diagnostic-collect':
        before = p['collect']['before']; after = p['collect']['after']; flat = list(monitors(before))
        if branch == 'name-always': return bool(flat) and all(type(c.get('name')) is str for c in flat)
        if branch == 'logs-only-when-enabled-nonempty': return all('logs' not in c or bool(c['logs']) for c in flat) and all('logs' not in c for c in monitors(p['disabledClocks'][0]['tree'])) and p['disabledClocks'][1]['tree']['children'][0]['logs'] == ['actual message']
        if branch == 'time-only-when-enabled': return all('executionTime' not in c for c in flat) and 'executionTime' in p['isolation']['one']
        if branch == 'children-only-when-nonempty': return 'children' not in p['isolation']['one'] and all('children' not in c or bool(c['children']) for c in flat)
        if branch == 'insertion-order': return [c['name'] for c in before['children']] == ['first','second'] and before['children'][0]['logs'] == ['one','two']
        if branch == 'fresh-independent-tree': return equal(before, after) and not equal(p['collect']['mutatedReturn'], after)
    if declaration == 'diagnostic-number-adapter':
        from validate_e09_coverage import numeric_reference
        rows = observation['numberAdapter']; expected = numeric_reference(root)
        if not equal(rows, [{k:r[k] for k in ('id','bitsHex','string')} for r in expected]): return False
        pairs = [(struct.unpack('>d',bytes.fromhex(r['bitsHex']))[0],r['string']) for r in rows]
        if branch == 'integer-rendering': return any(v == 20 and s == '20' for v,s in pairs)
        if branch == 'negative-zero': return any(r['bitsHex'] == '8000000000000000' and r['string'] == '0' for r in rows)
        if branch == 'decimal-1e-6': return any(v == 1e-6 and s == '0.000001' for v,s in pairs)
        if branch == 'scientific-1e-7': return any(v == 1e-7 and s == '1e-7' for v,s in pairs)
        if branch == 'exponent-sign-and-zero': return any('e+' in s for _,s in pairs) and any('e-' in s and 'e-0' not in s for _,s in pairs)
        if branch == 'shortest-roundtrip': return len(pairs) >= 298 and all(float(s) == v for v,s in pairs)
        if branch == 'tiny-finite': return any(0 < abs(v) < 1e-300 for v,_ in pairs)
    if declaration == 'diagnostic-boundaries':
        plain, traced = observation['kernelBoundaries']; events = plain['events']
        imported = next(e for e in events if e['role'] == 'provider-import'); exported = next(e for e in events if e['role'] == 'provider-transfer')
        if branch == 'recursive-includes-provider-import': return imported['rootRunning'] is True
        if branch == 'layered-excludes-provider-import': return imported['layeredPresent'] is False
        if branch == 'layered-excludes-transfer': return exported['layeredRunning'] is False
        if branch == 'recursive-includes-transfer': return exported['rootRunning'] is True
        if branch == 'snapshot-work-not-used-to-build-tree': return plain['snapshotCalls'] == 0 and traced['snapshotCalls'] == 38 and len(traced['trace']) == 19 and plain['trace'] == [] and equal(plain['tree'],traced['tree']) and equal(plain['result'],traced['result'])
    return False


def lifecycle_match(declaration, branch, value):
    if declaration == 'api-registry':
        aliases = value['registry']['aliases']
        wanted = [['layered'],[P+'layered'],['layered',P+'layered','layered']]
        if branch == 'explicit-layered': return aliases[0]['constructor']['algorithms'] == wanted[0] and aliases[1]['constructor']['algorithms'] == wanted[1] and all([a['id'] for a in row['queries']['algorithms']] == [P+'layered'] for row in aliases[:2])
        if branch == 'canonical-alias-dedup': return aliases[2]['constructor']['algorithms'] == wanted[2] and [a['id'] for a in aliases[2]['queries']['algorithms']] == [P+'layered'] and all(row['constructorBeforeSha256'] == row['constructorAfterSha256'] for row in aliases)
    if declaration == 'api-worker-options': return value['registry']['workerUrlError']['code'] == 'UNSUPPORTED_WORKER' and value['registry']['workerUrlError']['path'] == '/constructor/workerUrl'
    if declaration == 'api-closed':
        trace = value['registry']['closedTrace']; return bool(trace['before']) and trace['after'] == [] and trace['closedSnapshot']['state'] == 'closed'
    if declaration == 'lifecycle-fifo':
        capacity = value['capacity']; return [r['maxPending'] for r in capacity['valid']] == [1,64] and [r['value'] for r in capacity['invalid']] == [0,65,True] and all(r['error']['code'] == 'INVALID_OPTION_VALUE' for r in capacity['invalid'])
    if declaration == 'lifecycle-timeout':
        if branch == 'slot-recovers':
            running = value['runningTimeout']
            return running['afterRecovery']['pending'] == 0 and all(job['reaped'] is True for job in running['afterRecovery']['jobs']) and type(running['recoveryResult']) is dict and bool(running['recoveryTrace'])
        if branch == 'includes-queue':
            queued = value['queuedTimeout']; return queued['fixture'] == 'private-busy-host-control' and queued['queuedError']['code'] == 'EXECUTION_TIMEOUT' and any(j['pid'] is None and j['started_at'] is None and j['state'] == 'failed' and j['reaped'] is True for j in queued['afterQueuedTimeout']['jobs'])
        if branch == 'running-killed':
            running = value['runningTimeout']; attempt = running['attempts'][running['qualifiedAttempt']]
            events = attempt['phaseEvents']; return len(events) >= 2 and events[-1]['snapshot']['jobs'][-1]['progress']['process_time'] > events[0]['snapshot']['jobs'][-1]['progress']['process_time'] and attempt['error']['code'] == 'EXECUTION_TIMEOUT' and attempt['pidBefore']['pid'] == attempt['pidAfter']['pid'] and all(j['reaped'] is True for j in attempt['after']['jobs']) and bool(running['recoveryTrace'])
    if declaration == 'lifecycle-cancel-close':
        closing = value['crossThreadClose']
        if branch == 'close-running-and-queued': return closing['runningAndQueued']['pending'] == 2 and len(closing['runningAndQueued']['queued']) == 1 and len(closing['errors']) == 2 and all(e['code'] == 'RESOURCE_CLOSED' for e in closing['errors']) and closing['afterFirstClose']['pending'] == 0
        if branch == 'close-idempotent': return closing['threadCall']['returnValue'] is None and closing['secondReturnValue'] is None and closing['afterFirstClose']['state'] == 'closed' and closing['afterSecondClose']['state'] == 'closed'
        if branch == 'close-from-other-thread': return closing['threadCall']['threadId'] != closing['mainThreadId'] and closing['threadCall']['startedAt'] <= closing['threadCall']['finishedAt'] and closing['pidBefore']['pid'] == closing['pidAfter']['pid'] and closing['afterFirstClose']['state'] == 'closed'
    if declaration == 'lifecycle-errors':
        faults = value['faults']
        if branch == 'protocol-error': return all(faults[key]['error']['code'] == 'WORKER_PROTOCOL_ERROR' and bool(faults[key]['sentMessages']) for key in ('unknownKind','wrongJob','badBody'))
        if branch == 'internal-import-error': return faults['internalImport']['error']['type'] == 'WorkerExecutionError' and faults['internalImport']['error']['code'] == 'WORKER_EXECUTION_FAILED' and bool(faults['internalImport']['recoveryTrace'])
        if branch == 'spawn-failure': return faults['spawnFailure']['error']['type'] == 'WorkerExecutionError' and bool(faults['spawnFailure']['recoveryTrace'])
    return False


def raw_layout_records(receipts, root):
    records = []
    geometry_receipt = receipts.get('geometry')
    if geometry_receipt:
        observations = {h: embedded_json(base64.b64decode(raw, validate=True)) for h,raw in geometry_receipt['observationBytesBase64'].items()}
        for suite_name, planned in geometry_receipt['plan']['suites'].items():
            for definition, case in zip(planned['cases'], geometry_receipt['suites'][suite_name]['cases']):
                request = load(Path(root)/definition['request']); captures = []
                for key in case['executionReferences']['candidate']:
                    fingerprint = geometry_receipt['objects'][key]['observationSha256']
                    captures.append((observations[fingerprint],fingerprint))
                records.append({'role':'geometry','id':suite_name+'/'+case['id'],'request':request,'captures':captures})
    coverage = receipts.get('newcoverage')
    if coverage:
        for case in coverage.get('cases', []):
            raw = base64.b64decode(case['requestBytesBase64'],validate=True)
            records.append({'role':'newcoverage','id':case['definition']['id'],'request':embedded_json(raw),
                            'captures':[decode(capture) for capture in case['captures']]})
    return records


def raw_probe_records(receipt, field=None):
    if not receipt: return []
    value = receipt.get(field) if field else receipt
    if not value: return []
    return [decode(capture) for capture in value['captures']]


def public_matches(declaration, branch, value, root):
    definitions = load(Path(root)/'tests/fixtures/suites/E09/host-checks.json')['publicCases']
    by_id = {row['id']:row for row in value['publicCases']}
    wanted = PUBLIC_IDS.get((declaration,branch))
    if wanted is not None:
        if not set(wanted) <= by_id.keys(): return False
        selected = [next(d for d in definitions if d['id'] == name) for name in wanted]
    else:
        selected = []
        option = declaration.removeprefix('option-')
        for definition in definitions:
            expected = definition['expected']; error = expected.get('error', {})
            if expected['outcome'] != 'threw': continue
            if declaration == 'option-scope':
                matches = error.get('code') == 'AMBIGUOUS_OPTION'
            else:
                matches = error.get('name') == 'OptionValidationError' and error.get('code') == 'INVALID_OPTION_VALUE' and error.get('path','').endswith(('/elk.'+option,'/'+P+option))
            if matches: selected.append(definition)
        if not selected: return False
    for definition in selected:
        actual = by_id[definition['id']]
        if not unchanged(actual, definition['request']) or actual['outcome'] != definition['expected']['outcome']: return False
        if actual['outcome'] == 'threw':
            if not equal(actual['error'],definition['expected']['error']): return False
        elif not geometry(definition['request'],{'outcome':'returned','result':actual['result']},definition['geometry'])['passed']:
            return False
    return True


def _lifecycle_validator(root):
    path = Path(root)/'tools/reference/e09_host_lifecycle_probe.py'
    spec = importlib.util.spec_from_file_location('_e09_branch_lifecycle_validation',path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.validate_lifecycle_observation


def validate_branch_evidence(mapping, receipts, root=ROOT):
    """Pure raw-observation predicates after root's complete receipt validation.

    This function does not assert command/history authentication by itself.
    Root must validate geometry/API/newcoverage receipts before invoking it.
    A standalone CLI below performs those prerequisite gates explicitly.
    """
    root = Path(root); pending = []; verified = []; errors = []; required_mapping = None
    try:
        required_mapping = expected_mapping(root)
        exact(mapping, required_mapping, 'Frozen219 branch mapping/predicate denominator differs')
        if all(receipts.get(role) for role in ('geometry','api','newcoverage')):
            exact(receipts['geometry']['apiRuntime'], receipts['api'], 'API mapping does not point at geometry apiRuntime')
            for role in ('api','newcoverage'):
                exact(receipts[role]['installed'], receipts['geometry']['installed'], 'Branch roles use different installed wheel identities')
            require(receipts['api']['candidatePython'] == receipts['newcoverage']['candidatePython'], 'Branch candidate interpreters differ')
        layouts = raw_layout_records(receipts,root)
        api = raw_probe_records(receipts.get('api'))
        coverage = receipts.get('newcoverage')
        host = raw_probe_records(coverage,'hostProbe'); lifecycle = raw_probe_records(coverage,'lifecycleProbe')
        # Recompute the existing raw fact validators. Their input PASS flags are
        # never read, and this mapper still checks each target fact below.
        if api:
            from validate_e08_api import validate_native_observation
            for value,_ in api: validate_native_observation(value,receipts['api']['installed'],root)
        if host:
            from validate_e09_coverage import validate_host_observation
            request = load(root/'tests/fixtures/suites/E09/host-checks.json')
            for value,_ in host: validate_host_observation(value,request,root)
        if lifecycle:
            validator = _lifecycle_validator(root)
            for value,_ in lifecycle: validator(value)
        for row in mapping['rows']:
            declaration, branch = row['declarationId'],row['branch']; evidence = row['evidence']; kind = evidence['kind']; witnesses = []
            try:
                if kind == 'layout-observation':
                    for record in layouts:
                        if record['role'] in evidence['roles'] and len(record['captures']) >= 3 and all(layout_match(declaration,branch,record['request'],value) for value,_ in record['captures']):
                            witnesses.append({'role':record['role'],'caseId':record['id'],'observationSha256':[h for _,h in record['captures']],
                                              'fields':evidence['fields'],'assertion':evidence['assertion']})
                            break
                else:
                    actual = api if kind == 'api-observation' else lifecycle if kind == 'lifecycle-probe' else host
                    def matches(value):
                        if kind == 'api-observation': return api_match(declaration,branch,value,root)
                        if kind == 'lifecycle-probe': return lifecycle_match(declaration,branch,value)
                        if kind in ('host-public','host-public-selector'): return public_matches(declaration,branch,value,root)
                        return primitive_match(declaration,branch,value,root)
                    if len(actual) >= 3 and all(matches(value) for value,_ in actual):
                        witnesses.append({'role':evidence['role'],'kind':kind,'pointer':evidence.get('pointer','/publicCases'),
                                          'publicCaseIds':evidence.get('publicCaseIds'), 'observationSha256':[h for _,h in actual]})
            except (ValueError,KeyError,TypeError,IndexError,OverflowError,StopIteration) as error:
                row_error = str(error)
            else:
                row_error = 'No actual observation satisfies the frozen branch predicate'
            result = {'declarationId':declaration,'branch':branch}
            if witnesses: verified.append({**result,'witnesses':witnesses})
            else: pending.append({**result,'reason':row_error,'requiredEvidence':evidence})
        if not all(receipts.get(role) for role in ('geometry','api','newcoverage')):
            errors.append('All three current portable receipt roles are required')
    except (ValueError,OSError,KeyError,TypeError,AttributeError,IndexError,UnicodeError,ImportError,OverflowError) as error:
        errors.append(str(error))
        seen = {(row['declarationId'],row['branch']) for row in verified+pending}
        pending.extend({'declarationId':row['declarationId'],'branch':row['branch'],'reason':'Evidence prerequisite failed'}
                       for row in (required_mapping or mapping).get('rows',[]) if (row['declarationId'],row['branch']) not in seen)
    return {'schema':'py-elk-e09-branch-evidence-validation/v1','passed':not errors and not pending and len(verified)==219,
            'status':'E09_BRANCH_EVIDENCE_VALIDATED' if not errors and not pending and len(verified)==219 else 'PENDING',
            'errors':errors,'requiredBranchCount':219,'verifiedBranchCount':len(verified),'pendingBranchCount':len(pending),
            'verified':verified,'pending':pending,'runtimeReexecuted':False,'prerequisiteReceiptValidationRequired':True,
            'historicalExecutionAuthenticated':False,'wholeAlgorithmAccepted':False,'packagePublished':False}


def check_geometry_source(root=ROOT):
    """Offline G01 proof with original independent review and immutable facts."""
    root = Path(root)
    try:
        proof = load(root/'references/e09-geometry-premise.json'); facts = proof['facts']
        fingerprint = hashlib.sha256(canonical(facts).encode()).hexdigest()
        require(proof['schema'] == 'py-elk-e09-geometry-source-proof/v1' and proof['sourceApproved'] is True and
                fingerprint == 'efdb4249ead04f837c4bf2d2cdcfd73bb9035edf8e3d7a42137b039a145f80bc', 'Geometry fixed source facts/approval differ')
        require(proof['pythonAlgorithmsVerified'] == 0 and type(proof['pythonAlgorithmsVerified']) is int and proof['packagePublished'] is False,
                'Geometry proof promotes full algorithm/release')
        record = proof['independentReview']
        require(record['path'] == 'references/e09-source-reviews/Geometry-by-V.json' and
                record['sha256'] == '06ff744141375098f39f3d433109c2182957589733bd932c924c84ac6c1b4bd3', 'Geometry independent review seal differs')
        raw = (root/record['path']).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == record['sha256'], 'Geometry original review bytes differ')
        review = embedded_json(raw)
        require(review['accepted'] is True and review['blockers'] == [] and
                review['factsSha256'] == fingerprint and review['lemmaId'] == facts['lemmaId'] and
                review['acceptedComponentIds'] == [c['componentId'] for c in facts['components']], 'Geometry independent scope/review incomplete')
        original = base64.b64decode(record['reviewedProposalBytesBase64'],validate=True)
        require(hashlib.sha256(original).hexdigest() == review['proposalSha256'] and
                equal(embedded_json(original)['facts'],facts), 'Geometry original reviewed proposal differs')
        require(len(facts['components']) == 11, 'Geometry source component denominator differs')
        for component in facts['components']:
            body = base64.b64decode(component['sourceBytesBase64'],validate=True)
            require(hashlib.sha256(body).hexdigest() == component['spanSha256'] and b'\r' not in body and body.endswith(b'\n') and
                    len(body.decode().splitlines()) == component['endLine']-component['startLine']+1, 'Geometry source span bytes/range differ')
        for name, expected in facts['inheritedSources'].items():
            require(hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, 'Geometry inherited source facts differ')
        return {'passed':True,'errors':[],'approvedComponentCount':11,'lemmaId':facts['lemmaId'],
                'runtimeAcceptanceAssessed':False,'oldV2Changed':False,'packagePublished':False}
    except (ValueError,OSError,KeyError,TypeError,AttributeError,IndexError,UnicodeError) as error:
        return {'passed':False,'errors':[str(error)],'approvedComponentCount':0,'runtimeAcceptanceAssessed':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-map',type=Path)
    parser.add_argument('--out',type=Path)
    args = parser.parse_args()
    if args.write_map:
        from layout_checks import write
        write(args.write_map,expected_mapping()); return
    from validate_e08_runtime import validate_layout_receipt
    from validate_e09_coverage import validate_candidate_receipt
    geometry_receipt = load(ROOT/INSTALLED); coverage = load(ROOT/COVERAGE)
    validate_layout_receipt(geometry_receipt,ROOT); validate_candidate_receipt(coverage,ROOT)
    result = validate_branch_evidence(load(ROOT/MAP),{'geometry':geometry_receipt,'api':geometry_receipt['apiRuntime'],'newcoverage':coverage})
    if args.out:
        from layout_checks import write
        write(args.out,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('verified','pending')},indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
