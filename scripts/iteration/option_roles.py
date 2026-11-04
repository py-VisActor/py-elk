"""Offline 243-option role/consumer/witness inventory, never product execution.

--build writes the independent role table and Markdown. --check recomputes them
from tracked ledger, metadata, Python AST and existing byte-bound source spans.
Static references/defaults/input occurrences never create runtime witnesses.
An optional --branch-matrix imports A's separately scoped declared branches.
"""
from __future__ import annotations
import argparse
import ast
import base64
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import io
import math
import zipfile

ROOT=Path(__file__).resolve().parents[2]
JSON_PATH=Path('docs/iterations/FULL_OPTION_ROLES.json')
MD_PATH=Path('docs/iterations/FULL_OPTION_ROLES.md')
GETTERS={'option','_option','get_property','get_native_property','read_native_property',
         'get_native','read_native','read_layered_scalar','_read_property',
         'read_core_property','get_individual_or_default','has_option','has_property'}
SETTERS={'set_option','set_property','set_stored_property','set_native_property','set_native','remove_option','remove_property'}
SPECIAL_ROLES={
 'org.eclipse.elk.algorithm':'layout_strategy',
 'org.eclipse.elk.resolvedAlgorithm':'api_metadata',
 'org.eclipse.elk.randomSeed':'runtime_state',
 'org.eclipse.elk.debugMode':'diagnostic',
 'org.eclipse.elk.disco.debug.discoGraph':'diagnostic',
 'org.eclipse.elk.disco.debug.discoPolys':'diagnostic',
 'org.eclipse.elk.labelManager':'callback',
 'org.eclipse.elk.topdown.sizeApproximator':'callback',
 'org.eclipse.elk.font.name':'api_metadata',
 'org.eclipse.elk.font.size':'api_metadata',
 'org.eclipse.elk.json.edgeCoords':'runtime_state',
 'org.eclipse.elk.json.shapeCoords':'runtime_state',
}


