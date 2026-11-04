"""Offline243-option evidence ledger; input/parser evidence never implies effects.

No product import, layout, oracle process or existing suite replay occurs here.
The old compatibility ledger is read neither as an oracle nor modified.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys

ROOT=Path(__file__).resolve().parents[2]
LEDGER=ROOT/'docs/option-coverage.json'
sys.path.insert(0,str(ROOT/'scripts'))
from layout_checks import diff


ROOT_MAPS=[]


def resolve_path(path):
    """Resolve actual inputs only inside this checkout; never search an old root."""
    text=str(path);windows=PureWindowsPath(text)
    if windows.drive and not windows.is_absolute():raise ValueError('Drive-relative evidence path is ambiguous: '+text)
    if windows.is_absolute():
        for before,after in ROOT_MAPS:
            try:suffix=windows.relative_to(PureWindowsPath(before))
            except ValueError:continue
            target=(after/Path(*suffix.parts)).resolve()
            break
        else:
            target=Path(text).resolve()
            if not target.is_relative_to(ROOT):raise ValueError('Unmapped original execution path: '+text)
    else:target=(ROOT/Path(path)).resolve()
    if not target.is_relative_to(ROOT):raise ValueError('Evidence path escapes current root: '+text)
    return target


def sha(path):return hashlib.sha256(resolve_path(path).read_bytes()).hexdigest()
def read(path):return json.loads(resolve_path(path).read_text('utf-8'))
def declared(path,name):
    module=ast.parse(path.read_text('utf-8'))
    return next(ast.literal_eval(node.value)for node in module.body if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in node.targets))
def relative(path):return resolve_path(path).relative_to(ROOT).as_posix()


def at_pointer(value,path):
    if path=='':return value
    if type(path)is not str or not path.startswith('/'):raise ValueError('Expected a JSON Pointer')
    for token in path[1:].split('/'):
        token=token.replace('~1','/').replace('~0','~')
        if type(value)is list:
            if not token.isascii()or not token.isdecimal()or str(int(token))!=token:raise ValueError('Invalid array pointer index')
            value=value[int(token)]
        elif type(value)is dict:value=value[token]
        else:raise ValueError('Pointer traverses a scalar')
    return value


def selected_values(value,pointers,*,ordered=False):
    if type(pointers)is not list or not pointers:raise ValueError('Effect evidence needs actual observation pointers')
    result=[at_pointer(value,pointer)for pointer in pointers]
    return result[0]if len(result)==1 and not ordered else result


def check_option_changes(changes,canonical,optionids):
    """A newly added options holder is a map delta, not an extra input field."""
    for change in changes:
        pieces=change['path'].split('/')
        if pieces[-1]in('layoutOptions','properties')and change['kind']in('unexpected','missing'):
            value=change['actual']if change['kind']=='unexpected'else change['expected']
            assert type(value)is dict and value
            assert all(canonical(key)in optionids for key in value)
        else:
            assert len(pieces)>=2 and pieces[-2]in('layoutOptions','properties')
            assert canonical(pieces[-1].replace('~1','/').replace('~0','~'))in optionids


def check_structure():
    """CI schema/current-bindings check, explicitly weaker than archived-effect audit."""
    ledger=read(LEDGER);metadata=read(ROOT/'references/metadata/options.json')
    ids=[row['id']for row in metadata]
    assert ledger['schema']=='pyelk-option-coverage/v1'and ledger['denominator']==243
    assert len(ids)==len(set(ids))==len(ledger['options'])==243
    assert [row['id']for row in ledger['options']]==ids
    declarations={row[0]:row for row in declared(ROOT/'src/pyelk/options/_generic_data.py','SCALAR_DECLARATIONS')}
    declarations.update({row[0]:row for row in declared(ROOT/'src/pyelk/options/_object_data.py','OBJECT_DECLARATIONS')})
    assert set(declarations)==set(ids)
    available=[];absent=[]
    for key,item in ledger['evidence'].items():
        name=Path(item['path']);target=(ROOT/name).resolve()
        assert not name.is_absolute()and target.is_relative_to(ROOT)
        assert type(item['sha256'])is str and len(item['sha256'])==64
        if target.is_file():
            assert sha(target)==item['sha256'],('Available evidence changed',key,item['path'])
            available.append(key)
        else:
            assert name.parts[0]=='test-runs',('Missing tracked evidence',key,item['path'])
            absent.append(key)
    for key,case in ledger['caseIndex'].items():
        target=(ROOT/case['request']).resolve();assert target.is_relative_to(ROOT)and sha(target)==case['requestSha256']
        assert type(case['wholeOutputMatched'])is bool and case['effectCoverageInferred']is False
    for row,meta in zip(ledger['options'],metadata,strict=True):
        name=row['id']
        assert row['metadata']['status']=='registered_fields_verified'and row['metadata']['type']==meta['type']
        assert row['metadata']['targets']==meta.get('targets',[])
        assert row['parser']['kind']==declarations[name][1]
        assert row['parser']['status']in('value_verified','source_factory_unavailable')
        assert row['parser']['status']==('source_factory_unavailable'if declarations[name][1]=='opaque'else'value_verified')
        assert type(row['effects']['completeOptionSemanticsVerified'])is bool and not row['effects']['completeOptionSemanticsVerified']
        for occurrence in row['publicInputOccurrences']:
            assert occurrence['case']in ledger['caseIndex']and type(occurrence['wholeOutputMatched'])is bool
        for kind,field in(('layout_geometry','layoutGeometry'),('runtime_state','runtimeState')):
            assertions=[a for a in row['effects']['assertions']if a['kind']==kind]
            assert row['effects'][field]==('scoped_verified'if assertions else'unverified')
        for assertion in row['effects']['assertions']:
            assert assertion['status']=='scoped_verified'and assertion['description']and assertion['scope']
            assert assertion['kind']in('layout_geometry','runtime_state','source_selection')
            if 'reportEvidence'not in assertion:
                assert all(key in assertion for key in('assertionEvidence','executionEvidence','sourceOracleEvidence'))
            for key,value in assertion.items():
                if key.endswith('Evidence'):assert value in ledger['evidence']
            if 'expected'in assertion:
                assert diff(assertion['expected'],assertion['actual'],tolerant=False)['passed']
                assert assertion['referencePointers']and assertion['nativePointers']
    rows=ledger['options']
    summary={'metadataVerified':243,'parserValueVerified':sum(v['parser']['status']=='value_verified'for v in rows),
        'sourceUnavailableRawFactories':sum(v['parser']['status']=='source_factory_unavailable'for v in rows),
        'optionsExplicitlyPresentInPublicSuites':sum(bool(v['publicInputOccurrences'])for v in rows),
        'layoutGeometryScoped':sum(v['effects']['layoutGeometry']=='scoped_verified'for v in rows),
        'runtimeStateScoped':sum(v['effects']['runtimeState']=='scoped_verified'for v in rows),'completeOptionSemantics':0}
    assert diff(summary,ledger['summary'],tolerant=False)['passed']
    return {'passed':True,'action':'check-structure','status':'STRUCTURE_AND_AVAILABLE_BINDINGS_PASS',
            'summary':summary,'availableEvidence':available,'unavailableArchivedEvidence':absent,
            'allArchivedEvidenceFilesAvailable':not absent,'fullArchivedEvidenceAuditComplete':False,
            'effectSourceDataRecomputed':False,'ledgerSha256':sha(LEDGER),'checkerSha256':sha(Path(__file__)),
            'productsExecuted':0,'referenceProcessesExecuted':0,
            'scope':'Schema and actual available file bindings only. Missing ignored archive evidence is disclosed; this is not a new runtime or effect certification.'}


def family(identifier):
    short=identifier.removeprefix('org.eclipse.elk.')
    if short.startswith('layered.'):
        parts=short.split('.')
        return 'layered.'+(parts[1]if len(parts)>1 else'core')
    first=short.split('.')[0]
    if first in('force','stress','mrtree','radial','disco','spore','polyomino','rectpacking','topdown','json','nodeSize','nodeLabels','edgeLabels','portLabels','portAlignment','spacing'):return first
    if first=='port' or first=='portConstraints':return'ports'
    return'core'


def owned_options(graph):
    pending=[('node',graph,'/graph')]
    while pending:
        kind,item,path=pending.pop()
        if type(item)is not dict:continue
        raw=item.get('layoutOptions');key='layoutOptions'
        if type(raw)is not dict:raw=item.get('properties');key='properties'
        if type(raw)is dict:
            for spelling,value in raw.items():yield spelling,value,path+'/'+key
        groups=('children','ports','labels','edges')if kind=='node'else('labels',)if kind in('port','edge')else()
        for group in groups:
            values=item.get(group,[])
            if type(values)is list:
                childkind={'children':'node','ports':'port','labels':'label','edges':'edge'}[group]
                pending.extend((childkind,value,path+'/'+group+'/'+str(i))for i,value in reversed(list(enumerate(values))))


def build(effect_reports=()):
    evidence={}
    def bind(name,path):
        path=resolve_path(path)
        evidence[name]={'path':relative(path),'sha256':sha(path)}
        return read(path)
    metadata=bind('officialMetadata','references/metadata/options.json')
    ids={row['id']for row in metadata};assert len(metadata)==len(ids)==243
    scalarpath=ROOT/'src/pyelk/options/_generic_data.py';objectpath=ROOT/'src/pyelk/options/_object_data.py'
    evidence['scalarDeclarations']={'path':relative(scalarpath),'sha256':sha(scalarpath)}
    evidence['objectDeclarations']={'path':relative(objectpath),'sha256':sha(objectpath)}
    scalars={row[0]:row for row in declared(scalarpath,'SCALAR_DECLARATIONS')}
    objects={row[0]:row for row in declared(objectpath,'OBJECT_DECLARATIONS')}
    assert len(scalars)==225 and len(objects)==18 and set(scalars)|set(objects)==ids
    parser=bind('parserFirstNative','test-runs/20261104-FULL/V/property-catalogue-01/catalogue-comparison.json')
    original=bind('parserFirstSource','test-runs/20261104-FULL/V/property-catalogue-01/catalogue-original.json')
    correction=bind('parserObserverCorrection','test-runs/20261104-FULL/V/property-catalogue-observer-02/catalogue-original.json')
    parser_request=bind('parserRequest','test-runs/20261104-FULL/V/property-catalogue-01/catalogue-request.json')
    parser_summary=bind('parserSavedRecheck','test-runs/20261104-FULL/V/property-catalogue-observer-02/report.json')
    assert parser_summary['valueComparison']['passed']and parser_summary['errorOutcomeAndMessageComparison']['passed']
    assert original['workerSha256']==correction['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert parser['oracleSha256']==evidence['parserFirstSource']['sha256']
    assert original['requestSha256']==evidence['parserRequest']['sha256']
    corrected={row['id']:row for row in correction['observation']}
    sources={row['id']:corrected.get(row['id'],row)for row in original['observation']}
    natives={row['id']:row for row in parser['actual']}
    parser_by_option=defaultdict(list)
    for case in parser_request['cases']:parser_by_option[case['option']].append(case)
    registration=bind('metadataRegistration','test-runs/20261104-FULL/V/typed-integrated-01/metadata-registration/comparison.json')
    assert registration['passed']and all(row['passed']for row in registration['publicMetadataGetterComparisons'].values())
    full=bind('frozenDevelopment','docs/releases/evidence/development-frozen/report.json')
    assert full['passed']and full['inputsUnchanged']and len(full['commands'])==37
    evidence['geometryAssertion']={'path':'tests/conformance/test_e07_native.py','sha256':sha(ROOT/'tests/conformance/test_e07_native.py'),
        'symbol':'E07NativeConformance.test_all_real_native_results_match_official_contract_geometry_and_original_ids'}
    assert full['inputFilesSha256']['tests/conformance/test_e07_native.py']==evidence['geometryAssertion']['sha256']
    evidence['geometryImplementation']={'path':'scripts/layout_checks.py','sha256':sha(ROOT/'scripts/layout_checks.py'),'symbol':'geometry'}
    bind('legacyGeometryCases','tests/fixtures/suites/E07/cases.json')
    e07_oracle=bind('legacyGeometryOracleIndex','tests/fixtures/suites/E07/oracle/index.json')
    bind('versionOnlyDelta','docs/releases/evidence/0.1.0-delta-validation.json')
    bdefs=bind('algorithmCases','tests/fixtures/suites/full-native-algorithms/cases.json')
    bcomparison=bind('algorithmComparison','test-runs/full-native-01/B/comparison-02.json')
    adefs=bind('layeredCases','tests/fixtures/suites/full-native-layered/cases.json')
    areports=[bind('layeredComparison'+str(i),'test-runs/20261104-HOST-19/A/full-layered-0'+str(i)+'/report.json')for i in(1,2,3)]
    bstatus={row['id']:row for row in bcomparison['rows']}
    astatus={row['id']:row for report in areports for row in report['cases']}
    case_index={};occurrences=defaultdict(list);unresolved=[]
    def canonical(spelling):
        if spelling in ids:return spelling
        if 'org.eclipse.'+spelling in ids:return'org.eclipse.'+spelling
        matches=[key for key in ids if key.endswith('.'+spelling)]
        return matches[0]if len(matches)==1 else None
    def record_case(prefix,definition,status,base):
        request=ROOT/base/definition['request'];raw=read(request)
        assert sha(request)==definition['requestSha256']
        key=prefix+':'+definition['id']
        passed=status.get('status')=='PASS'if prefix=='B'else status.get('status')=='matched'
        case_index[key]={'request':relative(request),'requestSha256':sha(request),'status':status['status'],
                         'wholeOutputMatched':passed,'referenceSha256':status['referenceSha256'],
                         'nativeSha256':status.get('nativeSha256',status.get('candidateSha256')),
                         'effectCoverageInferred':False}
        selected=raw.get('layoutArguments',{}).get('layoutOptions',raw.get('constructor',{}).get('defaultLayoutOptions',{}))
        source=list(owned_options(raw.get('graph')))
        if type(selected)is dict:source.extend((spelling,value,'/selectedGlobalOptions')for spelling,value in selected.items())
        for spelling,value,path in source:
            name=canonical(spelling)
            if name:occurrences[name].append({'case':key,'spelling':spelling,'path':path,'value':value,'wholeOutputMatched':passed})
            else:unresolved.append({'case':key,'spelling':spelling,'path':path})
    for case in bdefs['cases']:record_case('B',case,bstatus[case['id']],Path('tests/fixtures/suites/full-native-algorithms'))
    for case in adefs['cases']:record_case('A',case,astatus[case['id']],Path('tests/fixtures/suites/full-native-layered'))
    assert len(case_index)==223
    # Seven scoped spatial contracts already executed in the frozen full run.
    # This does not certify every value, algorithm or option interaction.
    spatial={
        'org.eclipse.elk.direction':'Given orientation and layer/rank direction are checked by the applicable geometry policy.',
        'org.eclipse.elk.padding':'Actual root/child bounds and specified four-side padding are checked under E07 geometry applicability.',
        'org.eclipse.elk.edgeRouting':'Orthogonal endpoints/sections/axis-aligned segments only; polyline/spline semantics require their own assertions.',
        'org.eclipse.elk.separateConnectedComponents':'Separated/unsplit weak component frames and actual per-component processor counts are checked.',
        'org.eclipse.elk.spacing.nodeNode':'Applicable same-layer node separation is checked under the frozen geometry policy.',
        'org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers':'Applicable between-layer rank spacing is checked under the frozen geometry policy.',
        'org.eclipse.elk.spacing.componentComponent':'Applicable separated component spacing is checked under the frozen component-frame policy.'}
    effects=defaultdict(list)
    for name,description in spatial.items():
        effects[name].append({'id':'frozen-e07-spatial:'+name,'kind':'layout_geometry','status':'scoped_verified',
          'description':description,'assertionEvidence':'geometryAssertion','executionEvidence':'frozenDevelopment',
          'sourceOracleEvidence':'legacyGeometryOracleIndex','scope':'Existing E07 applicable flat orthogonal cases, executed by the current native worker during frozen full validation. Not all enum values or advanced combinations.'})
    state_witnesses=[
      ('targetState','selected-global-targets','generic-targets-oracle-01','test-runs/20261104-HOST-08/V/generic-targets-oracle-01/observation.json',
       ['font.name','priority','nodeSize.constraints','layered.crossingMinimization.semiInteractive'],
       'Actual local/global target application across9 owned holder kinds, explicit presence, local override and EnumSet sharing; not a layout effect.'),
      ('integerState','integer-provenance','integer-original-02','test-runs/20261104-HOST-09/root/integer-original-02/observation.json',
       ['priority','layered.considerModelOrder.groupModelOrder.crossingMinimizationId'],
       'Actual imported Integer provenance: local uncached identities, global sharing, cached/default0, removal and shallow snapshot tokens; not a geometry effect.'),
      ('snapshotState','typed-snapshot','snapshot-original-01','test-runs/20261104-HOST-08/root/snapshot-original-01/observation.json',
       ['nodeSize.minimum','nodeLabels.padding','nodeSize.constraints','resolvedAlgorithm','priority','spacing.individual'],
       'Actual MapHolder copy shares typed values and preserves mutation visibility while maps/replacements remain independent; not layout or ID cloning.'),
      ('chainState','object-parser-clone','object-original-01','test-runs/20261104-HOST-08/root/object-original-01/observation.json',
       ['bendPoints','junctionPoints'],
       'Actual configured chains clone shallowly with shared Vec references; junction default independently materializes and caches on each holder. Parse-only points are not an effect proof.'),
      ('ownerDefaultState','snapshot-owner-defaults','snapshot-default-original-01','test-runs/20261104-HOST-09/root/snapshot-default-original-01/observation.json',
       ['padding','nodeSize.options','aspectRatio','port.borderOffset'],
       'Actual new-holder Core type4 clone/cache and non-type4 shared/default-null presence rules; no metadata-default injection and no algorithm-specific geometry claim.')]
    for key,group,source_id,source_path,names,description in state_witnesses:
        report=bind(key,'test-runs/20261104-FULL/V/typed-integrated-01/'+group+'/comparison.json')
        source=bind(key+'Source',source_path)
        assert report['passed']is True
        comparison=report.get('comparison',report.get('difference'))
        if comparison is not None:assert comparison['passed']is True and not comparison['differences']
        else:assert not report['differences']
        assert source['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
        if 'oracleSha256'in report:assert report['oracleSha256']==evidence[key+'Source']['sha256']
        for short in names:
            name='org.eclipse.elk.'+short;assert name in ids
            effects[name].append({'id':key+':'+name,'kind':'runtime_state','status':'scoped_verified',
                'description':description,'reportEvidence':key,'sourceOracleEvidence':key+'Source',
                'scope':'Actual source/native state witness only, with complete comparison report. Not a selected layout branch or numeric layout effect.'})
    effect_attempts=defaultdict(list)
    if effect_reports:
        from validate_full_layered import compare_observations as compare_full_observations
        for key,path in(('effectWholeComparator','scripts/validate_full_layered.py'),('effectHashProjection','scripts/iteration/check_layered_saved.py')):
            evidence[key]={'path':path,'sha256':sha(ROOT/path)}
        if any(str(path).replace('\\','/').endswith('nonlayered-effects-wrapper-corrected-01.json')for path in effect_reports):
            audit=bind('effectComparatorWrapperAudit','test-runs/full-native-closure/A/nonlayered-wrapper-audit.json')
            assert audit['productExecutions']==audit['referenceExecutions']==0
            assert audit['comparedSavedNormalCases']==audit['wholeCoordinateComparisonsPassed']==52
            assert audit['comparisonToolSha256']==evidence['effectWholeComparator']['sha256']
            excluded=bind('effectExcludedMrtreeCapture','test-runs/full-native-closure/A/nonlayered-effects-wrapper-corrected-01-excluded-captures.json')
            assert excluded['allCasesCompared']is False and excluded['caseIds']==['mrtree-cycle-bfs']
            timeout=bind('effectMrtreeOriginalTimeout','test-runs/full-native-closure/B/nonlayered-effects-native-01/mrtree-cycle-bfs-command/command.json')
            assert timeout['timedOut']is True and timeout['exitCode']is None
    for index,path in enumerate(effect_reports):
        report=bind('newEffectReport'+str(index),path)
        if str(path).replace('\\','/').endswith('nonlayered-effects-wrapper-corrected-01.json'):
            assert evidence['newEffectReport'+str(index)]['sha256']==audit['newReportSha256']
        assert report['schema']=='pyelk-option-effect-results/v1'
        report_rows={row['id']:row for row in report['rows']}
        assert len(report_rows)==len(report['rows'])
        observed={}
        for row in report['rows']:
            snapshots={}
            for key in('request','reference','native'):
                item=row[key];p=resolve_path(item['path']);assert sha(p)==item['sha256']
                snapshots[key]=read(p)
            assert snapshots['reference']['requestSha256']==snapshots['native']['requestSha256']==row['request']['sha256']
            assert snapshots['reference']['engine']['version']=='0.12.1'
            assert snapshots['reference']['engine']['entrypointSha256']=='b1032b7cfd2a57c54c6f0e8369d7665e19a579954f7cd20a6dae28f1912ea0d7'
            assert snapshots['native']['engine']['version']=='0.1.0'
            assert type(row['comparison']['passed'])is bool
            checked=compare_full_observations(resolve_path(row['request']['path']),snapshots['reference'],snapshots['native'])
            assert checked['passed']is row['comparison']['passed'],'Whole-output comparison flag differs from actual observations'
            observed[row['id']]=snapshots
        for row in report['rows']:
            optionids=set(row['optionIds']);assert optionids<=ids
            if not optionids:
                assert not row['assertions']and row.get('baseline')is None
                continue
            raw_observations=observed[row['id']]
            baseline=row.get('baseline')
            if baseline is not None:
                assert baseline in observed and report_rows[baseline]['comparison']['passed']is True
                paired_delta=diff(observed[baseline]['request'],raw_observations['request'],tolerant=False)['differences']
                assert paired_delta
                check_option_changes(paired_delta,canonical,optionids)
            else:paired_delta=[]
            for assertion in row['assertions']:
                name=assertion['option'];assert name in optionids
                assert assertion['kind']in('layout_geometry','runtime_state','source_selection')
                assert type(assertion['passed'])is bool
                attempt={'id':row['id'],'kind':assertion['kind'],'passed':assertion['passed'],
                         'reportEvidence':'newEffectReport'+str(index),'baseline':baseline,
                         'description':assertion['description']}
                effect_attempts[name].append(attempt)
                if not row['comparison']['passed']or not assertion['passed']:continue
                assert assertion['sourceDerived']is True and assertion['description']
                ordered='pointers'in assertion.get('effectTest',{})
                if ordered:assert assertion['effectTest']['pointers']==assertion['referencePointers']==assertion['nativePointers']
                assert diff(selected_values(raw_observations['reference'],assertion['referencePointers'],ordered=ordered),assertion['expected'],tolerant=False)['passed']
                assert diff(selected_values(raw_observations['native'],assertion['nativePointers'],ordered=ordered),assertion['actual'],tolerant=False)['passed']
                assert diff(assertion['expected'],assertion['actual'],tolerant=False)['passed']
                if baseline is not None:
                    source_before=selected_values(observed[baseline]['reference'],assertion['referencePointers'],ordered=ordered)
                    native_before=selected_values(observed[baseline]['native'],assertion['nativePointers'],ordered=ordered)
                    assert not diff(source_before,assertion['expected'],tolerant=False)['passed'],'Source option produced no selected observable change'
                    assert not diff(native_before,assertion['actual'],tolerant=False)['passed'],'Native option produced no selected observable change'
                    assert diff(source_before,native_before,tolerant=False)['passed']
                else:source_before=native_before=None
                effects[name].append({'id':row['id'],'kind':assertion['kind'],'status':'scoped_verified',
                    'description':assertion['description'],'expected':assertion['expected'],'actual':assertion['actual'],
                    'referencePointers':assertion['referencePointers'],'nativePointers':assertion['nativePointers'],
                    'pointerProjection':'ordered-list'if ordered else'single-or-ordered-list',
                    'baseline':baseline,'sourceBefore':source_before,'nativeBefore':native_before,'pairedInputChanges':paired_delta,
                    'reportEvidence':'newEffectReport'+str(index),'scope':row.get('scope','Only actual input and asserted numeric/state branch; no cross-product inference')})
    rows=[]
    for item in metadata:
        name=item['id'];decl=scalars.get(name,objects.get(name));kind=decl[1]
        valid=next(case for case in parser_by_option[name]if case['id'].endswith(':valid'))
        expected=sources[valid['id']];actual=natives[valid['id']]
        if expected['outcome']=='returned':
            assert diff(expected,actual,tolerant=False)['passed'];parserstatus='value_verified';error=None
        else:
            assert actual['outcome']=='threw'and actual['error']['message']==expected['error']['message']
            parserstatus='source_factory_unavailable';error={'reference':expected['error'],'native':actual['error'],'rawClassParity':False}
        matched=[entry for entry in occurrences[name]if entry['wholeOutputMatched']]
        selected_effects=[entry for entry in effects[name]if entry['kind']=='source_selection']
        rows.append({'id':name,'family':family(name),'metadata':{'status':'registered_fields_verified','type':item['type'],
            'targets':item.get('targets',[]),'evidence':['officialMetadata','metadataRegistration']},
          'parser':{'status':parserstatus,'kind':kind,'caseIds':[case['id']for case in parser_by_option[name]],
            'validInput':valid['text'],'sourceObserverCorrected':valid['id']in corrected,'errors':error,
            'evidence':['parserRequest','parserFirstSource','parserFirstNative','parserSavedRecheck']},
          'publicInputOccurrences':occurrences[name],'sourceMatchedInputOccurrences':len(matched),
          'actuallySelectedBranchEvidence':selected_effects,
          'effects':{'layoutGeometry':'scoped_verified'if any(e['kind']=='layout_geometry'for e in effects[name])else'unverified',
                     'runtimeState':'scoped_verified'if any(e['kind']=='runtime_state'for e in effects[name])else'unverified',
                     'assertions':effects[name],'attempts':effect_attempts[name],'completeOptionSemanticsVerified':False},
          'gap':{'status':'remaining_scope_unverified','nextAction':'Map an existing exact effect/state assertion first; if absent add a minimal applicable paired Source/native assertion. Do not rerun passed matrices or infer an effect from input/parser/whole-result presence.',
                 'upstreamRawFactoryUnavailable':name in objects and not objects[name][4]}})
    assert len(rows)==243 and {row['id']for row in rows}==ids
    counts={'metadataVerified':243,'parserValueVerified':sum(row['parser']['status']=='value_verified'for row in rows),
            'sourceUnavailableRawFactories':sum(row['parser']['status']=='source_factory_unavailable'for row in rows),
            'optionsExplicitlyPresentInPublicSuites':sum(bool(row['publicInputOccurrences'])for row in rows),
            'layoutGeometryScoped':sum(row['effects']['layoutGeometry']=='scoped_verified'for row in rows),
            'runtimeStateScoped':sum(row['effects']['runtimeState']=='scoped_verified'for row in rows),
            'completeOptionSemantics':0}
    return {'schema':'pyelk-option-coverage/v1','upstreamVersion':'0.12.1','denominator':243,
            'evidenceExecutionBaselineVersion':'0.0.1a0','currentVersion':'0.1.0','versionDeltaEvidence':'versionOnlyDelta',
            'rules':['metadata != parser != input occurrence != selected branch != runtime state != layout effect',
                     'Whole-output parity is strong scenario evidence but never automatically promotes a per-option effect.',
                     'Effect whole-output comparisons are offline recomputations under the bound checker; original execution receipts and exact raw differences remain unchanged.',
                     'Scoped assertion status does not certify all enum values, defaults, targets or combinations.',
                     'Source unavailable factories and raw exception-class differences remain explicit.'],
            'summary':counts,'publicCaseCount':len(case_index),'caseIndex':case_index,'evidence':evidence,
            'effectReports':[relative(ROOT/p if not Path(p).is_absolute()else Path(p))for p in effect_reports],
            'unresolvedInputSpellings':unresolved,'families':dict(sorted(Counter(row['family']for row in rows).items())),
            'options':rows,'runtimeExecutedByThisTool':False,'oldCompatibilityLedgerModified':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--build',action='store_true');mode.add_argument('--check',action='store_true');mode.add_argument('--check-structure',action='store_true')
    parser.add_argument('--effect-report',type=Path,action='append',default=[]);parser.add_argument('--out',type=Path)
    parser.add_argument('--root-map',action='append',default=[],metavar='ORIGINAL=CURRENT',help='Explicit original Windows execution-root mapping; raw evidence bytes remain unchanged')
    parser.add_argument('--evidence-manifest',type=Path,help='Verify every archived input and checker dependency before the strict check')
    args=parser.parse_args();reports=args.effect_report;archive_verification=None
    for item in args.root_map:
        before,separator,after=item.partition('=')
        if not separator or not PureWindowsPath(before).is_absolute():parser.error('Expected ORIGINAL_WINDOWS_ROOT=CURRENT_ROOT')
        target=resolve_path(after)
        ROOT_MAPS.append((before,target))
    if args.evidence_manifest:
        if not args.check:parser.error('--evidence-manifest requires --check')
        from iteration.option_evidence import verify_restored
        archive_verification=verify_restored(resolve_path(args.evidence_manifest),ROOT)
    if args.check_structure:
        report=check_structure()
        if args.out:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x',encoding='utf-8')as stream:json.dump(report,stream,indent=2)
        print(json.dumps(report,ensure_ascii=False));return
    if not reports and LEDGER.is_file():reports=[Path(p)for p in read(LEDGER).get('effectReports',[])]
    data=build(reports)
    if args.build:
        LEDGER.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    else:
        comparison=diff(read(LEDGER),data,tolerant=False)
        if not comparison['passed']:raise ValueError('Option coverage ledger differs from actual inputs/evidence: '+str(comparison['differences'][:3]))
    report={'passed':True,'action':'build'if args.build else'check','summary':data['summary'],
            'ledgerSha256':sha(LEDGER),'checkerSha256':sha(Path(__file__)),'productsExecuted':0,'referenceProcessesExecuted':0,
            'archiveVerification':archive_verification,
            'explicitRootMappings':[{'original':before,'current':str(after)}for before,after in ROOT_MAPS]}
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('x',encoding='utf-8')as stream:json.dump(report,stream,indent=2)
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
