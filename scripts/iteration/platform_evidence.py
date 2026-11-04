"""Seal and independently recheck the historical 0.0.1a0 platform bytes offline.

--seal-archive reads the explicit original receipts once. --check reads only the
sealed archive and bound repository tools; it never installs or executes pyelk.
"""
from __future__ import annotations
import argparse
import base64
import builtins
from contextlib import contextmanager, redirect_stdout
from email.parser import BytesParser
import hashlib
import importlib
import io
import json
import os
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
import sys
import tempfile
from types import SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = 'references/full-native-closure/platform.zip'
MANIFEST = 'references/full-native-closure/platform.manifest.json'
ORIGINAL_REPORT = 'test-runs/20261104-FULL/V/platform-saved-02/report.json'
WHEEL = 'test-runs/full-native-01/distribution-first/py_elk-0.0.1a0-py3-none-any.whl'
SDIST = 'test-runs/full-native-01/distribution-first/py_elk-0.0.1a0.tar.gz'
REQUEST = 'tests/fixtures/suites/full-native-core/platform-layout-request.json'
ORACLE = 'test-runs/20261104-FULL/V/platform-layout-original-01/observation.json'
FROZEN_REPORT = 'docs/releases/evidence/development-frozen/report.json'
FROZEN_FOLDER = 'test-runs/full-native-01/development-frozen'
WANTED = {f'{s}-{v}-wheel' for s in ('windows', 'linux') for v in ('3.11', '3.12', '3.13', '3.14')}
WANTED |= {'windows-3.13-sdist', 'linux-3.14-sdist'}
DEPENDENCIES = (
    'scripts/iteration/platform_evidence.py', 'scripts/validate_full_platform.py',
    'scripts/layout_checks.py', 'scripts/source_read_cache.py',
    'scripts/validate_e08_api.py', 'scripts/validate_layout.py',
    'scripts/validate_e04_runtime.py', 'scripts/validate_e04_source_bindings.py',
    'scripts/e07_geometry_premise.py', 'scripts/e09_geometry_premise.py',
    'scripts/upstream.py', 'tools/reference/e09_host_lifecycle_probe.py',
    'tools/reference/native_process_probe.py',
    'tests/fixtures/suites/full-native-core/metadata-expected.json', FROZEN_REPORT,
)
_AUDIT_STATE = None
_AUDIT_INSTALLED = False


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def safe_path(root, name):
    if type(name) is not str or not name or '\\' in name or ':' in name:
        raise ValueError('Nonportable evidence path: ' + repr(name))
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('', '.', '..') for x in name.split('/')) or str(p) != name:
        raise ValueError('Escaping evidence path: ' + name)
    root = Path(root).resolve(); result = root.joinpath(*p.parts).resolve()
    if not result.is_relative_to(root):
        raise ValueError('Evidence path escapes root: ' + name)
    return result


def check_bytes(raw, row):
    if type(row.get('bytes')) is not int or row['bytes'] < 0 or len(raw) != row['bytes'] or digest(raw) != row['sha256']:
        raise ValueError('Evidence bytes/SHA differ: ' + row['path'])


def original_relative(name, original_root):
    return PureWindowsPath(name).relative_to(PureWindowsPath(original_root)).as_posix()


def validate_manifest(m):
    if m.get('schema') != 'pyelk-platform-evidence-manifest/v1' or m.get('baseline') != {'distributionName': 'py-elk', 'version': '0.0.1a0'}:
        raise ValueError('Not the historical 0.0.1a0 platform baseline')
    seen = set()
    for row in m['archivedFiles'] + m['repositoryDependencies']:
        name = row['path']; safe_path(Path.cwd(), name)
        if name in seen: raise ValueError('Duplicate manifest member: ' + name)
        seen.add(name)
        if type(row['bytes']) is not int or row['bytes'] < 0: raise ValueError('Invalid member size')
        if type(row['sha256']) is not str or len(row['sha256']) != 64 or any(c not in '0123456789abcdef' for c in row['sha256']):
            raise ValueError('Invalid member SHA')
    if {r['path'] for r in m['repositoryDependencies']} != set(DEPENDENCIES):
        raise ValueError('Repository dependency denominator differs')
    selected = m['selectedCells']
    if len(selected) != 10 or {r['id'] for r in selected} != WANTED:
        raise ValueError('Selected platform cells differ; duplicates/failure cells cannot count')
    archived = {r['path'] for r in m['archivedFiles']}
    for cell in selected:
        for key in ('cell', 'observation'):
            if cell[key] not in archived: raise ValueError('Selected raw missing from manifest')
        if not cell['commands'] or any(p not in archived for p in cell['commands']):
            raise ValueError('Selected commands missing')
    for name in (ORIGINAL_REPORT, WHEEL, SDIST, REQUEST, ORACLE):
        if name not in archived: raise ValueError('Required baseline input missing')


