"""One small Windows CPython/wheel platform cell, in a fresh external venv."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = {'PYTHONPATH', 'PYTHONHOME', 'NODE_OPTIONS', 'NODE_PATH'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def clean_environment():
    env = {key: value for key, value in os.environ.items() if key.upper() not in OVERRIDES}
    env['PATH'] = ''
    return env


def run_command(argv, cwd, output, *, timeout=180):
    output.mkdir(parents=True, exist_ok=False)
    started = time.time_ns(); tick = time.perf_counter()
    process = subprocess.Popen([str(value) for value in argv], cwd=cwd, env=clean_environment(),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True; process.kill(); stdout, stderr = process.communicate()
    command = {'argv': [str(value) for value in argv], 'cwd': str(cwd), 'pid': process.pid,
        'exitCode': process.returncode, 'timedOut': timed_out, 'elapsedSeconds': time.perf_counter()-tick,
        'startedTimeNs': started, 'finishedTimeNs': time.time_ns(),
        'stdoutSha256': digest(stdout), 'stderrSha256': digest(stderr),
        'environmentPolicy': {'pathEmpty': True, 'overridesAbsent': True}}
    for name, raw in [('stdout.log', stdout), ('stderr.log', stderr)]:
        (output/name).write_bytes(raw)
    (output/'command.json').write_text(json.dumps(command, indent=2)+'\n', encoding='utf-8', newline='\n')
    result = {'command': command, 'stdoutBytesBase64': base64.b64encode(stdout).decode(),
              'stderrBytesBase64': base64.b64encode(stderr).decode()}
    if process.returncode or timed_out:
        raise RuntimeError('Actual command failed; preserve '+str(output/'command.json'))
    return result


def capture_cell(python, minor, wheel, suite, output, *, artifact_kind='wheel', artifact=None, wheelhouse=None,
                 provenance=None):
    if platform.system() != 'Windows':
        raise RuntimeError('This runner captures Windows only')
    output = Path(output).absolute(); output.mkdir(parents=True, exist_ok=False)
    work = Path(tempfile.mkdtemp(prefix='py-elk-e10-windows-'+minor+'-')).absolute()
    if work.resolve().is_relative_to(ROOT):
        raise RuntimeError('Fresh platform venv/cwd must be outside the repository')
    python = os.path.abspath(python); wheel = Path(wheel).absolute(); suite = Path(suite).absolute()
    artifact = Path(artifact or wheel).absolute()
    creation = run_command([python, '-I', '-m', 'venv', str(work/'venv')], work, output/'venv-command')
    candidate = str(work/'venv/Scripts/python.exe')
    build_dependencies = None
    if artifact_kind == 'sdist':
        if wheelhouse is None:
            raise ValueError('sdist installation requires the fixed offline build wheelhouse')
        build_dependencies = run_command([candidate, '-I', '-m', 'pip', 'install', '--no-index', '--find-links',
            str(Path(wheelhouse).absolute()), 'setuptools==84.2.1', 'wheel==0.48.0', 'packaging==26.3'],
            work, output/'build-dependencies-command')
    installation = run_command([candidate, '-I', '-m', 'pip', 'install', '--no-index', '--no-deps',
        *(['--no-build-isolation'] if artifact_kind == 'sdist' else []), str(artifact)], work, output/'install-command')
    observation_path = work/'observation.json'
    captured = run_command([candidate, '-I', str(ROOT/'tools/platform/capture_e10.py'), '--wheel', str(wheel),
                           '--suite', str(suite), '--out', str(observation_path)], work, output/'capture-command')
    raw = observation_path.read_bytes(); observed = json.loads(raw)
    actual_minor = '.'.join(str(part) for part in observed['engine']['versionInfo'][:2])
    if actual_minor != minor or observed['engine']['platform']['system'] != 'Windows':
        raise RuntimeError('Requested platform/minor differs from actual interpreter')
    cell = {'schema': 'py-elk-e10-platform-cell/v1', 'id': 'windows-cpython-'+minor, 'os': 'Windows',
        'pythonMinor': minor, 'wheel': str(wheel), 'wheelSha256': digest(wheel.read_bytes()), 'candidatePython': candidate,
        'actualSourceRoot': str(ROOT), 'launcherPid': os.getpid(), **captured,
        'observationBytesBase64': base64.b64encode(raw).decode(), 'observationSha256': digest(raw),
        'installation': {'artifactKind': artifact_kind, 'artifact': str(artifact), 'artifactSha256': digest(artifact.read_bytes()),
                         'venvCommand': creation, 'installCommand': installation, 'buildDependenciesCommand': build_dependencies},
        'interpreterProvenance': provenance or {'provider': 'existing-host-python', 'executable': python,
                                              'sha256': digest(Path(python).read_bytes())},
        'externalWorkDirectory': str(work), 'fullValidation': False, 'historicalExecutionAuthenticated': False}
    (output/'observation.json').write_bytes(raw)
    with (output/'cell.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(cell, stream, ensure_ascii=False, allow_nan=False, indent=2); stream.write('\n')
    return cell


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', required=True)
    parser.add_argument('--minor', required=True, choices=('3.11','3.12','3.13','3.14'))
    parser.add_argument('--wheel', required=True, type=Path)
    parser.add_argument('--suite', type=Path, default=ROOT/'tests/fixtures/suites/E10')
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--artifact-kind', choices=('wheel','sdist'), default='wheel')
    parser.add_argument('--artifact', type=Path)
    parser.add_argument('--wheelhouse', type=Path)
    parser.add_argument('--provenance', type=Path)
    args = parser.parse_args()
    provenance = None if args.provenance is None else json.loads(args.provenance.read_bytes())
    value = capture_cell(args.python,args.minor,args.wheel,args.suite,args.out,artifact_kind=args.artifact_kind,
                         artifact=args.artifact,wheelhouse=args.wheelhouse,provenance=provenance)
    print(json.dumps({'id':value['id'],'artifactKind':args.artifact_kind,'cell':str(args.out/'cell.json')}))


if __name__ == '__main__':
    main()
