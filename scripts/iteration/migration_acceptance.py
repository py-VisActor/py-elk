"""Whole-migration requirement accounting from byte-bound saved observations.

This is an offline acceptance audit, never a layout, installation, benchmark,
platform recapture or a replacement for the original frozen full execution.
Run after the separate M6/M7/finite-branch/platform evidence owners freeze.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import tomllib

ROOT=Path(__file__).resolve().parents[2]
JSON=Path('docs/iterations/E20_E21_ACCEPTANCE.json')
MD=JSON.with_suffix('.md')


def require(condition,message):
    if not condition:
        raise ValueError(message)


def load(name):
    return json.loads((ROOT/name).read_bytes())


def binding(name):
    raw=(ROOT/name).read_bytes()
    return {'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


def module(name):
    path=ROOT/'scripts/iteration'/name
    spec=importlib.util.spec_from_file_location('_migration_acceptance_'+path.stem,path)
    result=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=result
    spec.loader.exec_module(result)
    return result


def validated(name, maker, path):
    value=maker()
    canonical=lambda item:json.dumps(item,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))
    require(canonical(value)==canonical(load(path)),name+' differs from actual saved-evidence recomputation')
    return value


def check_publication(publication, payload, wheel, sdist, download, audit):
    """Connect actual uploaded/downloaded artifacts, not prepared local builds."""
    names=('py_visactor_elk-0.1.0-py3-none-any.whl','py_visactor_elk-0.1.0.tar.gz')
    expected={names[0]:payload['wheel']['sha256'],names[1]:sdist['artifactSha256']}
    require(publication['uploadedArtifactsSha256']==download['expectedArtifactsSha256']
            ==audit['publishedArtifactsSha256']==expected,'Actual publication artifact SHA links differ')
    require(wheel['artifactSha256']==wheel['wheelSha256']==sdist['wheelSha256']==expected[names[0]]
            and wheel['sdistSha256']==sdist['sdistSha256']==expected[names[1]],
            'Actual published wheel/sdist installations refer to different bytes')
    require(download['passed'] is True and audit['passed'] is True
            and audit['uploadedArtifactsEqualPyPIDownloadsByteForByte'] is True,
            'Actual upload/download audit did not pass')


def check_performance(profiles):
    algorithms=('fixed','box','random','layered','mrtree','radial','force','stress',
                'disco','sporeOverlap','sporeCompaction','rectpacking')
    key=lambda row:(row['algorithm'],row['nodes'],json.dumps(row['options'],sort_keys=True,separators=(',',':')))
    expected={(name,size,'{}')for name in algorithms for size in (8,32,96)}
    expected|={('force',size,'{"force.model":"EADES"}')for size in (8,32,96)}
    require(len(profiles)==39 and {key(row)for row in profiles}==expected,
            'Actual performance profile denominator differs')
    for row in profiles:
        hashes=[sample['resultSha256']for sample in row['samples']]
        require(len(hashes)==5 and all(type(value)is str and len(value)==64
                and all(c in '0123456789abcdef'for c in value)for value in hashes)
                and len(set(hashes))==1,'Actual performance determinism hash set differs')


def recheck_option_ledger():
    """Recompute original effects in an explicit temporary archive restoration."""
    evidence=module('option_evidence.py');coverage=module('option_coverage.py')
    manifest_path=ROOT/'references/full-native-closure/options.manifest.json'
    manifest=json.loads(manifest_path.read_bytes())
    with tempfile.TemporaryDirectory(prefix='pyelk-option-final-')as folder:
        destination=Path(folder)
        for item in manifest['files']:
            if item['storage']!='repository':
                continue
            raw=(ROOT/item['path']).read_bytes();evidence.check_bytes(raw,item)
            target=evidence.safe_path(destination,item['path']);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw)
        verified=evidence.restore(manifest_path,ROOT/manifest['archive']['path'],destination)
        coverage.ROOT=destination;coverage.LEDGER=destination/'docs/option-coverage.json'
        coverage.ROOT_MAPS[:]=[(manifest['originalExecutionRoot'],destination)]
        saved=load('docs/option-coverage.json')
        result=coverage.build([Path(path)for path in saved['effectReports']])
        require(json.dumps(result,sort_keys=True,allow_nan=False)==json.dumps(saved,sort_keys=True,allow_nan=False),
                'Frozen option effects differ from actual saved-evidence recomputation')
    return {'verifiedFiles':verified['verifiedFiles'],'summary':result['summary'],
            'temporaryRestoreOnly':True,'oldWorkspaceFallback':False,'productExecutions':0}


def recheck_returned_calls(m6_module,m6,m7_module,m7):
    """Apply existing whole-output/input policies to sealed normal raw pairs.

    Source errors, nonfinite outputs and entropy trajectories keep their old
    separate observations; they are not normal coordinate passes here.
    """
    sys.path.insert(0,str(ROOT/'scripts'))
    from layout_checks import diff
    from iteration.check_layered_saved import project_hierarchy_shape_hashes
    groups={'M6-public72-normal':[],'M7-provider-public-normal':[]}
    e6=m6_module.Evidence();e7=m7_module.Evidence()
    for call in m6['public72']['calls']:
        if call['sourceOutcome']=='returned'and call['nativeOutcome']=='returned':
            groups['M6-public72-normal'].append((e6,call))
    for calls in m7['public151']['algorithms'].values():
        groups['M7-provider-public-normal'].extend((e7,call)for call in calls if call['status']=='PASS')
    counts={}
    for name,calls in groups.items():
        require(bool(calls),'A required public raw pair group is empty')
        for reader,call in calls:
            values={key:reader.json(call[key]['path'],call[key]['sha256'])
                    for key in ('request','reference','native')}
            request,source,native=[values[key]for key in ('request','reference','native')]
            require(source['outcome']==native['outcome']=='returned','Normal raw pair outcome differs')
            for key,after in (('graph','inputAfter'),('constructor','constructorAfter'),('layoutArguments','argumentsAfter')):
                require(diff(request[key],native[after],tolerant=False)['passed'],
                        'Actual caller input policy differs: '+call['id'])
            projected=copy.deepcopy(source['result']);adaptations=[];violations=[]
            project_hierarchy_shape_hashes(request['graph'],projected,native['result'],
                                          adaptations=adaptations,violations=violations)
            require(not violations and diff({'result':projected},{'result':native['result']},tolerant=True)['passed'],
                    'Actual normal whole-output comparison differs: '+call['id'])
        counts[name]=len(calls)
    return {'groups':counts,'SourceErrorsOrEntropyPromoted':False,
            'comparison':'Existing hierarchy-owned generated-H projection and coordinate1e-6/1e-9; other fields exact',
            'productExecutions':0}


def build():
    # Producers check byte-bound original comparisons and re-evaluate their
    # selected states/geometry. Whole normal outputs and the frozen effects
    # ledger are independently recalculated below; no product is rerun.
    branches=validated('Finite branches',module('declared_branch_matrix.py').build,
                       'docs/iterations/FULL_DECLARED_BRANCH_MATRIX.json')
    m6_module=module('e13_e15_acceptance.py')
    m6=validated('M6',m6_module.make,
                 'docs/iterations/E13_E15_ACCEPTANCE.json')
    m7_module=module('e16_e19_acceptance.py')
    m7=validated('M7',m7_module.make,
                 'docs/iterations/E16_E19_ACCEPTANCE.json')
    role_module=module('option_roles.py')
    roles_saved=load('docs/iterations/FULL_OPTION_ROLES.json')
    roles=validated('Option roles',lambda:role_module.build(branch_matrix=roles_saved.get('branchMatrixPath')),
                    'docs/iterations/FULL_OPTION_ROLES.json')
    original_effects=recheck_option_ledger()
    public_rechecks=recheck_returned_calls(m6_module,m6,m7_module,m7)
    performance=m7_module.Evidence().json(m7['performance39']['report']['path'],m7['performance39']['report']['sha256'])
    check_performance(performance['profiles'])
    platform=module('platform_evidence.py').check(ROOT)
    require(platform['passed'] is True and platform['version']=='0.0.1a0',
            'Platform evidence must retain its actual executed baseline version')
    require((platform['wheelCells'],platform['sdistRepresentativeCells'])==(8,2),
            'Platform cell denominator differs')
    full=platform['frozenValidation']
    require((full['steps'],full['testMethods'])==(37,917),'Frozen full command/log denominator differs')

    ready=load('docs/releases/0.1.0-readiness.json')
    def bound(row):
        require(binding(row['path'])['sha256']==row['sha256'],'Bound release evidence changed: '+row['path'])
        return load(row['path'])
    frozen=bound(ready['frozenValidation'])
    delta=bound(ready['candidateDelta'])
    checked=bound(ready['candidateDeltaValidation'])
    require(frozen['inputsUnchanged'] is True and frozen['changedDuringExecution']==[],
            'Original full execution changed its inputs')
    require([row['name']for row in frozen['commands']]==frozen['plannedSteps']
            and all(type(row['exitCode'])is int and row['exitCode']==0 and row['timedOut'] is False
                    for row in frozen['commands']),'Original full execution did not finish every command')
    release=module('release_readiness.py')
    current=release.validate_delta(ROOT,frozen,delta,checked,ready['candidateDelta']['sha256'])
    require(len(current)==208,'Current runtime payload denominator differs')
    project=tomllib.loads((ROOT/'pyproject.toml').read_text('utf-8'))['project']
    wheel=bound(ready['wheelInstallation']);sdist=bound(ready['sdistInstallation'])
    release.validate_distribution(project,delta,checked,(wheel,sdist))
    for name,expected in delta['metadataCandidateSha256'].items():
        require(binding(name)['sha256']==expected,'Reviewed release metadata changed: '+name)
    publication=load('docs/releases/evidence/published-0.1.0/publication.json')
    actual_wheel=load('docs/releases/evidence/published-0.1.0/wheel-installed.json')
    actual_sdist=load('docs/releases/evidence/published-0.1.0/sdist-installed.json')
    check_publication(publication,m7['publishedPayload'],actual_wheel,actual_sdist,
                      load('docs/releases/evidence/published-0.1.0/verification.json'),
                      load('docs/releases/evidence/published-0.1.0/independent-publication-audit.json'))
    require(all(publication[key] is True for key in ('published','downloadVerified','wheelInstalled','sdistInstalled')),
            'Actual publication/download/install proof is incomplete')
    require(publication['version']==project['version']=='0.1.0'
            and publication['distributionName']==project['name']=='py-visactor-elk',
            'Published distribution identity differs')
    require(m7['publishedPayload']['runtimeCount']==208
            and m7['publishedPayload']['runtimeByteEqualityRechecked'] is True
            and m6['publishedRuntime']['runtime208CurrentByteExact'] is True,
            'Current implementation is not the actually published payload')

    metadata=load('tests/fixtures/suites/full-native-core/metadata-expected.json')['expectedQueries']['default']
    catalogue={key:len(metadata[key])for key in ('algorithms','options','categories')}
    require(catalogue=={'algorithms':12,'options':243,'categories':8},'Actual catalogue denominator differs')
    require(len(roles['rows'])==243 and {row['id']for row in roles['rows']}=={row['id']for row in metadata['options']},
            'Option-role audit does not enumerate the complete source catalogue')
    require(branches['denominator']['coreFactories']==90
            and branches['denominator']['supplementalEnumRows']==121,'Finite branch denominator differs')
    require(not branches['summary']['unwitnessedCoreIds'],'Unwitnessed required core factories remain')
    remaining=m6['finiteRemainingWork']['unwitnessedIds']
    m6_states={row['id']:row['status']for row in m6['iterations']}
    m7_states={row['id']:row['status']for row in m7['iterations']}
    m6_complete=all(m6_states.get(key)=='met_scoped'for key in ('E13','E14','E15')) and not remaining
    m7_complete=all(m7_states.get(key) in ('met_scoped','met_scoped_with_numeric_diagnostics')
                    for key in ('E16','E17','E18','E19')) and not m7['minimumRemainingGaps']
    plan=load('docs/iteration-plan.json')
    earlier={row['id']:row['status']for row in plan['iterations']if int(row['id'][1:])<=19}
    require(set(earlier)=={'E'+str(number).zfill(2)for number in range(1,20)},
            'Prerequisite iteration denominator differs')

    def row(identifier, passed, evidence, scope):
        return {'id':identifier,'status':'met_scoped'if passed else'pending',
                'evidence':evidence,'scope':scope}
    requirements=[
      row('M8-01-api-json',True,['M6.corePublic','M6.public72','M7.hostLifecycle'],
          'Actual public recursive/topdown/registry/coordinate calls and real native scheduling, cancellation, close, deadline and recovery; no JS worker API emulation.'),
      row('M8-01-catalogue',True,['metadata-expected.json','OptionRoles.rows','M7.publishedPayload'],
          'Exact complete12/243/8 declaration sets, installed queries, aliases/typed parsing and per-option role/verification states. Registration is not243 complete semantic effects.'),
      row('M8-01-layered',m6_complete,['M6.requirements','FiniteBranches.rows','FiniteBranches.supplementalRows'],
          'All explicit M6 requirements and finite90core/121enum accounting, including separately justified Source/host boundaries. Helper/config/route evidence is not whole geometry or every internal conditional.'),
      row('M8-01-other-algorithms',m7_complete,['M7.criteria','M7.public151','M7.nonLayered52'],
          'Eleven other providers individually assessed; Source errors/nonfinite/seed0 entropy and private numeric diagnostics remain separate.'),
      row('M8-01-terminal-ledger',True,['OptionRoles.rows','M6.retainedBoundaries','M7.optionLedger'],
          'All declared items list actual implementation/evidence scope, unverified effects and differences; no unverified item is upgraded by a green aggregate or enum accounting.'),
      row('M8-02-original-full',True,['Platform.frozenValidation','release-readiness.validate_delta'],
          'Original full37steps/917test logs are hash-checked, with its original skip and0.0.1a0 input fingerprints. Current version/MrTree repair has explicit affected checks; old execution is not relabelled current.'),
      row('M8-02-platform',True,['Platform.cells','M7.publishedPayload.installations','M7.MrTreeRepair'],
          'Saved actual Windows/Linux3.11-3.14 wheel8cells and2sdist representatives, plus actual published Windows wheel/sdist/Linux wheel and affected repair checks. No unmeasured Cartesian algorithm/platform/options guarantee.'),
      row('M8-02-state-scale',True,['M7.hostLifecycle','Platform.cells','M7.MrTreeRepair'],
          'Real OS CPU/process/lease evidence, recovery and resource boundaries; preserved1500-level cases and finite measured scales, no universal memory/latency bound.'),
      row('M8-02-performance-quality',True,['M7.performance39','M7.publishedMrTreePerformanceDelta','M7.independentGeometry','M6.geometryDelta24'],
          'Actual39profiles/195formal samples plus only affected MrTree3profiles/15samples, measured resources/quality/determinism; independent geometry retains PARTIAL/NOT_ASSESSED and numeric differences.'),
      row('M8-03-published-candidate',True,['M7.publishedPayload','publication.json','release-readiness.validate_distribution'],
          'Actual0.1.0 already contains all196modules/208runtime files and fixed license notices. Current runtime is byte-identical; post-publication validation/documents do not require an artificial new version or overwrite0.1.0.'),
      row('M8-03-download',True,['publication.json','M7.publishedPayload.installations'],
          'Actual upload/PyPI index/download artifact hashes and external wheel/sdist installation are bound separately from local prepared artifacts.'),
      row('iteration-dependencies',all(value=='complete'for value in earlier.values()),['iteration-plan.json'],
          'E01-E19 completion is independently recorded before closing E20/E21; py-mermaid I0-I3 remain explicitly separate.')]
    paths=['docs/TASKS.md','docs/ITERATION_PLAN.md','docs/iterations/E13_E15_ACCEPTANCE.json',
      'docs/iterations/E16_E19_ACCEPTANCE.json','docs/iterations/FULL_DECLARED_BRANCH_MATRIX.json',
      'docs/iterations/FULL_OPTION_ROLES.json','docs/option-coverage.json',
      'references/full-native-closure/options.manifest.json','references/full-native-closure/branches.manifest.json',
      'references/full-native-closure/advanced.manifest.json','references/full-native-closure/algorithms.manifest.json',
      'references/full-native-closure/platform.manifest.json','docs/releases/0.1.0-readiness.json',
      'docs/releases/evidence/published-0.1.0/publication.json','pyproject.toml']
    return {'schema':'pyelk-whole-migration-acceptance/v1',
      'completeWithinDeclaredScopes':all(x['status']=='met_scoped'for x in requirements),
      'requirements':requirements,'catalogue':catalogue,'currentRuntimeFiles':len(current),
      'actualPublishedVersion':'0.1.0','frozenFull':full,
      'savedPublicRechecks':public_rechecks,'savedOptionEffectsRecheck':original_effects,
      'savedPerformanceDeterminism':{'profiles':39,'formalHashesPerProfile':5,'allStable':True},
      'finiteBranches':{'core':90,'enum':121,'remaining':remaining,'statuses':branches['summary']['supplementalStatuses']},
      'optionEffects':m7['optionLedger']['summary'],
      'knownBoundaries':['Source errors/nonfinite/seed0 entropy retain their outcomes',
        '8Source raw factories have explicit native exception-name differences',
        'MrTree Source RangeError versus native RecursionError is a documented termination repair',
        'ADR0010 retains23internal identity-order differences; stable-ID geometry is a separate check',
        'Radial11private objectives retain up to2ULP strict differences without tolerance widening',
        'PARTIAL/unverified effects remain unverified; no infinite-input or all-combination proof'],
      'evidence':[binding(path)for path in paths],
      'newProductExecutions':0,'newSourceExecutions':0,'newFullExecution':False,
      'mermaidIntegration':'separate_not_required'}


def markdown(data):
    lines=['# E20／E21 逐条件完成审计','','本清单从原始保存材料重算；不执行布局、Source、安装、性能或跨平台任务。',
      '','| 原条件 | 状态 | 实际证明范围 |','| --- | --- | --- |']
    lines.extend('| '+row['id']+' | '+row['status']+' | '+row['scope']+' |'for row in data['requirements'])
    lines+=['','完整 JSON 保留各证据文件 SHA、实际版本、有限枚举状态及仍未验证的选项效果。',
      '','```shell','python scripts/iteration/migration_acceptance.py --check --require-complete','```',
      '','这是最终变更证据和完成条件的离线审核，不是把旧37步全量标成新执行，也不将部分评估改为通过。',
      '已发布0.1.0的实际208运行字节与当前源码一致；发行文档见 [0.1.0](../releases/0.1.0.md)。',
      '','保留边界：','']+['- '+value for value in data['knownBoundaries']]+['']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--build',action='store_true');modes.add_argument('--check',action='store_true')
    parser.add_argument('--require-complete',action='store_true')
    args=parser.parse_args();data=build()
    raw=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n';md=markdown(data)
    if args.build:
        (ROOT/JSON).write_text(raw,encoding='utf-8',newline='\n')
        (ROOT/MD).write_text(md,encoding='utf-8',newline='\n')
    else:
        require((ROOT/JSON).read_text('utf-8')==raw,'Whole-migration JSON differs from actual audit')
        require((ROOT/MD).read_text('utf-8')==md,'Whole-migration Markdown differs from actual audit')
    if args.require_complete:
        require(data['completeWithinDeclaredScopes'],'Explicit migration requirements remain incomplete')
    print(json.dumps({'completeWithinDeclaredScopes':data['completeWithinDeclaredScopes'],
                      'pending':[row['id']for row in data['requirements']if row['status']=='pending'],
                      'newProductExecutions':0,'newSourceExecutions':0,'newFullExecution':False}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