def decode_archive(m, raw):
    """Check all bytes and names before extraction; no filesystem fallback."""
    validate_manifest(m)
    check_bytes(raw, {'path': ARCHIVE, **m['archive']})
    expected = {r['path']: r for r in m['archivedFiles']}; result = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as stream:
        infos = stream.infolist()
        if len(infos) != len(expected) or {i.filename for i in infos} != set(expected):
            raise ValueError('Missing, extra or duplicate ZIP members')
        for info in infos:
            safe_path(Path.cwd(), info.filename)
            if (info.external_attr >> 16) & 0o170000 == 0o120000 or info.is_dir():
                raise ValueError('Nonregular ZIP member')
            row = expected[info.filename]
            if info.file_size != row['bytes']: raise ValueError('ZIP declared size differs')
            value = stream.read(info); check_bytes(value, row); result[info.filename] = value
    return result


def seal_archive(root=ROOT, archive_path=None, manifest_path=None):
    root = Path(root).resolve(); archive_path = Path(archive_path or root / ARCHIVE); manifest_path = Path(manifest_path or root / MANIFEST)
    if archive_path.exists() or manifest_path.exists(): raise FileExistsError('Platform archive already sealed')
    report = load(root / ORIGINAL_REPORT)
    if report['passed'] is not True or len(report['filesSha256']) != 20 or len(report['cells']) != 10:
        raise ValueError('Original saved verification denominator differs')
    files = {}; selected = []
    def add(name, wanted=None):
        path = safe_path(root, name); raw = path.read_bytes()
        if wanted is not None and digest(raw) != wanted: raise ValueError('Original receipt SHA differs: ' + name)
        files[name] = raw
    for name in (ORIGINAL_REPORT, WHEEL, SDIST, REQUEST, ORACLE): add(name)
    for old, wanted in report['filesSha256'].items():
        name = original_relative(old, str(root)); add(name, wanted)
        if not name.endswith('/cell.json'): continue
        folder = PurePosixPath(name).parent; cell = load(root / name); observation = str(folder / 'observation.json')
        if cell['id'] not in WANTED: raise ValueError('Unexpected selected cell')
        commands = []
        for command in sorted((root / folder).glob('*/command.json')):
            for path in (command, command.with_name('stdout.log'), command.with_name('stderr.log')):
                relative = path.relative_to(root).as_posix(); add(relative); commands.append(relative)
        selected.append({'id': cell['id'], 'cell': name, 'observation': observation, 'commands': commands})
    # Preserve failed launchers and first failed audit as history, never as cells.
    history = []
    for folder in ('platform-matrix-01', 'platform-saved-01', 'platform-sdist-linux-02'):
        base = root / 'test-runs/20261104-FULL/V' / folder
        for path in sorted(base.glob('*')):
            if path.is_file() and path.suffix in ('.json', '.log'):
                name = path.relative_to(root).as_posix(); add(name); history.append(name)
    frozen = load(root / FROZEN_REPORT)
    for row in frozen['commands']:
        for leaf in ('command.json', 'stdout.log', 'stderr.log'):
            relative = row['name'] + '-command/' + leaf
            add(FROZEN_FOLDER + '/' + relative, frozen['files'][relative])
    deps = []
    for name in DEPENDENCIES:
        raw = safe_path(root, name).read_bytes(); deps.append({'path': name, 'bytes': len(raw), 'sha256': digest(raw)})
    m = {'schema': 'pyelk-platform-evidence-manifest/v1', 'baseline': {'distributionName': 'py-elk', 'version': '0.0.1a0'},
         'originalExecutionRoot': str(root), 'originalReport': ORIGINAL_REPORT,
         'selectedCells': sorted(selected, key=lambda r: r['id']), 'historyOnly': sorted(set(history)),
         'archivedFiles': [{'path': name, 'bytes': len(raw), 'sha256': digest(raw)} for name, raw in sorted(files.items())],
         'repositoryDependencies': deps, 'productExecutions': 0, 'sourceExecutions': 0}
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as stream:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 4, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o100644 << 16
            stream.writestr(info, raw, compresslevel=9)
    raw = archive_path.read_bytes(); m['archive'] = {'bytes': len(raw), 'sha256': digest(raw)}
    validate_manifest(m)
    manifest_path.write_text(json.dumps(m, indent=2) + '\n', encoding='utf8', newline='\n')
    return {'sealed': True, 'baseline': m['baseline'], 'archivedFiles': len(files), 'archiveSha256': digest(raw), 'productsExecuted': 0}



