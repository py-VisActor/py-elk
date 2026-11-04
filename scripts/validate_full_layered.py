"""Public-API Layered integration matrix; prepare first, execute after freeze.

--check-inputs reads fixture JSON only. --run explicitly enables subprocess
layout calls. Raw reference failures and every unprojected difference remain
in the output; an upstream exception is not a passing candidate comparison.
"""
from __future__ import annotations
import argparse
import asyncio
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / 'tests/fixtures/suites/full-native-layered/cases.json'
sys.path.insert(0, str(ROOT / 'scripts'))
from layout_checks import diff, load, validate_json
from iteration.check_layered_saved import project_hierarchy_shape_hashes


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


def definitions(suite=SUITE):
    suite = Path(suite).resolve()
    document = load(suite)
    if document['schema'] != 'py-elk-full-layered-suite/v1':
        raise ValueError('Unknown suite schema')
    identifiers = set()
    rows = []
    for case in document['cases']:
        if case['id'] in identifiers:
            raise ValueError('Duplicate case id')
        identifiers.add(case['id'])
        request = (suite.parent / case['request']).resolve()
        if not request.is_relative_to(suite.parent) or not request.is_file():
            raise ValueError('Missing or escaping request')
        if sha(request) != case['requestSha256']:
            raise ValueError('Fixture bytes differ: ' + case['id'])
        value = load(request)
        if value['schema'] != 'py-elk-layout-request/v1':
            raise ValueError('Invalid layout request')
        validate_json(value)
        if not isinstance(value['graph'], dict) or not isinstance(value['constructor'], dict) or not isinstance(value['layoutArguments'], dict):
            raise ValueError('Public API arguments must be mappings')
        if value['layoutArguments'].get('measureExecutionTime') is not False:
            raise ValueError('Timing is tested separately; exact layout matrix requires time=false')
        rows.append((case, request))
    if document['caseCount'] != len(rows):
        raise ValueError('Case denominator differs')
    return document, rows


