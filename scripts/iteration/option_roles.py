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


def build(root=ROOT,branch_matrix=None):
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
        for row in matrix['rows']:
            if row.get('optionId')in ids:
                branches[row['optionId']].append({'rowId':row['id'],'status':row['status'],
                    'pointer':'/rows/'+str(matrix['rows'].index(row)),'role':'branch selection/strategy scope only',
                    'effectPromotionInferred':False})
    rows=[]
    for index,(meta,old)in enumerate(zip(metadata,ledger['options'],strict=True)):
        name=meta['id'];candidate=candidate_role(meta,native[name]);witnesses=[]
        for n,a in enumerate(old['effects']['assertions']):
            witnesses.append({'id':a['id'],'kind':a['kind'],'ledgerPointer':'/options/'+str(index)+'/effects/assertions/'+str(n),
                              'scope':a['scope'],'description':a['description'],
                              'evidenceKeys':{k:v for k,v in a.items()if k.endswith('Evidence')}})
        has_witness=bool(witnesses);actual_roles=sorted({'geometry'if w['kind']=='layout_geometry'else'runtime_state'if w['kind']=='runtime_state'else'layout_strategy'for w in witnesses})
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
            'runtimeWitnesses':witnesses,'branchMatrixReferences':branches[name],
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
    return {'schema':'pyelk-full-option-roles/v1','upstreamVersion':'0.12.1','denominator':243,'inputsSha256':dict(sorted(inputs.items())),
            'frozenOptionLedgerSha256':inputs['docs/option-coverage.json'],'branchMatrixPath':matrix_path,
            'rules':['Static accessors, literals, defaults and public input occurrences are not runtime witnesses.',
                     'Source anchors are existing byte-verified compiled spans, not proof that a branch executed.',
                     'Imported ledger statuses retain their original scope; neither all values nor interactions are inferred.',
                     'No accessor found in the scanned inventory does not prove an option has no consumer.',
                     'A Source raw-factory failure does not prove the typed callback/internal contract unavailable.'],
            'summary':summary,'sourceInventory':source_scope,
            'unwitnessedByFamily':{family:[r['id']for r in rows if r['family']==family and not r['runtimeWitnesses']]
                                   for family in sorted({r['family']for r in rows})if any(r['family']==family and not r['runtimeWitnesses']for r in rows)},
            'rows':rows,'productsExecuted':0,'referenceProcessesExecuted':0,'frozenLedgerModified':False}


def markdown(data):
    s=data['summary'];lines=['# 243 项选项的角色与有限见证映射','',
      '此表独立于冻结 option-coverage 账本。它映射有限的 243 个声明，不要求无限数值或组合；静态读取、默认值和输入出现不当作运行证明。','',
      f"保留原账本：{s['scopedGeometryIDs']} 项限定几何、{s['scopedStateIDs']} 项限定状态，去重 {s['witnessUnionIDs']} 项；其余 {s['withoutScopedEffectOrStateWitness']} 项没有登记运行消费见证。8 项 raw factory 不可构造与 typed/internal 合同分别列示。完整选项语义通过数仍为 0。",'',
      '角色列是静态候选分类：只给已定位的 accessor 加真实函数/行号，字面量与声明另列 reference。实际已观察角色只来自冻结账本的具体断言。API 元数据注册不自动证明每项的消费或布局效果。','',
      f"本次现仓库定位 {s['withNativeAccessorAnchors']} 个 ID 的显式属性 accessor，其中 {s['withNativeConsumerReadAnchors']} 个有读取消费者；写入/移除生产者另列。既存 Source 包定位 {s['withArchivedSourceAccessorAnchors']} 个 ID 的读取 accessor。未定位是扫描范围内的缺口，不能声称编译后未使用。",'',
      '复核命令：`python scripts/iteration/option_roles.py --check`。工具只读 tracked 账本、元数据、Python AST 与既存 Source 字节；不导入产品、不运行布局、也不重放原版。可在 A 的分支矩阵冻结后用 `--build --branch-matrix docs/iterations/FULL_DECLARED_BRANCH_MATRIX.json` 接入交叉引用；分支配置不会提升几何效果。','',
      '## 逐项映射','', '| ID | 静态角色候选 | 已有断言角色 | 原生消费者锚 / 现有 Source 锚 | 有限见证状态 |', '| --- | --- | --- | --- | --- |']
    for row in data['rows']:
        native=row['nativeConsumers'];source=row['sourceConsumerAnchors']
        anchor=(f"`{native[0]['path']}:{native[0]['line']}` ({native[0]['symbol']})"if native else'未定位原生 accessor')
        if source:anchor+=f"；Source `{source[0]['path']}` worker:{source[0]['workerLine']}"
        observed=', '.join(row['observedRoles'])or'无运行消费见证'
        status='限定见证'if row['runtimeWitnesses']else'待最小状态/效果见证'
        if row['sourceRawFactoryUnavailable']:status+='；raw factory 不可用'
        lines.append('| `'+row['id'].removeprefix('org.eclipse.elk.')+'` | '+row['staticRoleCandidate']+' | '+observed+' | '+anchor+' | '+status+' |')
    lines+=['','## 仍须最小见证的声明','',
            'JSON 每行都有 `minimalRemainingWitness` 与具体既有断言指针，下面仅按家族列有限缺口。几何/策略应使用真实适用输入的数值或执行后状态；callback 要真实调用；diagnostic/API metadata 要日志、presence、目标覆盖或查询状态，不强求几何变化。若 Source 仅提供 typed/internal 路径，就明确该通道，不伪造 raw factory。','']
    for family,names in data['unwitnessedByFamily'].items():
        lines.append('- **'+family+'** ('+str(len(names))+'): '+', '.join('`'+n.removeprefix('org.eclipse.elk.')+'`'for n in names))
    lines+=['','编译源包中的角色/默认声明与 getter 行只定位实现，不证明任何具体请求消费了值。已失败或无变化的尝试保留在 JSON；表中未获见证项不被提升为“已完成”，也不被归为算法缺失。','']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--build',action='store_true');mode.add_argument('--check',action='store_true')
    parser.add_argument('--branch-matrix',type=Path);parser.add_argument('--out',type=Path)
    args=parser.parse_args();branch=args.branch_matrix
    if branch is None and (ROOT/JSON_PATH).is_file():branch=load(ROOT/JSON_PATH).get('branchMatrixPath')
    before=digest((ROOT/'docs/option-coverage.json').read_bytes());data=build(branch_matrix=branch)
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