def verify_frozen_validation(root, values):
    """Recount original logs; no unittest/command execution or current claim."""
    report = load(Path(root) / FROZEN_REPORT)
    names = report['plannedSteps']
    if (report['passed'] is not True or report['status'] != 'DEVELOPMENT_CHECKS_PASS'
            or report['inputsUnchanged'] is not True or report['changedDuringExecution'] != []
            or len(names) != 37 or len(set(names)) != 37
            or [row['name'] for row in report['commands']] != names):
        raise ValueError('Frozen37 validation identity/order differs')
    test_count = skipped = log_bytes = 0
    expected_files = set()
    for row in report['commands']:
        raw = {}
        for leaf in ('command.json', 'stdout.log', 'stderr.log'):
            relative = row['name'] + '-command/' + leaf; name = FROZEN_FOLDER + '/' + relative
            expected_files.add(name); data = values[name]
            if digest(data) != report['files'][relative]: raise ValueError('Frozen command/log SHA differs: ' + relative)
            raw[leaf] = data
        command = json.loads(raw['command.json'])
        expected = {k: v for k, v in row.items() if k != 'name'}
        if json.dumps(command, sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise ValueError('Frozen saved command differs: ' + row['name'])
        if type(command['exitCode']) is not int or command['exitCode'] != 0 or command['timedOut'] is not False:
            raise ValueError('Frozen command failed/timed out: ' + row['name'])
        for leaf, key in (('stdout.log', 'stdoutSha256'), ('stderr.log', 'stderrSha256')):
            if digest(raw[leaf]) != command[key]: raise ValueError('Frozen command stream SHA differs')
            log_bytes += len(raw[leaf])
        stderr = raw['stderr.log'].decode('utf8')
        test_count += sum(map(int, re.findall(r'(?m)^Ran (\d+) tests?\b', stderr)))
        skipped += sum(map(int, re.findall(r'\bskipped=(\d+)', stderr)))
    if {n for n in values if n.startswith(FROZEN_FOLDER + '/')} != expected_files or len(expected_files) != 111:
        raise ValueError('Frozen111 command/log file denominator differs')
    if (test_count, skipped, log_bytes) != (917, 1, 202901):
        raise ValueError('Frozen test/log denominator differs')
    return {'baselineVersion': '0.0.1a0', 'steps': 37, 'testMethods': test_count, 'commands': 37, 'tests': test_count, 'skipped': skipped,
            'rawFiles': 111, 'logs': 74, 'rawLogBytes': log_bytes, 'commandNames': names,
            'sourceReport': FROZEN_REPORT, 'sourceReportSha256': digest((Path(root) / FROZEN_REPORT).read_bytes()),
            'productExecutions': 0, 'testsReexecuted': 0}


def _audit(event, args):
    state = _AUDIT_STATE
    if state is None: return
    if event.startswith('subprocess.') or event in ('os.system', 'os.exec', 'os.spawn', 'os.posix_spawn', 'os.fork', 'os.kill', 'os.killpg', 'pty.spawn'):
        raise RuntimeError('Platform evidence check forbids process execution')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        text = os.fsdecode(args[0]); normalized = text.replace('\\', '/').lower()
        old = state['originalRoot'].replace('\\', '/').rstrip('/').lower()
        if normalized.startswith(old + '/test-runs/') or normalized.startswith(old + '/.local/'):
            raise RuntimeError('Platform evidence check forbids original ignored workspace reads')
        path = Path(text).resolve()
        root = state['root']
        if path.is_relative_to(root) and path.relative_to(root).parts[:1] in (('test-runs',), ('.local',)):
            raise RuntimeError('Platform evidence check forbids ignored workspace reads')


@contextmanager
def offline_guard(root, original_root):
    global _AUDIT_STATE, _AUDIT_INSTALLED
    if not _AUDIT_INSTALLED: sys.addaudithook(_audit); _AUDIT_INSTALLED = True
    old = _AUDIT_STATE; original_import = builtins.__import__
    def guarded_import(name, *args, **kwargs):
        if name == 'pyelk' or name.startswith('pyelk.'):
            raise RuntimeError('Platform evidence check forbids pyelk imports')
        return original_import(name, *args, **kwargs)
    _AUDIT_STATE = {'root': Path(root).resolve(), 'originalRoot': str(original_root)}; builtins.__import__ = guarded_import
    try: yield
    finally: builtins.__import__ = original_import; _AUDIT_STATE = old


def check(root=ROOT, archive_path=None, manifest_path=None):
    root = Path(root).resolve(); archive_path = Path(archive_path or root / ARCHIVE); manifest_path = Path(manifest_path or root / MANIFEST)
    m = load(manifest_path); validate_manifest(m)
    for row in m['repositoryDependencies']: check_bytes(safe_path(root, row['path']).read_bytes(), row)
    values = decode_archive(m, archive_path.read_bytes())
    frozen = verify_frozen_validation(root, values)
    old = json.loads(values[ORIGINAL_REPORT])
    if old['passed'] is not True or len(old['filesSha256']) != 20: raise ValueError('Historical saved report is not accepted')
    expected20 = {original_relative(k, m['originalExecutionRoot']): v for k, v in old['filesSha256'].items()}
    actual20 = {r[k] for r in m['selectedCells'] for k in ('cell', 'observation')}
    if set(expected20) != actual20: raise ValueError('Selected20 differs from historical frozen report')
    for name, wanted in expected20.items():
        if digest(values[name]) != wanted: raise ValueError('Historical selected raw binding differs')
    if digest(values[WHEEL]) != old['canonicalWheelSha256'] or digest(values[SDIST]) != old['sdistSha256']:
        raise ValueError('Historical distribution binding differs')
    with zipfile.ZipFile(io.BytesIO(values[WHEEL])) as wheel:
        metadata = BytesParser().parsebytes(wheel.read(next(n for n in wheel.namelist() if n.endswith('.dist-info/METADATA'))))
    if metadata['Name'] != 'py-elk' or metadata['Version'] != '0.0.1a0': raise ValueError('Historical artifact identity differs')
    with tempfile.TemporaryDirectory(prefix='pyelk-platform-evidence-') as temporary:
        temp = Path(temporary); extracted = temp / 'archive'; staged = temp / 'selected'; verified = temp / 'verification'; verified.mkdir()
        for name, raw in values.items():
            path = safe_path(extracted, name); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        for row in m['selectedCells']:
            folder = staged / row['id']; folder.mkdir(parents=True)
            cell = json.loads(values[row['cell']]); kind = 'sdist' if row['id'].endswith('-sdist') else 'wheel'
            if cell['id'] != row['id']: raise ValueError('Selected cell ID binding differs')
            if cell['artifactKind'] != kind or cell['artifactSha256'] != digest(values[SDIST if kind == 'sdist' else WHEEL]):
                raise ValueError('Cell artifact identity differs')
            for key in ('cell', 'observation'): (folder / (key + '.json')).write_bytes(values[row[key]])
            command_records = []
            base = PurePosixPath(row['cell']).parent
            for name in row['commands']:
                suffix = PurePosixPath(name).relative_to(base).as_posix(); target = safe_path(folder, suffix); target.parent.mkdir(exist_ok=True); target.write_bytes(values[name])
                if name.endswith('/command.json'): command_records.append(json.loads(values[name]))
            for command in cell['commands']:
                if not any(json.dumps(command, sort_keys=True) == json.dumps(r, sort_keys=True) for r in command_records):
                    raise ValueError('Cell command not bound to actual saved command.json')
        with offline_guard(root, m['originalExecutionRoot']):
            sys.path.insert(0, str(root / 'scripts')); sys.path.insert(0, str(root / 'tools/reference'))
            verifier = importlib.import_module('validate_full_platform')
            if Path(verifier.__file__).resolve() != (root / 'scripts/validate_full_platform.py').resolve(): raise ValueError('Verifier imported from another checkout')
            args = SimpleNamespace(wheel=extracted / WHEEL, sdist=extracted / SDIST, request=extracted / REQUEST, oracle=extracted / ORACLE, out=verified)
            with redirect_stdout(io.StringIO()): verifier.verify_saved([staged], args)
            current = load(verified / 'report.json')
            a = sorted(old['cells'], key=lambda r: r['id']); b = sorted(current['cells'], key=lambda r: r['id'])
            if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True): raise ValueError('Recomputed cells differ from historical saved audit')
    return {'schema': 'pyelk-offline-platform-evidence-check/v1', 'passed': True, 'version': '0.0.1a0', 'baseline': m['baseline'],
            'currentReleaseCertification': False, 'frozenValidation': frozen, 'wheelCells': 8, 'sdistRepresentativeCells': 2,
            'runtimeFilesPerCell': 208, 'selectedRawFiles': 20, 'archivedFiles': len(values),
            'canonicalWheelSha256': old['canonicalWheelSha256'], 'sdistSha256': old['sdistSha256'],
            'archiveSha256': digest(archive_path.read_bytes()), 'manifestSha256': digest(manifest_path.read_bytes()),
            'rawShapeHashDifferencesPreserved': True, 'cells': current['cells'],
            'executionGuards': ['pyelk import denied', 'subprocess execution denied', 'original test-runs/.local reads denied'],
            'productExecutions': 0, 'sourceExecutions': 0, 'installations': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__); modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--seal-archive', action='store_true'); modes.add_argument('--check', action='store_true')
    parser.add_argument('--archive', type=Path); parser.add_argument('--manifest', type=Path); parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = seal_archive(archive_path=args.archive, manifest_path=args.manifest) if args.seal_archive else check(archive_path=args.archive, manifest_path=args.manifest)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('x', encoding='utf8') as stream: json.dump(result, stream, indent=2)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__': main()