async def candidate_capture(request_path, output, source):
    # This branch is entered only in the explicitly launched candidate process.
    if source is not None:
        sys.path.insert(0, str(Path(source).resolve()))
    import pyelk
    package_root = Path(pyelk.__file__).resolve().parent
    def source_hashes():
        return {path.relative_to(package_root).as_posix(): sha(path)
                for path in sorted(package_root.rglob('*.py'))}
    sources_before = source_hashes()
    request = load(request_path)
    graph, options, arguments = (copy.deepcopy(request[key]) for key in ('graph', 'constructor', 'layoutArguments'))
    observation = {
        'schema': 'py-elk-layout-observation/v1', 'requestSha256': sha(request_path),
        'engine': {'name': 'pyelk', 'version': pyelk.__version__, 'python': sys.version,
                   'executable': sys.executable, 'module': pyelk.__file__, 'pid': os.getpid(),
                   'platform': sys.platform},
        'inputBefore': copy.deepcopy(graph), 'constructorBefore': copy.deepcopy(options),
        'argumentsBefore': copy.deepcopy(arguments), 'clock': {'startMs': time.time_ns() // 1_000_000},
    }
    instance = None
    try:
        instance = pyelk.ELK(options)
        observation['result'] = await instance.layout(graph, arguments)
        observation['outcome'] = 'returned'
    except Exception as error:
        observation['outcome'] = 'threw'
        observation['error'] = {'name': type(error).__name__, 'message': str(error),
                                'code': getattr(error, 'code', None), 'path': getattr(error, 'path', None)}
        observation['diagnostics'] = {'errorStack': traceback.format_exc()}
    finally:
        observation['clock']['endMs'] = time.time_ns() // 1_000_000
        observation.update(inputAfter=graph, constructorAfter=options, argumentsAfter=arguments)
        if instance is not None:
            try:
                value = instance.terminateWorker()
                observation['termination'] = {'outcome': 'returned', 'returnKind': type(value).__name__}
            except Exception as error:
                observation['termination'] = {'outcome': 'threw', 'name': type(error).__name__, 'message': str(error)}
        else:
            observation['termination'] = {'outcome': 'notConstructed'}
    observation['engine']['sourceFilesSha256'] = sources_before
    observation['engine']['sourcesUnchanged'] = sources_before == source_hashes()
    write(output, observation)


def command_capture(argv, directory, timeout):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    env = {key: value for key, value in os.environ.items()
           if key not in {'PYTHONPATH', 'PYTHONHOME', 'NODE_PATH', 'NODE_OPTIONS'}}
    env['PATH'] = ''
    started = time.monotonic()
    timed_out = False
    with (directory / 'stdout.bin').open('xb') as stdout, (directory / 'stderr.bin').open('xb') as stderr:
        try:
            result = subprocess.run(argv, cwd=directory, env=env, stdout=stdout, stderr=stderr,
                                    timeout=timeout, check=False)
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            timed_out, exit_code = True, None
    record = {'argv': argv, 'cwd': str(directory), 'exitCode': exit_code,
              'timedOut': timed_out, 'elapsedSeconds': time.monotonic() - started,
              'environmentPolicy': {'PATH': '', 'removed': ['PYTHONPATH', 'PYTHONHOME', 'NODE_PATH', 'NODE_OPTIONS']},
              'stdoutSha256': sha(directory / 'stdout.bin'), 'stderrSha256': sha(directory / 'stderr.bin')}
    write(directory / 'command.json', record)
    return record


def compare_observations(request_path, original, candidate):
    request = load(request_path)
    # Preserve independent original mutation behavior. Candidate input copying
    # is a host-policy check, not a claim that elkjs leaves its graph untouched.
    policy = {key: diff(request[key], candidate[field], tolerant=False)
              for key, field in (('graph', 'inputAfter'), ('constructor', 'constructorAfter'),
                                 ('layoutArguments', 'argumentsAfter'))}
    result = {'referenceOutcome': original['outcome'], 'candidateOutcome': candidate['outcome'],
              'candidateInputPolicy': policy, 'sourceInputAfter': original.get('inputAfter'),
              'referenceError': original.get('error'), 'candidateError': candidate.get('error'),
              'rawStrict': None, 'comparison': None, 'adaptations': [], 'violations': [],
              'passed': False}
    if original['requestSha256'] != sha(request_path) or candidate['requestSha256'] != sha(request_path):
        raise ValueError('Observation request binding differs')
    if original['outcome'] != 'returned':
        result['status'] = 'reference-error-requires-review'
        return result
    if candidate['outcome'] != 'returned':
        result['status'] = 'candidate-error'
        return result
    result['rawStrict'] = diff(original['result'], candidate['result'], tolerant=False)
    projected = copy.deepcopy(original['result'])
    result['hierarchyContextsVisited'] = project_hierarchy_shape_hashes(
        request['graph'], projected, candidate['result'],
        adaptations=result['adaptations'], violations=result['violations'])
    result['projectedStrict'] = diff(projected, candidate['result'], tolerant=False)
    # The shared comparator's established geometric paths start at /result.
    # Keep both exact views above; tolerance applies only to named coordinate
    # fields, never options, business numbers, IDs or log text.
    result['comparison'] = diff({'result': projected}, {'result': candidate['result']}, tolerant=True)
    result['comparisonRule'] = 'Existing geometry paths only: absolute1e-6/relative1e-9; other JSON exact'
    result['projectionRule'] = 'GWT-SHAPE-HASH-HIERARCHY-01 (ADR0011)'
    result['passed'] = (result['comparison']['passed'] and not result['violations']
                        and all(row['passed'] for row in policy.values())
                        and candidate['engine'].get('sourcesUnchanged') is True
                        and candidate.get('termination', {}).get('outcome') == 'returned')
    result['status'] = 'matched' if result['passed'] else 'different'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, default=SUITE)
    parser.add_argument('--check-inputs', action='store_true')
    parser.add_argument('--run', action='store_true', help='Explicitly execute layouts after the global freeze')
    parser.add_argument('--case', action='append', default=[])
    parser.add_argument('--out', type=Path)
    parser.add_argument('--node', default='node')
    parser.add_argument('--package', type=Path, default=ROOT / '.local/npm-elkjs/package')
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--source', type=Path, help='Explicit candidate source directory; omit for installed package')
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--capture-candidate', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.capture_candidate is not None:
        if args.out is None:
            parser.error('--out is required for capture')
        asyncio.run(candidate_capture(args.capture_candidate.resolve(), args.out.resolve(), args.source))
        return 0
    document, rows = definitions(args.suite)
    requested = set(args.case)
    if requested - {case['id'] for case, _ in rows}:
        parser.error('Unknown case id')
    if requested:
        rows = [(case, request) for case, request in rows if case['id'] in requested]
    if not args.run:
        print(json.dumps({'inputsValid': True, 'caseCount': len(rows), 'layoutExecutions': 0,
                          'features': sorted({feature for case, _ in rows for feature in case['features']})}))
        return 0
    if args.out is None:
        parser.error('--run requires --out')
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    collector = ROOT / 'tools/reference/full_layered.cjs'
    dependencies = {'runner': sha(__file__), 'referenceCollector': sha(collector),
                    'suite': sha(args.suite), 'comparison': sha(ROOT / 'scripts/layout_checks.py'),
                    'projection': sha(ROOT / 'scripts/iteration/check_layered_saved.py')}
    summaries = []
    batch = []
    for case, request in rows:
        directory = output / case['id']
        directory.mkdir()
        batch.append({'id':case['id'], 'request':str(request), 'output':str(directory / 'reference.json')})
    manifest = output / 'reference-batch.json'
    write(manifest, {'cases':batch})
    node = os.path.abspath(args.node) if Path(args.node).is_file() else shutil.which(args.node)
    if node is None:
        parser.error('Node executable not found')
    reference_command = command_capture([node, str(collector), str(args.package.resolve()), str(manifest)],
                                        output / 'reference-command', args.timeout * max(1, len(rows)))
    for case, request in rows:
        directory = output / case['id']
        original = directory / 'reference.json'
        candidate = directory / 'candidate.json'
        commands = {'reference': reference_command}
        argv = [os.path.abspath(args.python), '-I', str(Path(__file__).resolve()),
                '--capture-candidate', str(request), '--out', str(candidate)]
        if args.source is not None:
            argv.extend(['--source', str(args.source.resolve())])
        commands['candidate'] = command_capture(argv, directory / 'candidate-command', args.timeout)
        if any(row['timedOut'] or row['exitCode'] != 0 for row in commands.values()) or not original.exists() or not candidate.exists():
            comparison = {'passed': False, 'status': 'capture-failed', 'commands': commands}
        else:
            comparison = compare_observations(request, load(original), load(candidate))
        write(directory / 'comparison.json', comparison)
        summaries.append({'id': case['id'], 'features': case['features'],
                          'status': comparison['status'], 'passed': comparison['passed'],
                          'requestSha256': sha(request),
                          'referenceSha256': sha(original) if original.exists() else None,
                          'candidateSha256': sha(candidate) if candidate.exists() else None})
    current = {'runner': sha(__file__), 'referenceCollector': sha(collector),
               'suite': sha(args.suite), 'comparison': sha(ROOT / 'scripts/layout_checks.py'),
               'projection': sha(ROOT / 'scripts/iteration/check_layered_saved.py')}
    report = {'schema': 'py-elk-full-layered-report/v1', 'passed': all(row['passed'] for row in summaries)
              and dependencies == current, 'executionDependencies': dependencies,
              'dependenciesUnchanged': dependencies == current, 'cases': summaries,
              'referenceErrors': [row['id'] for row in summaries if row['status'] == 'reference-error-requires-review'],
              'caseCount': len(summaries), 'wholeAlgorithmAccepted': False}
    write(output / 'report.json', report)
    print(json.dumps({'passed': report['passed'], 'caseCount': len(summaries), 'referenceErrors': report['referenceErrors']}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
