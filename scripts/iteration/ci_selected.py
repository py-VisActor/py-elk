"""Explicit change checks; unknown impact stops instead of falling back to full.

The reviewed manifest is a human impact plan, not proof of exhaustive impact.
Saved evidence only permits exact current-byte rechecks, never cached PASS.
"""
from __future__ import annotations
import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_path(value):
    if type(value) is not str or not value or '\\' in value or '\x00' in value:
        raise ValueError('Changed path must be a nonempty repository POSIX path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ('', '.', '..') for p in value.split('/')) or ':' in value:
        raise ValueError('Changed path escapes repository: '+value)
    return value


def git_paths(base=None, root=ROOT, environment=None):
    env = os.environ if environment is None else environment
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip()
    if base is None:
        event = load(env['GITHUB_EVENT_PATH'])
        base = event['pull_request']['base']['sha'] if 'pull_request' in event else event['before']
    if not re.fullmatch('[0-9a-fA-F]{40}', base):
        raise ValueError('Expected explicit 40-hex base commit')
    argv = (['git', 'ls-files', '-z', '--cached'] if base == '0'*40 else
            ['git', 'diff', '-z', '--name-only', '--no-renames', base, head, '--'])
    return [safe_path(x.decode('utf8')) for x in subprocess.check_output(argv, cwd=root).split(b'\0') if x]


def plan(paths, manifest, root=ROOT):
    if manifest['schema'] != 'py-elk-ci-selected/v1':
        raise ValueError('Unknown CI manifest')
    if type(paths) is not list:
        raise ValueError('Changed paths must be an explicit JSON array')
    paths = sorted(set(safe_path(p) for p in paths))
    checks = manifest['checks']; selected = set(); documented = []; saved = []; unknown = []
    evidence = manifest['savedEvidence']
    evidence_path = safe_path(evidence['path'])
    if digest(Path(root)/evidence_path) != evidence['sha256']:
        raise ValueError('Saved evidence bytes differ from the explicit CI manifest')
    previous = {**load(Path(root)/evidence_path)['inputFilesSha256'],
                **evidence.get('additionalFrozenFilesSha256', {}), evidence_path: evidence['sha256']}
    for path in paths:
        matched = [r for r in manifest['rules'] if any(fnmatch.fnmatchcase(path, p) for p in r['paths'])]
        if matched:
            for rule in matched:
                selected.update(rule['checks'])
        elif any(fnmatch.fnmatchcase(path, p) for p in manifest['documentationOnly']):
            documented.append(path)
        elif path in previous and (Path(root)/path).is_file() and digest(Path(root)/path) == previous[path]:
            saved.append({'path': path, 'sha256': previous[path]})
        else:
            unknown.append(path)
    if any(key not in checks for key in selected):
        raise ValueError('Rule names an undefined check')
    commands = []
    for identifier in sorted(selected):
        if type(identifier) is not str or not re.fullmatch('[a-z0-9_-]+', identifier):
            raise ValueError('Check identifiers must be safe log basenames')
        check = checks[identifier]
        if check['kind'] == 'unittest-file':
            path = Path(safe_path(check['path']))
            if not path.name.startswith('test_') or path.suffix != '.py':
                raise ValueError('Select an explicit unittest file')
            argv = [sys.executable, '-m', 'unittest', 'discover', '-s', path.parent.as_posix(), '-p', path.name, '-v']
        elif check['kind'] == 'python-script':
            path = safe_path(check['path'])
            if path in {'scripts/check.py', 'scripts/check_fresh_copy.py', 'scripts/validate_layout.py', 'scripts/upstream.py'}:
                raise ValueError('Full/capture entrypoints are not selected CI checks')
            if not all(type(x) is str for x in check.get('arguments', [])):
                raise ValueError('Script arguments must be explicit strings')
            argv = [sys.executable, path, *check.get('arguments', [])]
        else:
            raise ValueError('Unknown selected check kind')
        commands.append({'id': identifier, 'argv': argv})
    return {'changedPaths': paths, 'commands': commands, 'documentationOnly': documented,
            'savedEvidenceByteRechecks': saved, 'unplannedPaths': unknown, 'passed': not unknown,
            'savedEvidenceReceipt': {'path': evidence_path, 'sha256': evidence['sha256']},
            'fullValidation': False, 'impactExhaustivenessProven': False}


def execute(selection, output, root=ROOT):
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    rows = []
    if selection['passed']:
        for command in selection['commands']:
            start = time.perf_counter(); timed_out = False
            try:
                process = subprocess.run(command['argv'], cwd=root, capture_output=True, timeout=300, check=False)
                code, stdout, stderr = process.returncode, process.stdout, process.stderr
            except subprocess.TimeoutExpired as error:
                code, stdout, stderr, timed_out = None, error.stdout or b'', error.stderr or b'', True
            (output/(command['id']+'.stdout.log')).write_bytes(stdout)
            (output/(command['id']+'.stderr.log')).write_bytes(stderr)
            rows.append({**command, 'cwd': str(root), 'exitCode': code, 'timedOut': timed_out,
                         'elapsedSeconds': time.perf_counter()-start,
                         'stdoutSha256': hashlib.sha256(stdout).hexdigest(),
                         'stderrSha256': hashlib.sha256(stderr).hexdigest()})
            if code != 0 or timed_out:
                break
    result = {'schema': 'py-elk-ci-selection-result/v1', **selection, 'executed': rows,
              'passed': selection['passed'] and all(r['exitCode'] == 0 and not r['timedOut'] for r in rows),
              'runtimeReexecuted': bool(rows), 'limitation': 'Explicit human impact plan; unknown paths need a reviewed plan. Saved hashes recheck bytes, not prior execution.'}
    (output/'report.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    return result


def final_ready(root=ROOT, environment=None):
    env = os.environ if environment is None else environment
    machine = load(Path(root)/'docs/iteration-plan.json')
    iterations = {row['id']: row for row in machine['iterations']}
    foundations_ready = all(iterations.get('E'+str(n), {}).get('status') == 'complete'
                            for n in (9, 10))
    features_ready = all(
        iterations.get('E'+str(n), {}).get('implementationStatus') == 'complete'
        or iterations.get('E'+str(n), {}).get('status') == 'complete'
        for n in range(13, 20))
    # Final validation precedes publication and establishes acceptance itself.
    # E11/E12 release work and E20/E21 acceptance are therefore not prerequisites.
    if (env.get('ALL_FEATURES_COMPLETE') != 'true' or
            machine.get('validationPolicy', {}).get('featureImplementationComplete') is not True or
            not foundations_ready or not features_ready):
        raise ValueError('Manual full requires ALL_FEATURES_COMPLETE=true, '
                         'featureImplementationComplete=true, E09/E10 complete, '
                         'and E13-E19 implementationStatus or status complete')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT/'docs/iterations/E11-ci-checks.json')
    parser.add_argument('--base'); parser.add_argument('--paths-file', type=Path)
    parser.add_argument('--out', type=Path); parser.add_argument('--require-final-ready', action='store_true')
    args = parser.parse_args()
    try:
        if args.require_final_ready:
            final_ready(); print('Final workflow gate satisfied'); return 0
        if args.out is None: parser.error('--out is required for selected checks')
        if args.base and args.paths_file: parser.error('Choose base or paths-file')
        paths = load(args.paths_file) if args.paths_file else git_paths(args.base)
        selection = plan(paths, load(args.manifest))
        selection.update(manifestSha256=digest(args.manifest), selectorSha256=digest(__file__))
        result = execute(selection, args.out)
        print(json.dumps({'passed': result['passed'], 'selectedChecks': [x['id'] for x in result['commands']],
                          'documentationPaths': len(result['documentationOnly']),
                          'savedEvidenceByteRechecks': len(result['savedEvidenceByteRechecks']),
                          'unplannedPaths': result['unplannedPaths'], 'reportPath': str(args.out/'report.json'),
                          'fullValidation': False}))
        return 0 if result['passed'] else 1
    except (KeyError, ValueError, OSError, TypeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
