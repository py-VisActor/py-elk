"""Reproducible E09 requests. This builder never imports the candidate package.

The original 25 master byte streams are retained. Added requests are fixed
before candidate execution; generated positives remain in ADR0008's 8/28 domain.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
from layout_checks import ROOT, load, write
from e07_geometry_premise import premises

SUITE = 'tests/fixtures/suites/E09'
MASTER = 'tests/fixtures/validation'
FLAGS = ((False, False), (True, False), (False, True), (True, True))
STRESSES = (('E05','e05-multiskip-permuted-eight'),('E06','e06-dense-cyclic-eight'),
            ('E06','e06-max-longedge-eight'),('E06','e06-mixed-eight-edge-limit'),
            ('E06','e06-reciprocal-twenty-eight'),('E06','e06-selfloop-twenty-eight'))

def encoded(value):
    return (json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode()

def math_request(request):
    """Explicit diagnostics-only view; never changes raw inputs or old profile."""
    view=copy.deepcopy(request)
    for key in ('logging','measureExecutionTime'):
        if key in view['layoutArguments']:
            if type(view['layoutArguments'][key]) is not bool: raise ValueError('Nonboolean diagnostics flag')
            del view['layoutArguments'][key]
    if type(view['graph']) is dict: view['graph'].pop('logging',None)
    return view

def geometry_policy(request):
    p=premises(math_request(request))
    if p is None: raise ValueError('Positive outside independent bounded premise')
    o=p['options']; graph=request['graph']; nodes=graph.get('children',[])
    adjacency={n['id']:[] for n in nodes}
    for edge in graph.get('edges',[]): adjacency[edge['sources'][0]].append(edge['targets'][0])
    gray=set();black=set()
    def cyclic(node):
        if node in gray:return True
        if node in black:return False
        gray.add(node)
        if any(cyclic(x) for x in adjacency[node]):return True
        gray.remove(node);black.add(node);return False
    forward=not any(cyclic(node) for node in adjacency)
    policy={'profile':'basic-flat-orthogonal','direction':'RIGHT' if o['direction']=='UNDEFINED' else o['direction'],
            'padding':o['padding'],'nodeNode':o['spacing.nodeNode'],'betweenLayers':o['layered.spacing.nodeNodeBetweenLayers'],
            'forwardEdges':forward,'rankSeparation':'default-layered-adjacent-edge-v3'}
    if o['separateConnectedComponents']:policy['layerFrame']='independent-components-v1'
    return policy

def generated(index):
    family=index//4; direction=('RIGHT','LEFT','DOWN','UP')[index%4]
    state=0xE0900001+index
    def step():
        nonlocal state
        state=(1664525*state+1013904223)&0xffffffff
        return state
    count=(6,6,7,8,8,8)[family]
    sizes=(0,0.125,1.25,3.5,31,0.0000001,17.75,1000000)
    children=[{'id':'n'+str(i),'width':sizes[(i+index)%8],'height':sizes[(i*3+index+1)%8]} for i in range(count)]
    if family==0:
        pairs=[(i,i+1) for i in range(count-1)]
        pairs += [(a,b) for a in range(count) for b in range(a+2,count) if step()%3==0]
    elif family==1:pairs=[(i,(i+1)%count) for i in range(count)]+[(0,3),(1,4),(5,2)]
    elif family==2:pairs=[(i,(i+1)%count) for i in range(count)]+[(0,0),(3,3),(0,1),(1,0),(5,2)]
    elif family==3:pairs=[(0,1),(1,2),(0,2),(3,4),(4,5),(5,3)]
    elif family==4:pairs=[]
    else:
        pairs=[(a,b) for a in range(count) for b in range(a+1,count)]
        for i in range(len(pairs)-1,0,-1):
            j=step()%(i+1);pairs[i],pairs[j]=pairs[j],pairs[i]
    edges=[{'id':'e'+str(i),'sources':['n'+str(a)],'targets':['n'+str(b)]} for i,(a,b) in enumerate(pairs)]
    return {'schema':'py-elk-layout-request/v1','constructor':{},'layoutArguments':{
        'logging':family in (1,2,3,5),'measureExecutionTime':family in (0,2,4,5)},
        'graph':{'id':'root','layoutOptions':{'elk.algorithm':'layered','elk.direction':direction,
            'elk.randomSeed':str((step()%2147483647)+1),'elk.separateConnectedComponents':'false' if index%2 else 'true',
            'elk.padding':'[top=0.125,left=1.25,bottom=3.5,right=0]',
            'elk.spacing.nodeNode':str((0,0.125,20,1000000)[index%4]),
            'elk.layered.spacing.nodeNodeBetweenLayers':str((20,0.125,0,1000000)[index%4])},
            'children':children,'edges':edges}}

def definitions(root=ROOT):
    root=Path(root); entries=[]; raws={}
    def add(identifier,raw,outcome,origin,master=None):
        request=json.loads(raw); item={'id':identifier,'request':'requests/'+identifier+'.json',
            'requestSha256':hashlib.sha256(raw).hexdigest(),'expectedOutcome':outcome,'origin':origin}
        if master:item['masterId']=master
        if outcome=='returned':item['geometry']=geometry_policy(request)
        entries.append(item);raws[item['request']]=raw
    masters=load(root/MASTER/'cases.json')['cases']
    if len(masters)!=25:raise ValueError('Master denominator differs')
    for master in masters:
        raw=(root/MASTER/master['request']).read_bytes(); original=json.loads(raw)
        add(master['id'],raw,master['expectedOutcome'],'master-original',master['id'])
        for logs,times in FLAGS[1:]:
            request=copy.deepcopy(original);request['layoutArguments'].update(logging=logs,measureExecutionTime=times)
            add(master['id']+'-flags-'+str(int(logs))+str(int(times)),encoded(request),master['expectedOutcome'],'master-diagnostics',master['id'])
    for index in range(24):add('generated-'+str(index).zfill(2),encoded(generated(index)),'returned','fixed-lcg-0xE0900001')
    base=json.loads((root/MASTER/'requests/layered-chain.json').read_bytes())
    for value_name,value in (('object',{'name':'BUSINESS_ROOT','executionTime':19,'children':[{'logging':41}]}),('null',None)):
        for logs,times in FLAGS:
            request=copy.deepcopy(base);request['layoutArguments'].update(logging=logs,measureExecutionTime=times)
            graph=request['graph'];graph['logging']=value;graph['executionTime']=321
            graph['business']={'logging':{'executionTime':765,'children':[{'name':'Recursive Graph Layout','executionTime':-7}]}}
            graph['children'][0]['logging']={'executionTime':123,'name':'LEAF_BUSINESS'}
            graph['edges'][0]['logging']={'executionTime':456,'name':'EDGE_BUSINESS'}
            add('reserved-'+value_name+'-'+str(int(logs))+str(int(times)),encoded(request),'returned','reserved-business-isolation')
    for suite,identifier in STRESSES:
        parent=root/'tests/fixtures/suites'/suite
        item=next(x for x in load(parent/'cases.json')['cases'] if x['id']==identifier)
        for times in (False,True):
            request=load(parent/item['request']);request['layoutArguments'].update(logging=True,measureExecutionTime=times)
            add(identifier+'-logs-'+str(int(times)),encoded(request),'returned','prior-project-stress')
    if len(entries)!=144 or len({x['id'] for x in entries})!=144:raise ValueError('E09 denominator differs')
    return {'schema':'py-elk-e09-coverage-suite/v1','caseCount':144,'masterCount':25,
            'generatedCount':24,'fullReferenceCounts':{'algorithms':12,'options':243,'categories':8},'cases':entries},raws

def host_definitions(root=ROOT):
    """Independent host rejection contracts, taken from reviewed admission rules.

    These are explicitly Python host tests. Broader JavaScript acceptance is
    not a reason to silently expand the bounded native input domain.
    """
    base=load(Path(root)/MASTER/'requests/layered-chain.json');rows=[]
    def add(identifier,mutate,path,message,*,name='UnsupportedFeatureError',code='UNSUPPORTED_SLICE'):
        request=copy.deepcopy(base);mutate(request)
        rows.append({'id':identifier,'request':request,'expected':{'outcome':'threw','error':{'name':name,'code':code,'path':path,'message':message}}})
    def option(r,key,value):r['graph']['layoutOptions'][key]=value
    add('nodes-9',lambda r:r['graph'].update(children=[{'id':'n'+str(i),'width':1,'height':1} for i in range(9)],edges=[]),'/children','The reviewed domain has at most 8 child nodes')
    add('edges-29',lambda r:r['graph'].update(edges=[{'id':'e'+str(i),'sources':['a'],'targets':['b']} for i in range(29)]),'/edges','The reviewed multigraph domain has at most 28 original edges')
    add('measure-over',lambda r:r['graph']['children'][0].update(width=1000001),'/children/0/width','Given dimensions must lie within the reviewed domain')
    add('spacing-over',lambda r:option(r,'elk.spacing.nodeNode','1000001'),'/layoutOptions/org.eclipse.elk.spacing.nodeNode','Spacing exceeds the reviewed numeric domain')
    add('padding-over',lambda r:option(r,'elk.padding','[top=1000001,left=0,bottom=0,right=0]'),'/layoutOptions/elk.padding','Padding exceeds the reviewed numeric domain')
    add('seed-zero',lambda r:option(r,'elk.randomSeed','0'),'/layoutOptions/elk.randomSeed','This slice requires an explicit deterministic seed branch')
    add('ports',lambda r:r['graph']['children'][0].update(ports=[{'id':'p','width':0,'height':0}]),'/children/0/ports','Explicit shape capability is outside this slice')
    add('labels',lambda r:r['graph']['children'][0].update(labels=[{'text':'label','width':1,'height':1}]),'/children/0/labels','Explicit shape capability is outside this slice')
    add('compound',lambda r:r['graph']['children'][0].update(children=[{'id':'nested','width':1,'height':1}]),'/children/0/children','Child-local capability is outside this slice')
    add('edge-local-options',lambda r:r['graph']['edges'][0].update(layoutOptions={'elk.direction':'RIGHT'}),'/edges/0/layoutOptions','Existing routing or edge-local capability is outside this slice')
    add('child-local-options',lambda r:r['graph']['children'][0].update(layoutOptions={'elk.direction':'RIGHT'}),'/children/0/layoutOptions','Only reviewed leaf-node padding is admitted locally')
    add('hyperedge',lambda r:r['graph']['edges'][0].update(sources=['a','b']),'/edges/0','This slice requires child-node single-source/target edges')
    add('root-endpoint',lambda r:r['graph']['edges'][0].update(sources=['root']),'/edges/0','This slice requires child-node single-source/target edges')
    add('legacy-properties',lambda r:r['graph'].update(properties={}),'/properties','Legacy option containers require a separate source branch')
    add('reference-hash',lambda r:r['graph'].update({'$H':7}),'/$H','Existing reference identity-cache fields are outside this slice')
    def numeric_id(r):
        r['graph']['children'][0]['id']=7;r['graph']['edges'][0]['sources']=[7]
    add('nonstring-id',numeric_id,'/children/0/id','This slice requires nonempty string identities')
    for key in ('x','y','width','height'):
        add('root-'+key,lambda r,k=key:r['graph'].update({k:0}),'/'+key,'Pre-existing root geometry uses a separate source branch')
    for key in ('x','y'):
        add('child-'+key,lambda r,k=key:r['graph']['children'][0].update({k:0}),'/children/0/'+key,'Pre-existing node positions are outside this slice')
    for key in ('sections','junctionPoints','bendPoints','startPoint','endPoint','sourcePoint','targetPoint','container'):
        value='root' if key=='container' else [] if key in ('sections','junctionPoints','bendPoints') else {'x':0,'y':0}
        add('edge-'+key,lambda r,k=key,v=value:r['graph']['edges'][0].update({k:v}),'/edges/0/'+key,'Pre-existing edge geometry requires a different source branch')
    add('padding-object',lambda r:option(r,'elk.padding',{'top':0,'left':0,'bottom':0,'right':0}),'/layoutOptions/elk.padding','This slice requires the reference-compatible padding string')
    add('child-padding-object',lambda r:r['graph']['children'][0].update(layoutOptions={'elk.padding':{'top':0,'left':0,'bottom':0,'right':0}}),'/children/0/layoutOptions','Child padding requires the reviewed four-side string')
    for flag in ('logging','measureExecutionTime'):
        for label,value in (('zero',0),('one',1),('text','true'),('null',None)):
            add(flag+'-'+label,lambda r,k=flag,v=value:r['layoutArguments'].update({k:v}),'/layoutArguments/'+flag,'Logging/timing flags must be booleans')
    for label,value in (('seed-negative-boundary',-2147483648),('seed-positive-boundary',2147483647)):
        request=copy.deepcopy(base);option(request,'elk.randomSeed',str(value))
        rows.append({'id':label,'request':request,'expected':{'outcome':'returned'},'geometry':geometry_policy(request)})
    for key,value,message in (
        ('algorithm',17,'Algorithm must be a string'),
        ('direction',17,'Expected one of: UNDEFINED, RIGHT, LEFT, DOWN, UP'),
        ('padding',17,'Padding requires all and only top/right/bottom/left'),
        ('spacing.nodeNode',True,'Expected a finite nonnegative number'),
        ('layered.spacing.nodeNodeBetweenLayers',True,'Expected a finite nonnegative number'),
        ('separateConnectedComponents',17,'Expected bool or a true/false string'),
        ('spacing.componentComponent',True,'Expected a finite nonnegative number'),
        ('edgeRouting',17,'Expected one of: ORTHOGONAL'),
        ('randomSeed',True,'Seed must be a signed 32-bit integer')):
        add('invalid-option-'+key,lambda r,k=key,v=value:option(r,'elk.'+k,v),'/local/elk.'+key,message,
            name='OptionValidationError',code='INVALID_OPTION_VALUE')
    add('same-scope-alias-conflict',lambda r:option(r,'org.eclipse.elk.direction','RIGHT'),'/local/org.eclipse.elk.direction',
        'Two aliases for the same option in one scope',name='OptionValidationError',code='AMBIGUOUS_OPTION')
    return {'schema':'py-elk-e09-host-checks/v1','publicCases':rows,'clockMode':'controlled primitive ticks are not real layout timing',
            'kernelInstrumentation':'provider import/transfer boundaries and trace snapshots; no public ELK lifecycle claim'}

def check(root=ROOT,suite=None):
    suite=Path(suite or Path(root)/SUITE);expected,raws=definitions(root)
    from validate_e04_runtime import exact
    exact(load(suite/'cases.json'),expected,'E09 suite differs from independent generation')
    if {p.relative_to(suite).as_posix() for p in (suite/'requests').glob('*.json')}!=set(raws):raise ValueError('E09 request file denominator differs')
    for name,raw in raws.items():
        if (suite/name).read_bytes()!=raw:raise ValueError('E09 request bytes differ: '+name)
    exact(load(suite/'host-checks.json'),host_definitions(root),'E09 host contracts differ from independent definitions')
    return {'passed':True,'caseCount':144,'masterCount':25,'generatedCount':24}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('build','check'))
    parser.add_argument('--out',type=Path);parser.add_argument('--suite',type=Path);args=parser.parse_args()
    if args.action=='build':
        if args.out is None:parser.error('--out required')
        args.out.mkdir(parents=True,exist_ok=False);suite,raws=definitions()
        for name,raw in raws.items():
            path=args.out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        write(args.out/'cases.json',suite)
        write(args.out/'host-checks.json',host_definitions())
    else:print(json.dumps(check(suite=args.suite)))

if __name__=='__main__':main()
