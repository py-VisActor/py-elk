"""Pinned Linux interpreters and targeted E10 installed cells; no full checks."""
from __future__ import annotations
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import subprocess
import tarfile
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
MINORS = ('3.11', '3.12', '3.13', '3.14')
OVERRIDES = {'PYTHONPATH', 'PYTHONHOME', 'NODE_OPTIONS', 'NODE_PATH'}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): digest.update(block)
    return digest.hexdigest()


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def clean_environment(*, runtime):
    environment = {k: v for k, v in os.environ.items() if k.upper() not in OVERRIDES}
    if runtime: environment['PATH'] = ''
    return environment


def run_command(argv, folder, *, cwd, runtime=False, timeout=120):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=False)
    environment = clean_environment(runtime=runtime)
    start = time.perf_counter(); process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try: stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True; process.kill(); stdout, stderr = process.communicate()
    (folder/'stdout.log').write_bytes(stdout); (folder/'stderr.log').write_bytes(stderr)
    command = {'argv': list(map(str, argv)), 'cwd': str(cwd), 'pid': process.pid,
               'exitCode': process.returncode, 'timedOut': timed_out,
               'environmentPolicy': {'pathEmpty': environment.get('PATH') == '', 'overridesAbsent': not any(k.upper() in OVERRIDES for k in environment)},
               'elapsedSeconds': time.perf_counter()-start,
               'stdoutSha256': hashlib.sha256(stdout).hexdigest(), 'stderrSha256': hashlib.sha256(stderr).hexdigest()}
    save(folder/'command.json', command)
    return {'command': command, 'stdoutBytesBase64': base64.b64encode(stdout).decode(),
            'stderrBytesBase64': base64.b64encode(stderr).decode()}


def choose_assets(release_file, expected_sha):
    if sha256(release_file) != expected_sha: raise ValueError('Release API original bytes differ')
    release = json.loads(Path(release_file).read_text())
    if release.get('tag_name') != '20261026' or release.get('immutable') is not True:
        raise ValueError('Use the reviewed immutable PBS20261026 release')
    selected = {}
    for minor in MINORS:
        pattern = r'cpython-('+re.escape(minor)+r'\.\d+)\+20261026-x86_64-unknown-linux-gnu-install_only\.tar\.gz'
        candidates = [(a, re.fullmatch(pattern, a['name'])) for a in release['assets']]
        candidates = [(a, m) for a, m in candidates if m]
        if len(candidates) != 1: raise ValueError('Missing/ambiguous standard Linux build '+minor)
        asset, match = candidates[0]
        if (type(asset['size']) is not int or asset['size'] <= 0 or
                not re.fullmatch(r'sha256:[0-9a-f]{64}', asset['digest'])):
            raise ValueError('Published asset size/digest missing')
        selected[minor] = {'version': match[1], **{k: asset[k] for k in ('id', 'name', 'size', 'digest', 'browser_download_url')}}
    return selected


def download_asset(asset, cache):
    digest = asset['digest'].split(':', 1)[1]
    folder = Path(cache)/'archives'/digest; folder.mkdir(parents=True, exist_ok=True)
    target = folder/asset['name']
    if target.exists():
        if target.stat().st_size != asset['size'] or sha256(target) != digest:
            raise ValueError('Existing archive differs; retained without overwriting: '+str(target))
        return target
    temporary = folder/(asset['name']+'.partial-'+uuid.uuid4().hex)
    started = time.monotonic(); status = None; headers = None
    try:
        request = urllib.request.Request(asset['browser_download_url'], headers={'User-Agent': 'py-elk-E10-targeted-platform'})
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open('xb') as stream:
            status = response.status; headers = {k: response.headers.get(k) for k in ('Content-Length', 'ETag', 'Last-Modified')}
            while block := response.read(1024*1024): stream.write(block)
        actual = sha256(temporary)
        if temporary.stat().st_size != asset['size'] or actual != digest: raise ValueError('Downloaded archive size/SHA differs')
        temporary.rename(target)
        save(folder/('download-'+uuid.uuid4().hex+'.json'), {'url': asset['browser_download_url'], 'asset': asset,
             'httpStatus': status, 'headers': headers, 'elapsedSeconds': time.monotonic()-started, 'archiveSha256': actual})
    except Exception as error:
        save(folder/('failed-download-'+uuid.uuid4().hex+'.json'), {'url': asset['browser_download_url'], 'httpStatus': status,
             'elapsedSeconds': time.monotonic()-started, 'retainedPartial': str(temporary), 'error': str(error)})
        raise
    return target


