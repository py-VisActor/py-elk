"""Validate reviewed release inputs without building or publishing.

Used by both selected CI and the privileged publication workflow. The frozen
development run retains its actual version; release evidence is a delta plus
new installed-candidate observations, never a relabelled old execution.
"""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

REPAIR_ID='mrtree-second-walk-active-path/v1'
MODULE='pyelk/algorithms/mrtree.py'
VERSION_MODULE='pyelk/__init__.py'
BASELINE_WHEEL_SHA='494f877ce6a3fa2480ba1602bf96bbac2bff64a3a01f6ecf78600ab15d28eba7'
BUNDLE_SHA='b1032b7cfd2a57c54c6f0e8369d7665e19a579954f7cd20a6dae28f1912ea0d7'


def require(condition,message):
    if not condition:raise ValueError(message)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def safe_path(root,name):
    require(type(name)is str and name and '\\'not in name and ':'not in name,'Evidence path is not repository-relative')
    parts=PurePosixPath(name);target=(Path(root)/parts).resolve()
    require(not parts.is_absolute()and all(p not in ('','.','..')for p in name.split('/'))
            and target.is_relative_to(Path(root).resolve()),'Evidence path escapes repository')
    return target


def bound_bytes(root,row):
    raw=safe_path(root,row['path']).read_bytes()
    require(digest(raw)==row['sha256'],'Evidence bytes differ: '+row['path'])
    return raw


def bound_json(root,row):return json.loads(bound_bytes(root,row))


def version_before(raw):
    """Reconstruct baseline bytes changing only the literal version value."""
    tree=ast.parse(raw)
    values=[n.value for n in tree.body if isinstance(n,ast.Assign)and len(n.targets)==1
            and isinstance(n.targets[0],ast.Name)and n.targets[0].id=='__version__']
    require(len(values)==1 and isinstance(values[0],ast.Constant)and values[0].value=='0.1.0','Expected one candidate version literal')
    value=values[0];lines=raw.splitlines(keepends=True)
    start=sum(map(len,lines[:value.lineno-1]))+value.col_offset
    end=sum(map(len,lines[:value.end_lineno-1]))+value.end_col_offset;literal=raw[start:end]
    require(literal in (b'"0.1.0"',b"'0.1.0'"),'Version promotion changed literal formatting')
    return raw[:start]+literal[:1]+b'0.0.1a0'+literal[-1:]+raw[end:]


def repair_diff(before,after):
    return ''.join(difflib.unified_diff(before.decode('utf8').splitlines(keepends=True),
        after.decode('utf8').splitlines(keepends=True),fromfile='before/'+MODULE,tofile='after/'+MODULE)).encode('utf8')


def validate_distribution(project,delta,checked,installations=()):
    """Missing historical fields mean py-elk, never the newly named candidate."""
    name=delta.get('distributionName','py-elk')
    require(name in ('py-elk','py-visactor-elk'),'Unapproved distribution name')
    require(project['name']==name,'Project distribution differs from candidate metadata')
    require(checked.get('distributionName','py-elk')==name,'Delta validation is bound to another distribution')
    for observation in installations:
        require(observation.get('distributionName','py-elk')==name,'Installation receipt is bound to another distribution')
        require(observation['installedObservation'].get('distributionName','py-elk')==name,
                'Installed distribution identity is absent or differs from candidate')
    return name


def check_repair_receipt(root,binding,kind,module_sha,current,review):
    receipt=bound_json(root,binding)
    native_schema={'cycle-termination':'pyelk-mrtree-cycle-termination/v1',
                   'valid-tree-regression':'pyelk-mrtree-valid-tree-regression/v1'}
    if receipt['schema']==native_schema[kind]:
        cases=[{'id':kind,**{key:receipt[key]for key in('request','reference','native')},'nativeCommand':receipt['command']}]
    else:
        require(receipt['schema']=='pyelk-runtime-repair-check/v1'and receipt['repairId']==REPAIR_ID
                and receipt['kind']==kind,'Runtime repair check schema/kind differs')
        cases=receipt['cases']
    require(receipt['candidateModuleSha256']==module_sha,'Repair check used another module')
    require(type(cases)is list and bool(cases),'Repair check has no actual cases')
    require(len({row['id']for row in cases})==len(cases),'Duplicate repair check case')
    if kind=='cycle-termination':require(len(cases)==1,'Cycle repair check must bind the one affected case')
    source_hashes={name.removeprefix('pyelk/'):sha for name,sha in current.items()if name.endswith('.py')}
    for case in cases:
        request=bound_json(root,case['request']);reference=bound_json(root,case['reference'])
        native=bound_json(root,case['native']);command=bound_json(root,case['nativeCommand'])
        require(reference['requestSha256']==native['requestSha256']==case['request']['sha256'],'Repair request binding differs')
        require(reference['schema']==native['schema']=='py-elk-layout-observation/v1','Unknown repair observation schema')
        require(reference['engine']['name']=='elkjs'and reference['engine']['version']=='0.12.1'
                and reference['engine']['entrypointSha256']==BUNDLE_SHA,'Repair reference is not the locked engine')
        require(native['engine']['name']=='pyelk'and native['engine']['version']=='0.1.0'
                and native['engine']['sourceFilesSha256']==source_hashes
                and native['engine']['sourcesUnchanged']is True,'Repair native source closure differs')
        require(type(command['exitCode'])is int and command['exitCode']==0 and command['timedOut']is False,
                'Repair command failed or required a deadline')
        require(native['termination']['outcome']=='returned','Repair worker cleanup failed')
        require(request['graph']['layoutOptions']['org.eclipse.elk.algorithm']=='mrtree','Repair case did not select MrTree')
        if kind=='cycle-termination':
            require(reference['outcome']=='threw'and reference['error']=={
                'name':'RangeError','message':'Maximum call stack size exceeded'},'Cycle Source failure differs')
            require(native['outcome']=='threw'and native['error']==review['expectedNativeError'],'Cycle native error differs from reviewed behavior')
        else:
            sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
            from validate_full_layered import compare_observations
            require(compare_observations(safe_path(root,case['request']['path']),reference,native)['passed']is True,
                    'Valid-tree whole-output regression differs')