def digest(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def rendered(value):return json.dumps(value,ensure_ascii=False,indent=2)+'\n'


def literal_assignment(tree,name):
    for node in tree.body:
        if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('Missing literal declaration '+name)


def walk_dicts(value,pointer=''):
    pending=[(value,pointer)]
    while pending:
        value,pointer=pending.pop()
        if isinstance(value,dict):
            yield value,pointer
            pending.extend((v,pointer+'/'+str(k).replace('~','~0').replace('/','~1'))for k,v in reversed(list(value.items())))
        elif isinstance(value,list):pending.extend((v,pointer+'/'+str(i))for i,v in reversed(list(enumerate(value))))


def native_consumers(root,ids,aliases,bind):
    reads=defaultdict(list);references=defaultdict(list)
    shorts=defaultdict(set)
    for name in ids:
        shorts[name.removeprefix('org.eclipse.elk.')].add(name)
    def canonical(value):
        if value in ids:return value
        if value in aliases and aliases[value]in ids:return aliases[value]
        if value=='org.eclipse.elk.labels.labelManager':return 'org.eclipse.elk.labelManager'
        values=shorts.get(value,())
        return next(iter(values))if len(values)==1 else None
    for path in sorted((root/'src/pyelk').rglob('*.py')):
        name=path.relative_to(root).as_posix();raw=path.read_bytes();tree=ast.parse(raw);lines=raw.decode('utf8').splitlines()
        bind(name)
        class Visitor(ast.NodeVisitor):
            def __init__(self):self.context=[]
            def visit_FunctionDef(self,node):
                self.context.append(node.name);self.generic_visit(node);self.context.pop()
            visit_AsyncFunctionDef=visit_FunctionDef
            def visit_ClassDef(self,node):
                self.context.append(node.name);self.generic_visit(node);self.context.pop()
            def anchor(self,node,operation):
                return {'path':name,'symbol':'.'.join(self.context)or'<module>',
                        'line':node.lineno,'operation':operation,'snippet':lines[node.lineno-1].strip()[:220],
                        'runtimeProof':False}
            def visit_Constant(self,node):
                if isinstance(node.value,str):
                    identifier=canonical(node.value)
                    if identifier:references[identifier].append(self.anchor(node,'literal_or_binding_reference'))
            def visit_Call(self,node):
                function=node.func;method=function.attr if isinstance(function,ast.Attribute)else function.id if isinstance(function,ast.Name)else''
                operation=None;key=None
                if method in GETTERS|SETTERS:
                    for arg in node.args[:2]:
                        if isinstance(arg,ast.Constant)and isinstance(arg.value,str)and canonical(arg.value):
                            key=canonical(arg.value);break
                    operation='property_value_read'if method in GETTERS else'property_write_or_remove'
                elif method in ('get','pop','setdefault')and isinstance(function,ast.Attribute):
                    receiver=function.value
                    if isinstance(receiver,ast.Attribute)and receiver.attr=='properties'and node.args:
                        arg=node.args[0]
                        if isinstance(arg,ast.Constant)and isinstance(arg.value,str):key=canonical(arg.value)
                        operation='property_map_read'if method=='get'else'property_map_mutation'
                if key and operation:reads[key].append(self.anchor(node,operation))
                self.generic_visit(node)
            def visit_Subscript(self,node):
                if isinstance(node.value,ast.Attribute)and node.value.attr=='properties'and isinstance(node.slice,ast.Constant)and isinstance(node.slice.value,str):
                    key=canonical(node.slice.value)
                    if key:reads[key].append(self.anchor(node,'property_map_write'if isinstance(node.ctx,ast.Store)else'property_map_read'))
                self.generic_visit(node)
        Visitor().visit(tree)
    # Catalogues/declaration/default tables are references, never consumers.
    for name in reads:
        reads[name]=[a for a in reads[name]if not a['path'].startswith(('src/pyelk/options/','src/pyelk/metadata/'))]
    return reads,references


def source_consumers(root,ids,bind):
    spans=[];seen=set();symbols=defaultdict(set);declarations=defaultdict(list)
    constructor=re.compile(r"\b([A-Z][A-Z0-9_]+)\s*=\s*new Property(?:_\d+)?\(['\"]([^'\"]+)['\"]")
    for path in sorted((root/'references').glob('*sources.json')):
        name=path.relative_to(root).as_posix();document=load(path);used=False
        for row,pointer in walk_dicts(document):
            encoded=row.get('sourceBytesBase64',row.get('bytesBase64'))
            start=row.get('startLine',row.get('lineStart'));end=row.get('endLine',row.get('lineEnd'))
            expected=row.get('spanSha256',row.get('sha256'))
            if not(encoded and type(start)is int and type(end)is int and type(expected)is str):continue
            raw=base64.b64decode(encoded,validate=True)
            if digest(raw)!=expected:raise ValueError('Source span bytes differ: '+name+pointer)
            used=True
            if (expected,start,end)in seen:continue
            seen.add((expected,start,end));text=raw.decode('utf8')
            span={'path':name,'pointer':pointer,'symbol':row.get('symbol',row.get('id','<span>')),
                  'workerLineStart':start,'workerLineEnd':end,'spanSha256':expected,'text':text}
            spans.append(span)
            for offset,line in enumerate(text.splitlines()):
                for match in constructor.finditer(line):
                    symbol,identifier=match.groups()
                    if identifier=='org.eclipse.elk.labels.labelManager':identifier='org.eclipse.elk.labelManager'
                    if identifier not in ids:continue
                    symbols[symbol].add(identifier)
                    declarations[identifier].append({k:v for k,v in span.items()if k!='text'}|{
                        'workerLine':start+offset,'propertySymbol':symbol,'kind':'source_property_declaration','runtimeProof':False})
        if used:bind(name)
    result=defaultdict(list)
    tokens=re.compile(r'\b[A-Z][A-Z0-9_]+\b')
    for span in spans:
        for offset,line in enumerate(span['text'].splitlines()):
            if not re.search(r'\$(?:getProperty|hasProperty)\s*\(',line):continue
            for symbol in sorted(set(tokens.findall(line))&symbols.keys()):
                # Ambiguous symbols stay declaration references, not bindings.
                if len(symbols[symbol])!=1:continue
                identifier=next(iter(symbols[symbol]))
                result[identifier].append({k:v for k,v in span.items()if k!='text'}|{
                    'workerLine':span['workerLineStart']+offset,'propertySymbol':symbol,
                    'kind':'source_accessor_static_anchor','runtimeProof':False,'snippet':line.strip()[:220]})
    return result,declarations,{'packets':len({v['path']for v in spans}),'uniqueByteVerifiedSpans':len(spans),
                                'scope':'Existing archived spans only; absence is not proof of no compiled consumer.'}


def candidate_role(meta,consumers):
    identifier=meta['id']
    if identifier in SPECIAL_ROLES:return SPECIAL_ROLES[identifier]
    if not consumers:return'unclassified_no_static_consumer_anchor'
    if any(a['path'].startswith('src/pyelk/algorithms/')for a in consumers):
        return'layout_strategy'if meta['type']in('ENUM','ENUMSET','BOOLEAN')else'geometry'
    return'runtime_state'


def json_pointer(value,pointer):
    for part in pointer.split('/')[1:]:
        part=part.replace('~1','/').replace('~0','~')
        value=value[int(part)]if isinstance(value,list)else value[part]
    return value


def same_value(first,second):
    if type(first)is bool or type(second)is bool:return type(first)is type(second)and first==second
    if isinstance(first,(int,float))and isinstance(second,(int,float)):
        return first==second and(first!=0 or math.copysign(1,first)==math.copysign(1,second))
    if type(first)is not type(second):return False
    if isinstance(first,dict):return first.keys()==second.keys()and all(same_value(first[k],second[k])for k in first)
    if isinstance(first,list):return len(first)==len(second)and all(same_value(a,b)for a,b in zip(first,second))
    return first==second


_EXISTING_ROLE_FINDINGS = {'core': [{'option': 'org.eclipse.elk.scaleFactor', 'kind': 'actual_pre_post_scaling_state', 'requestPointer': '/graph/children/0/layoutOptions/elk.scaleFactor', 'inputValue': 1.5, 'referencePointers': ['/observation/events/9/geometry/width', '/observation/events/9/geometry/height', '/observation/geometry/1/width', '/observation/geometry/1/height'], 'nativePointers': ['/actual/events/9/geometry/width', '/actual/events/9/geometry/height', '/actual/geometry/1/width', '/actual/geometry/1/height'], 'values': [28, 53, 42, 79.5], 'scope': 'Actual coordinator child dimensions multiplied by1.5 between child leave and final parent result; not a merely configured scale.', 'bindings': [{'path': 'tests/fixtures/suites/next-native/recursive-ordinary-nested-request.json', 'sha256': '04b033d6537292b51bf1f7d6236ffe6c8f1f3026e543fe68df68b6cb39ca61b4'}, {'path': 'tests/fixtures/suites/next-native/recursive-ordinary-probe.cjs', 'sha256': '3af2252d0724e928983140d2417514ffd91f0b46b5c12b5e8d1362a4b4b5ea84'}, {'path': 'test-runs/20261104-HOST-11/V/recursive-ordinary-nested-oracle-01/observation.json', 'sha256': '1016b8393a086dd93dd56b524e50bc340b77d498aac26983a927d516923653c3'}, {'path': 'test-runs/20261104-HOST-11/root/recursive-ordinary-nested-native-01/comparison.json', 'sha256': '8078618fa63aab2c8e6b0c8f6ebc2cd5dea5993d7f2a7c8aab95b6c644a47627'}]}, {'option': 'org.eclipse.elk.noLayout', 'kind': 'actual_coordinator_exclusion_state', 'requestPointer': '/graph/children/1/layoutOptions/elk.noLayout', 'inputValue': True, 'referencePointers': ['/observation/events', '/observation/geometry/5'], 'nativePointers': ['/actual/events', '/actual/geometry/5'], 'assertion': 'Actual enter/leave skip, no execute for skip, no enter for untouched; real c/r execute. Untouched child geometry remains3,4,6,8.', 'scope': 'One nested noLayout guard after genuine recursive traversal; no all-graph geometry claim.', 'bindings': [{'path': 'tests/fixtures/suites/next-native/recursive-ordinary-nested-request.json', 'sha256': '04b033d6537292b51bf1f7d6236ffe6c8f1f3026e543fe68df68b6cb39ca61b4'}, {'path': 'tests/fixtures/suites/next-native/recursive-ordinary-probe.cjs', 'sha256': '3af2252d0724e928983140d2417514ffd91f0b46b5c12b5e8d1362a4b4b5ea84'}, {'path': 'test-runs/20261104-HOST-11/V/recursive-ordinary-nested-oracle-01/observation.json', 'sha256': '1016b8393a086dd93dd56b524e50bc340b77d498aac26983a927d516923653c3'}, {'path': 'test-runs/20261104-HOST-11/root/recursive-ordinary-nested-native-01/comparison.json', 'sha256': '8078618fa63aab2c8e6b0c8f6ebc2cd5dea5993d7f2a7c8aab95b6c644a47627'}]}, {'option': 'org.eclipse.elk.layered.considerModelOrder.crossingCounterNodeInfluence', 'kind': 'actual_model_order_activation_predicate', 'referencePointers': ['/observation/predicates/0/needed', '/observation/predicates/14/options', '/observation/predicates/14/needed'], 'nativePointers': ['/actual/predicates/0/needed', '/actual/predicates/14/options', '/actual/predicates/14/needed'], 'values': [False, {'elk.layered.considerModelOrder.crossingCounterNodeInfluence': 1}, True], 'scope': 'Original needsModelOrderBasedOnParent actually called on imported parent; numeric weight1 activates model-order production vs absent/default0. Not weighted cost/geometry proof.', 'bindings': [{'path': 'tests/fixtures/suites/next-native/model-order-producer-probe.cjs', 'sha256': '4f3efe0ca67f4165b49ff3d44630df9c0d849d1bfd7389d3d23fdd05fe3cdde7'}, {'path': 'test-runs/20261104-HOST-10/root/model-order-original-01/observation.json', 'sha256': '4a59417c1e46673a73a03e7c8286a2937bd3d304a18083ca63ed6757e5ac877e'}, {'path': 'test-runs/20261104-HOST-10/root/model-order-native-01/comparison.json', 'sha256': '15c398ff066029e155067a5b6754a3943ce0dafa534cdebd7c175596cdcd9289'}]}, {'option': 'org.eclipse.elk.layered.considerModelOrder.noModelOrder', 'kind': 'actual_import_model_order_exclusion', 'inlineInputAnchor': 'Source probe lines17-23 excluded node noModelOrder=true; full Source importFlatGraph called line23', 'referencePointers': ['/observation/nodes/1', '/observation/nodes/2', '/observation/nodes/3', '/observation/ports/0', '/observation/importedNodeCount'], 'nativePointers': ['/actual/nodes/1', '/actual/nodes/2', '/actual/nodes/3', '/actual/ports/0', '/actual/importedNodeCount'], 'values': [['excluded', None], ['c', 0], ['d', 1], ['xp', None], 3], 'scope': 'Node remains imported but model-order assignment and its port traversal are excluded; native comparator exercises real producer with explicit geometry callbacks, not full layout.', 'bindings': [{'path': 'tests/fixtures/suites/next-native/model-order-producer-probe.cjs', 'sha256': '4f3efe0ca67f4165b49ff3d44630df9c0d849d1bfd7389d3d23fdd05fe3cdde7'}, {'path': 'test-runs/20261104-HOST-10/root/model-order-original-01/observation.json', 'sha256': '4a59417c1e46673a73a03e7c8286a2937bd3d304a18083ca63ed6757e5ac877e'}, {'path': 'test-runs/20261104-HOST-10/root/model-order-native-01/comparison.json', 'sha256': '15c398ff066029e155067a5b6754a3943ce0dafa534cdebd7c175596cdcd9289'}]}], 'algorithm': {'cases': ['basic-layered', 'basic-box'], 'requestChanges': [{'path': '/graph/layoutOptions/elk.algorithm', 'kind': 'value', 'expected': 'layered', 'actual': 'box'}], 'geometry': [{'pointer': '/result/children/0/x', 'sourceBefore': 12, 'nativeBefore': 12.0, 'sourceAfter': 15, 'nativeAfter': 15.0}, {'pointer': '/result/children/0/y', 'sourceBefore': 16, 'nativeBefore': 16.0, 'sourceAfter': 15, 'nativeAfter': 15.0}, {'pointer': '/result/children/1/x', 'sourceBefore': 53.5, 'nativeBefore': 53.5, 'sourceAfter': 50, 'nativeAfter': 50.0}], 'option': 'org.eclipse.elk.algorithm', 'wholeOutputStatuses': ['PASS', 'PASS'], 'bindings': [{'path': 'tests/fixtures/suites/full-native-algorithms/requests/basic-layered.json', 'sha256': '96189d3d61d0f1391d0ebe767bfefe04df8bb51d0a89d1fd27aa53dd4e9f82dd'}, {'path': 'tests/fixtures/suites/full-native-algorithms/requests/basic-box.json', 'sha256': '45394f188b31e8d6b40446cfb3877173259431ccfac26cffb26c4624de75d225'}, {'path': 'test-runs/full-native-01/B/reference-01/observations/basic-layered.json', 'sha256': '954caac5e8d0745ed184ad7f6c095de9b4888c90cd87a764f6d34c70f063bf4e'}, {'path': 'test-runs/full-native-01/B/reference-01/observations/basic-box.json', 'sha256': 'f90d92ebde27fd81e828ded5eb5458308c7c137fc26109eff6b6ee7d84a5f39c'}, {'path': 'test-runs/full-native-01/B/native-01/observations/basic-layered.json', 'sha256': '1b58cf83f0d31243048f961bfdbc78a9fc9b34c4a3340d97c4205ec181563068'}, {'path': 'test-runs/full-native-01/B/native-01/observations/basic-box.json', 'sha256': 'b1f26f2bc6ac8d5cf826176ac1714136d4a1e2eb06833d5c9ec9a390459df32c'}], 'strength': 'strict existing paired public requests; only algorithm selector differs; actual Source/native numeric geometry changes match'}}

def additional_role_witnesses(root,bind,*,import_existing=False):
    """Five previously captured facts, strictly replayed from explicit raw bytes.

    The extra bytes live in M6's advanced archive. We bind member bytes rather
    than its whole-archive digest in the generated role JSON to avoid a
    roles->advanced manifest->roles SHA cycle. Every read still verifies the
    archive against its manifest and the exact member against the fixed SHA.
    --check never imports the old execution tree.
    """
    aliases={
        'test-runs/20261104-HOST-11/V/recursive-ordinary-nested-oracle-01/observation.json':'tests/fixtures/suites/next-native/recursive-ordinary-nested-oracle.json',
        'test-runs/20261104-HOST-10/root/model-order-original-01/observation.json':'tests/fixtures/suites/next-native/model-order-producer-oracle.json',
    }
    caches={}
    def read(binding):
        original=binding['path'];expected=binding['sha256'];path=aliases.get(original,original)
        if Path(path).is_absolute()or':'in path or'..'in Path(path).parts:raise ValueError('Escaping role evidence path')
        storage='repository'
        if not path.startswith(('test-runs/','.local/')):
            raw=(root/path).read_bytes();bind(path)
        else:
            raw=None
            for kind in('algorithms','branches','options','advanced'):
                if kind not in caches:
                    manifest=load(root/f'references/full-native-closure/{kind}.manifest.json')
                    entries=manifest.get('members',manifest.get('files',[]))
                    members=entries if isinstance(entries,dict)else{x['path']:x['sha256']for x in entries}
                    archive=manifest['archive'];archive_path=archive['path']if isinstance(archive,dict)else archive
                    archive_sha=archive['sha256']if isinstance(archive,dict)else manifest['archiveSha256']
                    if archive_path!=f'references/full-native-closure/{kind}.zip':raise ValueError('Escaping role evidence archive path')
                    packed=(root/archive_path).read_bytes()
                    if digest(packed)!=archive_sha:raise ValueError('Role evidence archive SHA differs: '+archive_path)
                    caches[kind]=(archive_path,zipfile.ZipFile(io.BytesIO(packed)),members)
                archive_path,z,members=caches[kind]
                if members.get(path)==expected:
                    raw=z.read(path);storage=archive_path;break
            if raw is None:
                if not import_existing:raise ValueError('Role evidence has no explicit archive member: '+path)
                raw=(root/path).read_bytes();storage='references/full-native-closure/advanced.zip'
        if digest(raw)!=expected:raise ValueError('Role evidence SHA differs: '+path)
        return json.loads(raw)if path.endswith('.json')else raw,dict(path=path,sha256=expected,storage=storage,originalExecutionPath=original)
    result=[]
    for finding in _EXISTING_ROLE_FINDINGS['core']:
        values=[];bindings=[]
        for item in finding['bindings']:
            value,binding=read(item);values.append(value);bindings.append(binding)
        source,native=values[-2:]
        if native.get('passed')is not True or native.get('oracleSha256')!=finding['bindings'][-2]['sha256']:raise ValueError('Core role execution binding differs')
        observations=[json_pointer(source,p)for p in finding['referencePointers']]
        actual=[json_pointer(native,p)for p in finding['nativePointers']]
        if not same_value(observations,actual):raise ValueError('Core role state differs: '+finding['option'])
        if 'values'in finding and not same_value(observations,finding['values']):raise ValueError('Core role expected state differs')
        if 'requestPointer'in finding:
            if not same_value(json_pointer(values[0],finding['requestPointer']),finding['inputValue']):raise ValueError('Role request value differs')
            if source['requestSha256']!=finding['bindings'][0]['sha256']or source['probeSha256']!=finding['bindings'][1]['sha256']:raise ValueError('Role request/probe binding differs')
        else:
            if source['probeSha256']!=finding['bindings'][0]['sha256']:raise ValueError('Role inline probe binding differs')
        if finding['option']=='org.eclipse.elk.scaleFactor':
            if observations[2]!=observations[0]*1.5 or observations[3]!=observations[1]*1.5:raise ValueError('Actual scaling effect missing')
        if finding['option']=='org.eclipse.elk.noLayout':
            events=observations[0]
            if [e['node']for e in events if e['kind']=='execute']!=['c','r']or any(e.get('node')=='untouched'for e in events):raise ValueError('Actual noLayout exclusion missing')
            untouched=observations[1]
            if [untouched[k]for k in('x','y','width','height')]!=[3,4,6,8]:raise ValueError('Excluded geometry mutated')
        result.append({'optionId':finding['option'],'kind':'runtime_state','role':'runtime_state','status':'scoped_saved_state_verified',
                       'description':finding['kind'],'scope':finding['scope'],'bindings':bindings,
                       'referencePointers':finding['referencePointers'],'nativePointers':finding['nativePointers'],
                       'referenceValues':observations,'actualValues':actual,'passed':True,'fullOptionSemanticsProven':False})
    pair=_EXISTING_ROLE_FINDINGS['algorithm'];values=[];bindings=[]
    for item in pair['bindings']:
        value,binding=read(item);values.append(value);bindings.append(binding)
    before,after,ref_before,ref_after,native_before,native_after=values
    first=json.loads(json.dumps(before));second=json.loads(json.dumps(after))
    first['graph']['layoutOptions'].pop('elk.algorithm');second['graph']['layoutOptions'].pop('elk.algorithm')
    if not same_value(first,second):raise ValueError('Algorithm causal pair changes another input')
    for request,reference,native,binding in((before,ref_before,native_before,pair['bindings'][0]),(after,ref_after,native_after,pair['bindings'][1])):
        if reference['requestSha256']!=binding['sha256']or native['requestSha256']!=binding['sha256']:raise ValueError('Algorithm causal request binding differs')
        if reference['outcome']!='returned'or native['outcome']!='returned':raise ValueError('Algorithm causal outcome differs')
    checks=[]
    for geometry in pair['geometry']:
        pointer=geometry['pointer'];observed=[json_pointer(v,pointer)for v in(ref_before,native_before,ref_after,native_after)]
        expected=[geometry[k]for k in('sourceBefore','nativeBefore','sourceAfter','nativeAfter')]
        if not same_value(observed,expected)or same_value(observed[0],observed[2])or not same_value(observed[0],observed[1])or not same_value(observed[2],observed[3]):raise ValueError('Algorithm causal geometry differs')
        checks.append(dict(pointer=pointer,referenceBefore=observed[0],actualBefore=observed[1],referenceAfter=observed[2],actualAfter=observed[3],passed=True))
    result.append({'optionId':'org.eclipse.elk.algorithm','kind':'layout_geometry','role':'layout_strategy','status':'scoped_saved_causal_geometry_verified',
                   'description':'algorithm-only public paired input, layered versus box','scope':pair['strength'],
                   'bindings':bindings,'checks':checks,'passed':True,'fullOptionSemanticsProven':False})
    if len(result)!=5 or len({v['optionId']for v in result})!=5:raise ValueError('Existing role increment denominator differs')
    return result


def build(root=ROOT,branch_matrix=None,*,import_existing=False):
    root=Path(root);inputs={}
    def bind(name):
        raw=(root/name).read_bytes();inputs[name]=digest(raw);return json.loads(raw)if name.endswith('.json')else raw
    metadata=bind('references/metadata/options.json');ledger=bind('docs/option-coverage.json')
    assert len(metadata)==len(ledger['options'])==243 and [r['id']for r in metadata]==[r['id']for r in ledger['options']]
    ids={r['id']for r in metadata};aliases=literal_assignment(ast.parse(bind('src/pyelk/algorithms/layered/native_properties.py')),'_ALIAS_IDS')
    accessors,refs=native_consumers(root,ids,aliases,bind)
    native={name:[a for a in accessors[name]if a['operation']in('property_value_read','property_map_read')]for name in ids}
    producers={name:[a for a in accessors[name]if a not in native[name]]for name in ids}
    source,declarations,source_scope=source_consumers(root,ids,bind)
    branches=defaultdict(list);matrix_path=None
    if branch_matrix:
        matrix_path=Path(branch_matrix).as_posix();matrix=bind(matrix_path)
        assert matrix['schema']=='pyelk-declared-branch-matrix/v1'
        for row in matrix['rows']+matrix['supplementalRows']:
            if row.get('optionId')in ids:
                group='rows'if row in matrix['rows']else'supplementalRows'
                branches[row['optionId']].append({'rowId':row['id'],'status':row['status'],
                    'pointer':'/'+group+'/'+str(matrix[group].index(row)),'role':'branch selection/strategy scope only',
                    'effectPromotionInferred':False})
    increments=additional_role_witnesses(root,bind,import_existing=import_existing)
    rows=[]
    for index,(meta,old)in enumerate(zip(metadata,ledger['options'],strict=True)):
        name=meta['id'];candidate=candidate_role(meta,native[name]);witnesses=[]
        for n,a in enumerate(old['effects']['assertions']):
            witnesses.append({'id':a['id'],'kind':a['kind'],'ledgerPointer':'/options/'+str(index)+'/effects/assertions/'+str(n),
                              'scope':a['scope'],'description':a['description'],
                              'evidenceKeys':{k:v for k,v in a.items()if k.endswith('Evidence')}})
        added=[w for w in increments if w['optionId']==name]
        has_witness=bool(witnesses or added);actual_roles=sorted({'geometry'if w['kind']=='layout_geometry'else'runtime_state'if w['kind']=='runtime_state'else'layout_strategy'for w in witnesses}|{w['role']for w in added})
        if candidate=='callback':need='Actual applicable typed callback invocation and returned state/size, with Source/native ordering; declaration/parser failure is insufficient.'
        elif candidate=='diagnostic':need='Actual diagnostic/logging/output-state assertion under the applicable caller; no geometry change is required for a diagnostic-only role.'
        elif candidate=='api_metadata':need='Actual target/presence/override/query or descriptor-state consumer assertion; catalogue registration alone does not prove this role is consumed.'
        elif candidate=='layout_strategy':need='Applicable finite strategy branch actually executed plus Source/native state or numeric assertion; a configuration or class name alone is insufficient.'
        elif candidate=='geometry':need='Minimal applicable Source/native size/position/route/constraint assertion, preferably a paired sensitive input; unchanged output is not an effect proof.'
        elif candidate=='runtime_state':need='Applicable Source/native state/presence/identity/serialization assertion beyond parser value and input occurrence.'
        else:need='First identify an applicable real caller or external/API-only contract; scanned literals/defaults do not establish consumption or prove the option unused.'
        rows.append({'id':name,'family':old['family'],'metadataType':meta['type'],'targets':meta.get('targets',[]),
            'staticRoleCandidate':candidate,'classificationBasis':'named role from declared contract; unexecuted consumer anchors only'if name in SPECIAL_ROLES else'actual accessor location and declared value type; a candidate classification only',
            'observedRoles':actual_roles,'nativeConsumers':native[name][:12],'nativeConsumerCount':len(native[name]),
            'nativeProducerAnchors':producers[name][:8],'nativeProducerCount':len(producers[name]),
            'sourceConsumerAnchors':source[name][:8],'sourceConsumerAnchorCount':len(source[name]),
            'declarationReferences':declarations[name][:3],'literalReferenceCount':len(refs[name]),
            'literalReferenceSamples':refs[name][:3],'staticReferencesAreRuntimeProof':False,
            'runtimeWitnesses':witnesses,'additionalRoleWitnesses':added,'branchMatrixReferences':branches[name],
            'existingScopedGeometry':old['effects']['layoutGeometry'],'existingScopedState':old['effects']['runtimeState'],
            'finiteWitnessStatus':'scoped_effect_or_state_witness'if has_witness else'no_runtime_consumption_witness',
            'sourceRawFactoryUnavailable':old['parser']['status']=='source_factory_unavailable',
            'parserValueStatus':old['parser']['status'],'publicInputOccurrenceCount':len(old['publicInputOccurrences']),
            'failedOrUnprovenAttempts':old['effects'].get('attempts',[]),
            'minimalRemainingWitness':{'requiredForUnwitnessedRole':not has_witness,'need':need,
                'channel':'typed/internal or actual callback caller; raw Source factory unavailable'if old['parser']['status']=='source_factory_unavailable'else'applicable public API or typed state consumer',
                'fullOptionSemanticsProven':False},'unusedOptionProven':False})
    union=sum(bool(r['runtimeWitnesses'])for r in rows)
    summary={'declaredIDs':243,'scopedGeometryIDs':sum(r['existingScopedGeometry']=='scoped_verified'for r in rows),
             'scopedStateIDs':sum(r['existingScopedState']=='scoped_verified'for r in rows),'witnessUnionIDs':union,
             'withoutScopedEffectOrStateWitness':243-union,'sourceRawFactoryUnavailable':sum(r['sourceRawFactoryUnavailable']for r in rows),
             'withNativeAccessorAnchors':sum(bool(r['nativeConsumers']or r['nativeProducerAnchors'])for r in rows),
             'withNativeConsumerReadAnchors':sum(bool(r['nativeConsumers'])for r in rows),
             'withArchivedSourceAccessorAnchors':sum(bool(r['sourceConsumerAnchors'])for r in rows),
             'noNativeAccessorAnchorLocated':sum(not(r['nativeConsumers']or r['nativeProducerAnchors'])for r in rows),
             'fullOptionSemanticsProven':0}
    assert summary['scopedGeometryIDs']==73 and summary['scopedStateIDs']==15 and union==82
    summary.update(additionalRoleWitnessIDs=len(increments),additionalCausalGeometryRoleIDs=sum(w['kind']=='layout_geometry'for w in increments),
                   additionalStateRoleIDs=sum(w['kind']=='runtime_state'for w in increments),roleWitnessUnionIDs=sum(bool(r['runtimeWitnesses']or r['additionalRoleWitnesses'])for r in rows),
                   withoutAnyRoleWitness=sum(not(r['runtimeWitnesses']or r['additionalRoleWitnesses'])for r in rows),
                   branchCrossReferences=sum(len(r['branchMatrixReferences'])for r in rows))
    return {'schema':'pyelk-full-option-roles/v1','upstreamVersion':'0.12.1','denominator':243,'inputsSha256':dict(sorted(inputs.items())),
            'frozenOptionLedgerSha256':inputs['docs/option-coverage.json'],'branchMatrixPath':matrix_path,
            'rules':['Static accessors, literals, defaults and public input occurrences are not runtime witnesses.',
                     'Source anchors are existing byte-verified compiled spans, not proof that a branch executed.',
                     'Imported ledger statuses retain their original scope; neither all values nor interactions are inferred.',
                     'No accessor found in the scanned inventory does not prove an option has no consumer.',
                     'A Source raw-factory failure does not prove the typed callback/internal contract unavailable.'],
            'summary':summary,'sourceInventory':source_scope,
            'unwitnessedByFamily':{family:[r['id']for r in rows if r['family']==family and not(r['runtimeWitnesses']or r['additionalRoleWitnesses'])]
                                   for family in sorted({r['family']for r in rows})if any(r['family']==family and not(r['runtimeWitnesses']or r['additionalRoleWitnesses'])for r in rows)},
            'rows':rows,'productsExecuted':0,'referenceProcessesExecuted':0,'frozenLedgerModified':False}


def markdown(data):
    s=data['summary']
    lines=['# Roles and finite witnesses for 243 declared options','',
      'This independent role map preserves the frozen option ledger. Static reads, defaults, literals, input mentions and configured branches never become geometry or runtime proof.','',
      f"Frozen ledger: **{s['scopedGeometryIDs']} geometry IDs, {s['scopedStateIDs']} state IDs, union {s['witnessUnionIDs']}**. These counts and the ledger bytes are unchanged. Full option semantics proven:0.",'',
      f"A separate saved-only increment registers {s['additionalRoleWitnessIDs']} existing role witnesses: {s['additionalCausalGeometryRoleIDs']} algorithm-only causal geometry pair and {s['additionalStateRoleIDs']} actual consumer states. Role-witness union:{s['roleWitnessUnionIDs']}; without any role witness:{s['withoutAnyRoleWitness']}. This does not rewrite the ledger or turn an activation predicate into weighted-cost proof.",'',
      f"Finite branch cross-references:{s['branchCrossReferences']}. Each retains its own helper/body, configuration, route-state, scheduler-exclusion or identity-boundary status. Cross-references do not promote the option's geometry status.",'',
      'The algorithm pair differs only in the selected algorithm; saved public positions change identically. The four state witnesses cover real scaling, noLayout traversal exclusion, model-order activation, and noModelOrder import exclusion. Historical execution versions remain historical; no product/reference is rerun.','',
      'Check: `python scripts/iteration/option_roles.py --check`. Additional raw files must be explicit SHA-verified archive members or named tracked aliases. No ignored-workspace fallback is allowed. `--build --import-existing-evidence` is an explicit import step before sealing advanced.zip and is prohibited with --check.','',
      '| ID | Static role candidate | Observed role | Scoped witness | Branch references |',
      '| --- | --- | --- | --- | --- |']
    for row in data['rows']:
        observed=', '.join(row['observedRoles'])or'none'
        status='ledger scoped witness'if row['runtimeWitnesses']else'additional saved role witness'if row['additionalRoleWitnesses']else'no runtime consumption witness'
        if row['sourceRawFactoryUnavailable']:status+='; raw Source factory unavailable'
        lines.append('| `'+row['id'].removeprefix('org.eclipse.elk.')+'` | '+row['staticRoleCandidate']+' | '+observed+' | '+status+' | '+str(len(row['branchMatrixReferences']))+' |')
    lines+=['','## Remaining finite role witnesses','',
      'Each JSON row retains actual consumer/source anchors, failed attempts, exact raw bindings and minimalRemainingWitness. An API/diagnostic/state/callback contract requires an applicable observation of that role; no geometry change is demanded for a purely diagnostic contract. No located accessor is not proof of an unused option.','']
    for family,names in data['unwitnessedByFamily'].items():
        lines.append('- **'+family+'** ('+str(len(names))+'): '+', '.join('`'+n.removeprefix('org.eclipse.elk.')+'`'for n in names))
    lines+=['','The completed finite branch accounting does not establish every numeric value, graph interaction, option semantic or full raw parity. All retained Source errors, alias scopes and identity-order boundaries remain in the separate matrix.','']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--build',action='store_true');mode.add_argument('--check',action='store_true')
    parser.add_argument('--branch-matrix',type=Path);parser.add_argument('--out',type=Path)
    parser.add_argument('--import-existing-evidence',action='store_true',help='Build only: explicitly import the fixed historical raw files before sealing M6 advanced.zip')
    args=parser.parse_args();branch=args.branch_matrix
    if args.import_existing_evidence and not args.build:parser.error('evidence import is allowed only with --build')
    if branch is None and (ROOT/JSON_PATH).is_file():branch=load(ROOT/JSON_PATH).get('branchMatrixPath')
    before=digest((ROOT/'docs/option-coverage.json').read_bytes());data=build(branch_matrix=branch,import_existing=args.import_existing_evidence)
    raw=rendered(data);md=markdown(data)
    if args.build:
        (ROOT/JSON_PATH).write_text(raw,encoding='utf8',newline='\n');(ROOT/MD_PATH).write_text(md,encoding='utf8',newline='\n')
    else:
        if (ROOT/JSON_PATH).read_text('utf8')!=raw or (ROOT/MD_PATH).read_text('utf8')!=md:raise ValueError('Option roles differ from actual static inputs and scoped ledger')
    assert digest((ROOT/'docs/option-coverage.json').read_bytes())==before
    report={'passed':True,'summary':data['summary'],'rolesSha256':digest((ROOT/JSON_PATH).read_bytes()),
            'checkerSha256':digest(Path(__file__).read_bytes()),'productsExecuted':0,'referenceProcessesExecuted':0,'frozenLedgerModified':False}
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('x',encoding='utf8')as stream:json.dump(report,stream,indent=2)
    print(json.dumps(report))


if __name__=='__main__':main()