def extract_asset(archive, asset, cache):
    destination = Path(cache)/'python'/asset['digest'].split(':', 1)[1]
    executable = destination/'python/bin'/('python'+asset['version'].rsplit('.', 1)[0])
    if executable.is_file(): return executable
    staging = destination.with_name(destination.name+'.extracting-'+uuid.uuid4().hex); staging.mkdir(parents=True)
    with tarfile.open(archive, 'r:gz') as source:
        for member in source.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'python':
                raise ValueError('Archive member escapes Python root')
            if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                raise ValueError('Unsupported special archive member')
            if member.issym() or member.islnk():
                link = member.linkname if member.islnk() else posixpath.join(str(path.parent), member.linkname)
                normalized = PurePosixPath(posixpath.normpath(link))
                if normalized.is_absolute() or not normalized.parts or normalized.parts[0] != 'python' or '..' in normalized.parts:
                    raise ValueError('Archive link escapes Python root')
        source.extractall(staging, filter='data')
    staged = staging/executable.relative_to(destination)
    if not staged.is_file() or not staged.resolve().is_relative_to(staging.resolve()): raise ValueError('Extracted interpreter missing/escaping')
    staging.rename(destination)
    return executable


def acquire(release_file, release_sha, cache, out):
    if os.name != 'posix': raise ValueError('Run Linux acquisition inside WSL/Linux')
    selected = choose_assets(release_file, release_sha); rows = []
    for minor, asset in selected.items():
        archive = download_asset(asset, cache); executable = extract_asset(archive, asset, cache)
        code = 'import sys,platform,json,sysconfig;print(json.dumps({"version":sys.version,"versionInfo":list(sys.version_info[:3]),"implementation":platform.python_implementation(),"executable":sys.executable,"prefix":sys.prefix,"basePrefix":sys.base_prefix,"soabi":sysconfig.get_config_var("SOABI")}))'
        command = run_command([str(executable), '-IB', '-c', code], Path(out)/('identity-'+minor), cwd=Path(cache))
        if command['command']['exitCode'] != 0: raise ValueError('Acquired interpreter cannot execute '+minor)
        identity = json.loads(base64.b64decode(command['stdoutBytesBase64']))
        if identity['implementation'] != 'CPython' or '.'.join(map(str, identity['versionInfo'])) != asset['version']:
            raise ValueError('Extracted version differs from selected archive')
        row = {'pythonMinor': minor, 'asset': asset, 'archive': str(archive), 'archiveSha256': sha256(archive),
               'executable': str(executable), 'executableSha256': sha256(executable), 'identity': identity, 'identityCommand': command}
        save(Path(out)/('python-'+minor+'.json'), row); rows.append(row)
    result = {'schema': 'py-elk-e10-linux-interpreters/v1', 'releaseApiSha256': release_sha,
              'releaseApiPath': str(release_file), 'cache': str(cache), 'interpreters': rows, 'fullValidation': False}
    save(Path(out)/'interpreters.json', result); return result


def cell(interpreter, wheel, suite, out):
    out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=False)
    candidate = out/'venv/bin/python'
    creation = run_command([interpreter['executable'], '-I', '-m', 'venv', str(out/'venv')], out/'venv-command', cwd=out)
    if creation['command']['exitCode'] != 0: raise ValueError('Linux venv creation failed')
    installation = run_command([str(candidate), '-I', '-m', 'pip', 'install', '--no-index', '--no-deps', str(wheel)], out/'install-command', cwd=out)
    if installation['command']['exitCode'] != 0: raise ValueError('Linux exact wheel installation failed')
    captured = run_command([str(candidate), '-I', str(ROOT/'tools/platform/capture_e10.py'), '--wheel', str(wheel),
                            '--suite', str(suite), '--out', str(out/'observation.json')], out/'capture-command', cwd=out, runtime=True)
    record = {'schema': 'py-elk-e10-platform-cell/v1', 'id': 'linux-cpython-'+interpreter['pythonMinor'], 'os': 'Linux',
              'pythonMinor': interpreter['pythonMinor'], 'wheel': str(wheel), 'wheelSha256': sha256(wheel),
              'candidatePython': str(candidate), 'actualSourceRoot': str(ROOT), 'launcherPid': os.getpid(), **captured,
              'installation': {'venvCommand': creation, 'installCommand': installation, 'artifactKind': 'wheel', 'artifactSha256': sha256(wheel)},
              'interpreterProvenance': interpreter, 'fullValidation': False}
    if (out/'observation.json').exists():
        raw = (out/'observation.json').read_bytes(); record.update(observationBytesBase64=base64.b64encode(raw).decode(), observationSha256=hashlib.sha256(raw).hexdigest())
    save(out/'cell.json', record)
    if captured['command']['exitCode'] != 0 or captured['command']['timedOut']: raise ValueError('Actual Linux platform capture failed; original command retained')
    return record


