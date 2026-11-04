"""Seven logged public requests for previously unobserved P1/P2 selections.

Pilot captures the first native call; finish captures Source once in one batch
and only the remaining six native calls. Audit reads saved bytes only.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from validate_full_layered import command_capture, sha, write

SUITE = ROOT/'tests/fixtures/suites/missing-p1-p2-runtime/cases.json'
PAIRS = (
    ('GREEDY_MODEL_ORDER', 'INTERACTIVE', 'GreedyModelOrderCycleBreaker', 'InteractiveLayerer'),
    ('INTERACTIVE', 'MIN_WIDTH', 'InteractiveCycleBreaker', 'MinWidthLayerer'),
    ('MODEL_ORDER', 'STRETCH_WIDTH', 'ModelOrderCycleBreaker', 'StretchWidthLayerer'),
    ('SCC_CONNECTIVITY', 'BF_MODEL_ORDER', 'SCConnectivity', 'BreadthFirstModelOrderLayerer'),
    ('SCC_NODE_TYPE', 'DF_MODEL_ORDER', 'SCCNodeTypeCycleBreaker', 'DepthFirstModelOrderLayerer'),
    ('DFS_NODE_ORDER', 'NETWORK_SIMPLEX', 'DFSNodeOrderCycleBreaker', 'NetworkSimplexLayerer'),
    ('BFS_NODE_ORDER', 'NETWORK_SIMPLEX', 'BFSNodeOrderCycleBreaker', 'NetworkSimplexLayerer'),
)


def load(path):
    return json.loads(Path(path).read_bytes())


def prepare():
    rows = []
    for p1, p2, class1, class2 in PAIRS:
        old = ROOT/('tests/fixtures/suites/full-native-algorithms/requests/p1-' + p1.lower() + '--p2-' + p2.lower() + '.json')
        request = load(old)
        request['layoutArguments']['logging'] = True
        identifier = 'logged-' + p1.lower() + '--' + p2.lower()
        path = SUITE.parent/'requests'/(identifier+'.json')
        write(path, request)
        rows.append({'id': identifier, 'p1': p1, 'p2': p2, 'classes': [class1, class2],
                     'request': 'requests/'+path.name, 'requestSha256': sha(path),
                     'oldRequest': old.relative_to(ROOT).as_posix(), 'oldRequestSha256': sha(old)})
    write(SUITE, {'schema': 'pyelk-missing-p1-p2-runtime/v1', 'cases': rows, 'caseCount': 7,
                  'scope': 'Only seven logged selections on the existing81 graph, not a new mathematical matrix'})


def definitions():
    suite = load(SUITE)
    for row in suite['cases']:
        path = SUITE.parent/row['request']
        if sha(path) != row['requestSha256']:
            raise ValueError('Request SHA differs')
        old = load(ROOT/row['oldRequest'])
        expected = copy.deepcopy(old)
        expected['layoutArguments']['logging'] = True
        if expected != load(path):
            raise ValueError('More than logging changed')
    return suite['cases']


def capture_native(row, output):
    return command_capture([sys.executable, '-I', str(ROOT/'scripts/validate_full_layered.py'),
                            '--capture-candidate', str(SUITE.parent/row['request']),
                            '--source', str(ROOT/'src'), '--out', str(output/'native'/(row['id']+'.json'))],
                           output/'commands'/row['id'], 20)


def logs(observation):
    tasks, messages = [], []

    def visit(value, path):
        if isinstance(value, dict):
            if isinstance(value.get('name'), str):
                tasks.append({'pointer': path+'/name', 'name': value['name']})
            for name, item in value.items():
                if name == 'logs' and isinstance(item, list):
                    messages.extend({'pointer': path+'/logs/'+str(i), 'text': text}
                                    for i, text in enumerate(item) if isinstance(text, str))
                else:
                    visit(item, path+'/'+str(name))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, path+'/'+str(index))
    visit(observation.get('result', {}).get('logging', {}), '/result/logging')
    return tasks, messages


def audit(output, rows):
    result = []
    for row in rows:
        entry = {'id': row['id'], 'p1': row['p1'], 'p2': row['p2'], 'bindings': {}}
        for role in ('source', 'native'):
            path = output/role/(row['id']+'.json')
            observation = load(path)
            if observation['requestSha256'] != row['requestSha256']:
                raise ValueError('Observation request binding differs')
            tasks, messages = logs(observation)
            entry['bindings'][role] = {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)}
            entry[role] = {'outcome': observation['outcome'], 'error': observation.get('error'),
                           'tasks': tasks, 'slotLogs': [item for item in messages if re.search(r'Slot \d+: ', item['text'])],
                           'selectedClassLogs': {name: [item for item in messages if re.search(r'Slot \d+: .*\.'+re.escape(name)+r'$', item['text'])]
                                                 for name in row['classes']}}
        entry['namedSelectionWitnessed'] = all(entry[role]['outcome'] == 'returned'
                                               and all(entry[role]['selectedClassLogs'].values())
                                               for role in ('source', 'native'))
        result.append(entry)
    write(output/'report.json', {'schema': 'pyelk-missing-p1-p2-runtime-results/v1', 'rows': result,
                                 'caseCount': len(result), 'namedSelectionWitnessed': sum(row['namedSelectionWitnessed'] for row in result),
                                 'suiteSha256': sha(SUITE), 'runnerSha256': sha(__file__),
                                 'mathematicalMatrixRerun': False})
    print(json.dumps({'caseCount': len(result), 'namedSelectionWitnessed': sum(row['namedSelectionWitnessed'] for row in result)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('prepare', 'pilot', 'finish', 'audit'), required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.stage == 'prepare':
        prepare()
        return
    if args.out is None:
        parser.error('--out required')
    output = args.out.resolve()
    rows = definitions()
    if args.stage == 'pilot':
        output.mkdir(parents=True, exist_ok=False)
        (output/'native').mkdir()
        (output/'source').mkdir()
        (output/'executed-runner.py').write_bytes(Path(__file__).read_bytes())
        (output/'executed-suite.json').write_bytes(SUITE.read_bytes())
        command = capture_native(rows[0], output)
        if command['timedOut'] or command['exitCode'] != 0:
            raise RuntimeError('Pilot capture failed; original command retained')
        observation = load(output/'native'/(rows[0]['id']+'.json'))
        print(json.dumps({'outcome': observation['outcome'], 'error': observation.get('error'), 'logs': logs(observation)}))
    elif args.stage == 'finish':
        pilot = output/'native'/(rows[0]['id']+'.json')
        if not pilot.is_file():
            raise ValueError('Actual pilot required')
        batch = output/'source-batch.json'
        write(batch, {'cases': [{'id': row['id'], 'request': str(SUITE.parent/row['request']),
                                 'output': str(output/'source'/(row['id']+'.json'))} for row in rows]})
        command = command_capture(['C:/Program Files/nodejs/node.exe', str(ROOT/'tools/reference/full_layered.cjs'),
                                   str(ROOT/'.local/npm-elkjs/package'), str(batch)], output/'source-command', 120)
        if command['timedOut'] or command['exitCode'] != 0:
            raise RuntimeError('Source batch failed; command retained')
        for row in rows[1:]:
            command = capture_native(row, output)
            if command['timedOut'] or command['exitCode'] != 0:
                raise RuntimeError('Native capture failed; command retained')
        audit(output, rows)
    else:
        audit(output, rows)


if __name__ == '__main__':
    main()
