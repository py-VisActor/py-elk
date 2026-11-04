"""Small public-API option effects, with reusable immutable stock captures.

Input occurrence, selected runtime branch and observable output effect are
reported separately. A full-output match alone never establishes option effect.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from layout_checks import diff, load
from validate_full_layered import command_capture, compare_observations, sha, write

SUITE = ROOT / 'tests/fixtures/suites/full-option-effects/cases.json'


def pointer(value, path):
    if not path.startswith('/'):
        raise ValueError('Expected an absolute JSON pointer')
    for part in path[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def task_names(observation):
    result = []
    stack = [observation.get('result', {}).get('logging', {}).get('tree', {})]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            if isinstance(value.get('name'), str):
                result.append(value['name'])
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    return result


def definitions(path):
    suite = load(path)
    if suite['schema'] != 'py-elk-option-effects/v1':
        raise ValueError('Unknown effects suite')
    rows = []
    identifiers = set()
    for case in suite['cases']:
        if case['id'] in identifiers:
            raise ValueError('Duplicate case ID')
        identifiers.add(case['id'])
        request = (path.parent / case['request']).resolve()
        if not request.is_relative_to(path.parent.resolve()) or sha(request) != case['requestSha256']:
            raise ValueError('Missing, escaping or changed request')
        value = load(request)
        if value['schema'] != 'py-elk-layout-request/v1':
            raise ValueError('Expected the shared public API request format')
        for proof in case.get('proofs', []):
            if not proof['optionId'].startswith('org.eclipse.elk.'):
                raise ValueError('Use the real canonical option ID')
            if proof['kind'] not in ('equals', 'changed', 'task-present', 'task-absent'):
                raise ValueError('Unsupported proof kind')
            if proof['kind'] in ('equals', 'changed'):
                paths = proof.get('pointers', [proof.get('pointer')])
                if not paths or any(not isinstance(p, str) or not p.startswith('/result/')
                    or '/layoutOptions/' in p or '/business/' in p or '/logging/' in p for p in paths):
                    raise ValueError('Effect proof must inspect computed result state, not echoed input/logs')
        rows.append((case, request))
    for case, _ in rows:
        if case.get('baseline') is not None and case['baseline'] not in identifiers:
            raise ValueError('Missing baseline case')
    return rows


def evaluate(proof, case, source, native, sources, natives):
    result = {'optionId': proof['optionId'], 'kind': proof['kind'],
              'claim': proof['claim'], 'passed': False,
              'evidenceLevel': 'selected-runtime-branch' if proof['kind'].startswith('task-')
                               else 'observable-output-effect'}
    try:
        if proof['kind'].startswith('task-'):
            expected = proof['kind'] == 'task-present'
            result['sourceSatisfied'] = (proof['name'] in task_names(source)) is expected
            result['nativeSatisfied'] = (proof['name'] in task_names(native)) is expected
        else:
            def selected(observation):
                if 'pointers' in proof:
                    return [pointer(observation, p) for p in proof['pointers']]
                return pointer(observation, proof['pointer'])
            actual_source = selected(source)
            actual_native = selected(native)
            result.update(pointers=proof.get('pointers', [proof.get('pointer')]),
                          sourceValue=actual_source, nativeValue=actual_native)
            result['valueParity'] = diff(actual_source, actual_native, tolerant=False)['passed']
            if proof['kind'] == 'equals':
                result['expected'] = proof['value']
                result['sourceSatisfied'] = diff(proof['value'], actual_source, tolerant=False)['passed']
                result['nativeSatisfied'] = diff(proof['value'], actual_native, tolerant=False)['passed']
            else:
                baseline = case['baseline']
                before_source = selected(sources[baseline])
                before_native = selected(natives[baseline])
                result.update(baseline=baseline, sourceBefore=before_source, nativeBefore=before_native)
                result['sourceSatisfied'] = not diff(before_source, actual_source, tolerant=False)['passed']
                result['nativeSatisfied'] = not diff(before_native, actual_native, tolerant=False)['passed']
        result['passed'] = (result['sourceSatisfied'] and result['nativeSatisfied']
                            and result.get('valueParity', True))
    except (KeyError, IndexError, TypeError) as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    return result


def compare(rows, reference, candidate, out):
    sources = {c['id']: load(reference / (c['id'] + '.json')) for c, _ in rows}
    natives = {c['id']: load(candidate / (c['id'] + '.json')) for c, _ in rows}
    full_results = {c['id']: compare_observations(p, sources[c['id']], natives[c['id']]) for c, p in rows}
    results = []
    for case, request in rows:
        original, native = sources[case['id']], natives[case['id']]
        full = full_results[case['id']]
        proofs = [evaluate(p, case, original, native, sources, natives) for p in case.get('proofs', [])]
        current = native.get('engine', {}).get('version') == '0.1.0'
        assertions = []
        for proof, observation in zip(case.get('proofs', []), proofs):
            assertions.append({'option': proof['optionId'],
                'kind': 'source_selection' if proof['kind'].startswith('task-') else 'layout_geometry',
                'description': proof['claim'], 'expected': observation.get('sourceValue'),
                'actual': observation.get('nativeValue'), 'sourceDerived': True,
                'referencePointers': proof.get('pointers', [proof['pointer']] if 'pointer' in proof else []),
                'nativePointers': proof.get('pointers', [proof['pointer']] if 'pointer' in proof else []),
                'passed': observation['passed'], 'effectTest': observation})
        baseline_ok = case.get('baseline') is None or full_results[case['baseline']]['passed']
        results.append({'id': case['id'], 'baseline': case.get('baseline'),
                        'optionIds': sorted({p['optionId'] for p in case.get('proofs', [])}),
                        'request': {'path': str(request), 'sha256': sha(request)},
                        'reference': {'path': str(reference / (case['id'] + '.json')), 'sha256': sha(reference / (case['id'] + '.json'))},
                        'native': {'path': str(candidate / (case['id'] + '.json')), 'sha256': sha(candidate / (case['id'] + '.json'))},
                        'requestSha256': sha(request), 'referenceSha256': sha(reference / (case['id'] + '.json')),
                        'candidateSha256': sha(candidate / (case['id'] + '.json')),
                        'fullComparison': full, 'comparison': {'passed': full['passed']},
                        'proofs': proofs, 'assertions': assertions, 'candidateIs0_1_0': current,
                        'passed': full['passed'] and baseline_ok and current and all(p['passed'] for p in proofs)})
    report = {'schema': 'pyelk-option-effect-results/v1', 'caseCount': len(results),
              'passed': all(row['passed'] for row in results), 'rows': results,
              'rawDifferencesRetained': True, 'allOptionCombinationsClaimed': False,
              'sourceReexecutedByCompare': False, 'candidateReexecutedByCompare': False,
              'checkerSha256': sha(__file__)}
    write(out, report)
    print(json.dumps({'passed': report['passed'], 'cases': len(results),
                      'effectAssertions': sum(len(r['proofs']) for r in results)}))
    return 0 if report['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, default=SUITE)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--capture', choices=('reference', 'candidate'))
    parser.add_argument('--node', type=Path, default=Path('C:/Program Files/nodejs/node.exe'))
    parser.add_argument('--python', type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    rows = definitions(args.suite.resolve())
    if args.capture is None:
        if args.reference is None or args.candidate is None:
            parser.error('Pure comparison requires --reference and --candidate')
        return compare(rows, args.reference.resolve(), args.candidate.resolve(), args.out.resolve())
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    if args.capture == 'reference':
        manifest = out / 'batch.json'
        write(manifest, {'cases': [{'id': c['id'], 'request': str(p),
                                  'output': str(out / (c['id'] + '.json'))} for c, p in rows]})
        command = command_capture([str(args.node.resolve()), str(ROOT / 'tools/reference/full_layered.cjs'),
                                   str(ROOT / '.local/npm-elkjs/package'), str(manifest)], out / 'command', 180)
        commands = [command]
    else:
        commands = []
        for case, request in rows:
            commands.append(command_capture([str(args.python.resolve()), '-I',
                str(ROOT / 'scripts/validate_full_layered.py'), '--capture-candidate', str(request),
                '--source', str(ROOT / 'src'), '--out', str(out / (case['id'] + '.json'))],
                out / (case['id'] + '-command'), 60))
    report = {'schema': 'py-elk-option-effects-capture/v1', 'role': args.capture,
              'suiteSha256': sha(args.suite), 'commands': commands,
              'passed': all(c['exitCode'] == 0 and not c['timedOut'] for c in commands),
              'checkerSha256': sha(__file__)}
    write(out / 'receipt.json', report)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