def validate_delta(root,frozen,delta,checked,delta_sha):
    """Read actual payload/repair evidence; never execute/import the product."""
    root=Path(root)
    require(delta['candidateVersion']=='0.1.0'and delta['baselineVersion']=='0.0.1a0','Candidate delta version differs')
    require(delta['baselineExecutionReusedForCandidate']is False and checked['baselineExecutionRebound']is False,'Historical execution was rebound')
    require(delta['baselineWheelSha256']==checked['baselineWheelSha256']==BASELINE_WHEEL_SHA,'Frozen baseline wheel differs')
    payload={p.relative_to(root/'src').as_posix():p.read_bytes()for p in(root/'src/pyelk').rglob('*')
             if p.is_file()and '__pycache__'not in p.parts and(p.suffix=='.py'or p.name=='py.typed'or '_licenses'in p.parts)}
    current={name:digest(raw)for name,raw in payload.items()}
    require(current==delta['runtimeFilesSha256']and len(current)==208,'Release source differs from reviewed candidate')
    require(sum(name.endswith('.py')for name in current)==196,'Python module denominator differs')
    baseline={name:frozen['inputFilesSha256'].get('src/'+name)for name in current}
    require(all(type(sha)is str and len(sha)==64 for sha in baseline.values()),'Frozen baseline lacks a complete runtime payload')
    require(set('src/'+name for name in current)<=set(delta['sourceOriginalSha256']),'Delta omits baseline runtime bindings')
    for name,sha in delta['sourceOriginalSha256'].items():
        require(frozen['inputFilesSha256'].get(name)==sha,'Frozen source differs from candidate baseline: '+name)
    require(digest(version_before(payload[VERSION_MODULE]))==baseline[VERSION_MODULE],
            'Initializer contains changes beyond its version literal')
    changed=sorted(name for name in current if current[name]!=baseline[name])
    schema=delta['schema']
    if schema=='py-elk-release-candidate-delta/v1':
        expected=[VERSION_MODULE];unchanged_modules=196
        require('runtimeRepair'not in delta and delta.get('validationMode','version-only')=='version-only','Legacy delta cannot approve a runtime repair')
    else:
        require(schema=='py-elk-release-candidate-delta/v2'and delta['validationMode']=='runtime-repair','Unknown candidate delta schema/mode')
        expected=[VERSION_MODULE,MODULE];unchanged_modules=195
        require(checked['schema']=='py-elk-release-candidate-delta-validation/v2'
                and checked['candidateDeltaSha256']==delta_sha,'Repair validation is bound to another delta')
        repair=delta['runtimeRepair'];require(repair['id']==REPAIR_ID,'Unknown runtime repair')
        before=bound_bytes(root,repair['beforeModule']);after=bound_bytes(root,repair['afterModule'])
        require(repair['beforeModule']['sha256']==baseline[MODULE]and repair['afterModule']['path']=='src/'+MODULE
                and repair['afterModule']['sha256']==current[MODULE],'Repair before/after source differs')
        require(checked['runtimeRepairModuleSha256']==current[MODULE]and checked['runtimeReexecuted']is True,'Repair validation lacks current-source execution')
        review=bound_json(root,repair['review'])
        require(review['schema']=='pyelk-runtime-repair-review/v1'and review['repairId']==REPAIR_ID
                and review['approved']is True,'Runtime repair has no approved diff review')
        require(review['beforeModuleSha256']==digest(before)and review['afterModuleSha256']==digest(after),'Repair review source hashes differ')
        require(bound_bytes(root,review['diff'])==repair_diff(before,after),'Reviewed repair diff differs from actual source')
        require(review['expectedNativeError']['name']=='RecursionError'
                and type(review['expectedNativeError']['message'])is str and review['expectedNativeError']['message'],'Repair error behavior is not explicit')
        require(set(repair['checks'])=={'cycleTermination','validTreeRegression'},'Missing or unrecognized repair checks')
        check_repair_receipt(root,repair['checks']['cycleTermination'],'cycle-termination',current[MODULE],current,review)
        check_repair_receipt(root,repair['checks']['validTreeRegression'],'valid-tree-regression',current[MODULE],current,review)
    require(changed==expected and delta['changedRuntimeFiles']==expected and checked['changedRuntimeFiles']==expected,
            'Runtime changed-file allowlist differs from actual frozen-byte delta')
    require(checked['passed']is True and type(checked['runtimeFiles'])is int and checked['runtimeFiles']==208
            and type(checked['normalizedPythonModules'])is int and checked['normalizedPythonModules']==unchanged_modules,
            'Candidate delta is not validated with the complete denominator')
    return current

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-only',action='store_true',help='Check only; never upload')
    parser.parse_args()
    import hashlib, json, pathlib, tomllib
    root = pathlib.Path(__file__).resolve().parents[2]
    def require(value, message):
        if not value: raise SystemExit(message)
    def record_file(row):
        name = pathlib.PurePosixPath(row['path'])
        raw = safe_path(root,row['path']).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == row['sha256'], 'Evidence bytes differ: ' + str(name))
        return json.loads(raw)
    ready = json.loads((root / 'docs/releases/0.1.0-readiness.json').read_bytes())
    require(ready['schema'] == 'py-elk-release-readiness/v1' and ready['status'] == 'READY', 'Root has not finalized actual release evidence')
    require(ready['releaseVersion'] == '0.1.0' and ready['featureImplementationComplete'] is True, 'Release readiness differs')
    plan = json.loads((root / 'docs/iteration-plan.json').read_bytes())
    require(plan.get('validationPolicy', {}).get('featureImplementationComplete') is True, 'Feature implementation is not complete')
    # E12 contains publication itself: requiring it complete would be circular.
    frozen = record_file(ready['frozenValidation'])
    require(frozen['schema'] == 'py-elk-development-check/v1' and frozen['status'] == 'DEVELOPMENT_CHECKS_PASS' and frozen['passed'] is True and frozen['fullValidation'] is True and frozen['checkMode'] == 'full', 'Frozen full validation did not pass')
    require(frozen['inputsUnchanged'] is True and frozen['changedDuringExecution'] == [], 'Frozen full validation inputs changed')
    require([c['name'] for c in frozen['commands']] == frozen['plannedSteps'] and bool(frozen['commands']), 'Frozen command denominator differs')
    require({'full-native-interfaces', 'full-native-host'} <= set(frozen['plannedSteps']), 'Current native checks are absent')
    require(all(type(c['exitCode']) is int and c['exitCode'] == 0 and c['timedOut'] is False for c in frozen['commands']), 'Frozen command failed')
    delta = record_file(ready['candidateDelta'])
    checked = record_file(ready['candidateDeltaValidation'])
    try:current=validate_delta(root,frozen,delta,checked,ready['candidateDelta']['sha256'])
    except(ValueError,KeyError,TypeError,OSError,SyntaxError)as error:raise SystemExit(str(error))from error
    for name, sha in delta['metadataCandidateSha256'].items():
        require(hashlib.sha256((root / name).read_bytes()).hexdigest() == sha, 'Release metadata differs from reviewed candidate: ' + name)
    project = tomllib.loads((root / 'pyproject.toml').read_text())['project']
    require(project['version'] == '0.1.0' and project['dependencies'] == [], 'Release project metadata differs')
    require('pyproject.toml'in delta['metadataCandidateSha256'],'Candidate metadata omits project identity binding')
    wheel = record_file(ready['wheelInstallation'])
    sdist = record_file(ready['sdistInstallation'])
    for observation in (wheel, sdist):
        actual = observation['installedObservation']
        require(observation['passed'] is True and actual['version'] == '0.1.0' and actual['modules'] == 196 and actual['metadata'] == [12, 243, 8] and actual['nodes'] == 20, 'Candidate installation did not pass')
    require(wheel['wheelSha256'] == checked['wheelSha256'] and wheel['sdistSha256'] == sdist['artifactSha256'] == checked['sdistSha256'], 'Candidate artifact receipts differ')
    require(wheel['runtimeFilesSha256']==current,'Installed wheel receipt is bound to another runtime payload')
    try:validate_distribution(project,delta,checked,(wheel,sdist))
    except(ValueError,KeyError,TypeError)as error:raise SystemExit(str(error))from error
    print('Frozen full validation, candidate delta, and actual wheel/sdist installations are ready')


if __name__=="__main__":main()