def sdist_cell(interpreter, sdist, wheelhouse, suite, out):
    """One Linux representative builds the actual sdist without network access."""
    if interpreter['pythonMinor'] != '3.14': raise ValueError('Only the declared Linux3.14 sdist representative')
    out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=False); python = out/'build-venv/bin/python'
    create = run_command([interpreter['executable'], '-I', '-m', 'venv', str(out/'build-venv')], out/'build-venv-command', cwd=out)
    if create['command']['exitCode'] != 0: raise ValueError('Sdist build venv failed')
    dependencies = run_command([str(python), '-I', '-m', 'pip', 'install', '--no-index', '--no-deps', '--find-links', str(wheelhouse),
                                'setuptools==84.2.1', 'wheel==0.48.0', 'packaging==26.3'], out/'build-dependencies-command', cwd=out)
    if dependencies['command']['exitCode'] != 0: raise ValueError('Offline pinned build tools missing')
    build = run_command([str(python), '-I', '-m', 'pip', 'wheel', '--no-index', '--no-deps', '--no-build-isolation',
                         '--wheel-dir', str(out/'dist'), str(sdist)], out/'build-command', cwd=out)
    wheels = list((out/'dist').glob('*.whl'))
    if build['command']['exitCode'] != 0 or len(wheels) != 1: raise ValueError('Actual offline sdist build failed')
    captured = cell(interpreter, wheels[0], suite, out/'installed-capture')
    captured['id'] += '-sdist'
    captured['installation'].update(artifactKind='sdist', artifactSha256=sha256(sdist), sourceArchive=str(sdist),
                                   buildVenvCommand=create, buildDependenciesCommand=dependencies, buildCommand=build,
                                   builtWheelSha256=sha256(wheels[0]))
    save(out/'sdist-cell.json', captured)
    return captured


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='action', required=True)
    download = sub.add_parser('acquire'); download.add_argument('--release-api', type=Path, required=True); download.add_argument('--release-sha', required=True)
    download.add_argument('--cache', type=Path, required=True); download.add_argument('--out', type=Path, required=True)
    execute = sub.add_parser('run'); execute.add_argument('--interpreters', type=Path, required=True); execute.add_argument('--wheel', type=Path, required=True)
    execute.add_argument('--suite', type=Path, required=True); execute.add_argument('--out', type=Path, required=True); execute.add_argument('--jobs', type=int, default=2)
    sdist = sub.add_parser('sdist'); sdist.add_argument('--interpreters', type=Path, required=True); sdist.add_argument('--sdist', type=Path, required=True)
    sdist.add_argument('--wheelhouse', type=Path, required=True); sdist.add_argument('--suite', type=Path, required=True); sdist.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); args.out = args.out.resolve(); args.out.mkdir(parents=True, exist_ok=False)
    if args.action == 'acquire':
        acquire(args.release_api.resolve(), args.release_sha, args.cache.expanduser().resolve(), args.out)
    elif args.action == 'sdist':
        rows = json.loads(args.interpreters.read_text())['interpreters']
        selected = next(row for row in rows if row['pythonMinor'] == '3.14')
        sdist_cell(selected, args.sdist.resolve(), args.wheelhouse.resolve(), args.suite.resolve(), args.out/'representative')
    else:
        if not 1 <= args.jobs <= 4: raise ValueError('Use1..4 independent platform cells')
        interpreters = json.loads(args.interpreters.read_text())['interpreters']
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = [pool.submit(cell, row, args.wheel.resolve(), args.suite.resolve(), args.out/row['pythonMinor']) for row in interpreters]
            results = [future.result() for future in futures]
        save(args.out/'matrix.json', {'schema': 'py-elk-e10-linux-platform-matrix/v1', 'cells': results, 'fullValidation': False})


if __name__ == '__main__': main()
