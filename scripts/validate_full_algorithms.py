"""Unified public ELK differential. Reference capture is immutable and reused.

--build creates deterministic requests; --reference runs ONE original Node batch;
--native captures public Python API only; --compare retains every raw difference.
Random and upstream errors are explicitly reported, never accepted as exact PASS.
"""
from __future__ import annotations
import argparse,asyncio,copy,hashlib,json,math,os,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SUITE=ROOT/'tests/fixtures/suites/full-native-algorithms/cases.json'
P1=('GREEDY','DEPTH_FIRST','INTERACTIVE','MODEL_ORDER','GREEDY_MODEL_ORDER','SCC_CONNECTIVITY','SCC_NODE_TYPE','DFS_NODE_ORDER','BFS_NODE_ORDER')
P2=('NETWORK_SIMPLEX','LONGEST_PATH','LONGEST_PATH_SOURCE','COFFMAN_GRAHAM','BF_MODEL_ORDER','DF_MODEL_ORDER','INTERACTIVE','MIN_WIDTH','STRETCH_WIDTH')
ALGORITHMS=('layered','fixed','box','random','mrtree','radial','force','stress','disco','rectpacking','sporeOverlap','sporeCompaction')
def digest(b):return hashlib.sha256(b).hexdigest()
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf8',newline='\n')as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def load(path):return json.loads(path.read_bytes())
def source_hashes():return {p.relative_to(ROOT).as_posix():digest(p.read_bytes())for p in (ROOT/'src/pyelk').rglob('*.py')}
def build():
 rows=[]
 def add(cid,req,group,mode='deterministic',origin=None):
  target=SUITE.parent/'requests'/f'{cid}.json';write(target,req);rows.append(dict(id=cid,request='requests/'+target.name,requestSha256=digest(target.read_bytes()),group=group,comparisonMode=mode,origin=origin))
 def graph(algorithm):
  return {'id':'root','business':{'keep':['all',0,False]},'layoutOptions':{'elk.algorithm':algorithm,'elk.randomSeed':53},'children':[{'id':f'n{i}','width':20+i*3,'height':12+i*2,'x':i*47,'y':i*29}for i in range(5)],'edges':[{'id':f'e{i}','sources':[f'n{a}'],'targets':[f'n{b}']}for i,(a,b)in enumerate(((0,1),(0,2),(1,3),(2,3),(3,4)))]}
 for alg in ALGORITHMS:
  g=graph(alg)
  if alg=='fixed':g['edges']=[]
  add('basic-'+alg,dict(schema='py-elk-layout-request/v1',constructor={},graph=g,layoutArguments={}), 'algorithm-basic')
 for p1 in P1:
  for p2 in P2:
   g=graph('layered');g['children'] +=[{'id':'n5','width':27,'height':19,'x':210,'y':21},{'id':'n6','width':22,'height':15,'x':250,'y':45}]
   g['edges'] +=[{'id':'back','sources':['n3'],'targets':['n0']},{'id':'parallel','sources':['n0'],'targets':['n1']},{'id':'tail','sources':['n4'],'targets':['n5']}]
   g['layoutOptions'].update({'elk.layered.cycleBreaking.strategy':p1,'elk.layered.layering.strategy':p2})
   add('p1-'+p1.lower()+'--p2-'+p2.lower(),dict(schema='py-elk-layout-request/v1',constructor={},graph=g,layoutArguments={}), 'p1-p2-cartesian')
 # Previously defined PUBLIC requests, not prepared internal DTO probes.
 base=ROOT/'tests/fixtures/suites/next-native'
 for dirname in ('fixed-branches','box-random-branches','mrtree-first','radial-first','force-stress-first','spore-providers','random-unseeded','provider-state','stress-inline-default','mrtree-diagnostics'):
  folder=base/dirname
  if not (folder/'cases.json').exists():continue
  for c in load(folder/'cases.json')['cases']:
   path=folder/c['request'];req=load(path)
   if req.get('schema')!='py-elk-layout-request/v1':continue
   mode='nondeterministic'if dirname=='random-unseeded'else'deterministic'
   add('branch-'+dirname+'-'+c['id'],req,'algorithm-option',mode,path.relative_to(ROOT).as_posix())
 for c in load(ROOT/'tests/fixtures/suites/E09/cases.json')['cases']:
  if c.get('origin')=='master-original':
   path=ROOT/'tests/fixtures/suites/E09'/c['request'];add('master-'+c['id'],load(path),'master',origin=path.relative_to(ROOT).as_posix())
 write(SUITE,dict(schema='py-elk-full-algorithms-suite/v1',algorithms=list(ALGORITHMS),p1=list(P1),p2=list(P2),cases=rows))
 print(json.dumps({'built':len(rows),'suite':str(SUITE)}))
def command(argv,out,timeout=600):
 out.mkdir(parents=True,exist_ok=False);start=time.time();p=subprocess.Popen(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:stdout,stderr=p.communicate(timeout=timeout);timed=False
 except subprocess.TimeoutExpired:p.kill();stdout,stderr=p.communicate();timed=True
 (out/'stdout.log').write_bytes(stdout);(out/'stderr.log').write_bytes(stderr)
 write(out/'command.json',dict(argv=argv,cwd=str(ROOT),pid=p.pid,exitCode=p.returncode,timedOut=timed,elapsedSeconds=time.time()-start,stdoutSha256=digest(stdout),stderrSha256=digest(stderr)))
 return p.returncode
async def native(out,selected):
 sys.path.insert(0,str(ROOT/'src'));from pyelk import ELK
 out.mkdir(parents=True,exist_ok=False);before=source_hashes();rows=[]
 for c in load(SUITE)['cases']:
  if selected and c['id']not in selected:continue
  raw=(SUITE.parent/c['request']).read_bytes();assert digest(raw)==c['requestSha256'];req=json.loads(raw)
  graph=copy.deepcopy(req['graph']);constructor=copy.deepcopy(req['constructor']);args=copy.deepcopy(req['layoutArguments']);elk=None;start=time.perf_counter()
  obs=dict(id=c['id'],requestSha256=digest(raw),inputBefore=copy.deepcopy(graph))
  try:
   elk=ELK(constructor,timeout=12);obs['result']=await elk.layout(graph,args);obs['outcome']='returned'
  except Exception as e:obs.update(outcome='threw',error=dict(name=type(e).__name__,message=str(e),code=getattr(e,'code',None)),stack=traceback.format_exc())
  obs.update(elapsedSeconds=time.perf_counter()-start,inputAfter=graph,constructorAfter=constructor,argumentsAfter=args)
  if elk:
   obs['trace']=elk.last_trace
   try:elk.terminateWorker();obs['termination']={'outcome':'returned','returnKind':'NoneType'}
   except Exception as e:obs['termination']={'outcome':'threw','name':type(e).__name__,'message':str(e)}
  write(out/(c['id']+'.json'),obs);rows.append(dict(id=c['id'],sha256=digest((out/(c['id']+'.json')).read_bytes()),outcome=obs['outcome']))
  print(json.dumps({'id':c['id'],'outcome':obs['outcome']}),flush=True)
 write(out/'receipt.json',dict(schema='py-elk-full-algorithms-native/v1',publicModule=str(sys.modules['pyelk'].__file__),pid=os.getpid(),python=sys.version,suiteSha256=digest(SUITE.read_bytes()),sourceBefore=before,sourceAfter=source_hashes(),rows=rows))
def compare(reference,candidate,out):
 from layout_checks import diff,pointer,_GEOMETRY
 refrec=load(reference/'receipt.json');candrec=load(candidate/'receipt.json');assert refrec['suiteSha256']==candrec['suiteSha256']==digest(SUITE.read_bytes())
 assert refrec['distribution']==load(ROOT/'UPSTREAM.json')['distribution']['sha256Files']
 rm={c['id']:c for c in refrec['rows']};cm={c['id']:c for c in candrec['rows']};rows=[]
 def generated(graph,path='/result'):
  paths=set()
  if '$H'not in graph:paths.add(path+'/$H')
  for key in ('children','ports'):
   for i,child in enumerate(graph.get(key,[])):paths|=generated(child,pointer(pointer(path,key),i))
  return paths
 def nonfinite(value,path='/result'):
  if _GEOMETRY.fullmatch(path):return [path]if type(value)not in(int,float)or not math.isfinite(value)else[]
  if isinstance(value,dict):return [p for k,v in value.items()for p in nonfinite(v,pointer(path,k))]
  if isinstance(value,list):return[p for i,v in enumerate(value)for p in nonfinite(v,pointer(path,i))]
  return[]
 for c in load(SUITE)['cases']:
  cid=c['id']
  if cid not in cm:continue
  rp=reference/(cid+'.json');cp=candidate/(cid+'.json');assert digest(rp.read_bytes())==rm[cid]['sha256']and digest(cp.read_bytes())==cm[cid]['sha256']
  a,b=load(rp),load(cp);req=load(SUITE.parent/c['request']);assert a['requestSha256']==b['requestSha256']==c['requestSha256']
  row=dict(id=cid,group=c['group'],comparisonMode=c['comparisonMode'],referenceOutcome=a['outcome'],nativeOutcome=b['outcome'],referenceSha256=rm[cid]['sha256'],nativeSha256=cm[cid]['sha256'])
  row['inputPreserved']=diff(req['graph'],b['inputAfter'])['passed']and diff(req['constructor'],b['constructorAfter'])['passed']and diff(req['layoutArguments'],b['argumentsAfter'])['passed']
  row['rawCallerMutationDifference']=diff({k:a[k]for k in ('inputAfter','constructorAfter','argumentsAfter')},{k:b[k]for k in ('inputAfter','constructorAfter','argumentsAfter')})
  row['callerPolicy']='Native preserves owned caller JSON; original generated hash mutations are retained as raw differences, not required to mutate native caller inputs.'
  if a['outcome']=='returned'and b['outcome']=='returned':
   strict=diff({'result':a['result']},{'result':b['result']});tol=diff({'result':a['result']},{'result':b['result']},tolerant=True)
   generated_paths=generated(req['graph']);classified=[d for d in tol['differences']if d['path']in generated_paths and d['kind']=='missing'and type(d.get('expected'))is int]
   mandatory=[d for d in tol['differences']if d not in classified];invalid=nonfinite(a['result'])+nonfinite(b['result'])
   row.update(rawStrictDifference=strict,coordinateToleranceDifference=tol,generatedRuntimeHashDifferences=classified,mandatoryDifferences=mandatory,nonfiniteGeometryPaths=invalid)
   random_bad=[d for d in mandatory if not _GEOMETRY.fullmatch(d['path'])]
   row['status']=('NONDETERMINISTIC_OBSERVATION'if c['comparisonMode']=='nondeterministic'and not random_bad and not invalid and row['inputPreserved']else'UPSTREAM_NONFINITE_WIRE_PARITY'if invalid and not mandatory and row['inputPreserved']else'PASS'if not mandatory and row['inputPreserved']else'FAIL')
  elif a['outcome']=='threw':
   shared_error={k:b.get('error',{}).get(k)for k in ('name','message')}
   row.update(status='UPSTREAM_ERROR_OBSERVATION'if b['outcome']=='threw'and row['inputPreserved']else'FAIL',referenceError=a.get('error'),nativeError=b.get('error'),exactErrorParity=a.get('error')==shared_error,errorContractDifference=diff(a.get('error'),shared_error))
  else:row.update(status='FAIL',nativeError=b.get('error'),nativeStack=b.get('stack'))
  rows.append(row)
 counts={status:sum(r['status']==status for r in rows)for status in sorted({r['status']for r in rows})}
 write(out,dict(schema='py-elk-full-algorithms-comparison/v1',counts=counts,executed=len(rows),rows=rows,referenceReceiptSha256=digest((reference/'receipt.json').read_bytes()),nativeReceiptSha256=digest((candidate/'receipt.json').read_bytes()),sourceStable=candrec['sourceBefore']==candrec['sourceAfter'],scope='Public ELK API; generated absent shape $H classified explicitly, raw differences retained; existing geometry tolerances 1e-6/1e-9 only. Upstream errors and random trajectories are not conformance PASS.'))
 print(json.dumps({'executed':len(rows),'counts':counts,'failed':[r['id']for r in rows if r['status']=='FAIL']}))
 return 1 if counts.get('FAIL',0)or candrec['sourceBefore']!=candrec['sourceAfter']else 0
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',action='store_true');p.add_argument('--reference',type=Path);p.add_argument('--native',type=Path);p.add_argument('--native-capture',type=Path);p.add_argument('--compare',nargs=3,type=Path);p.add_argument('--ids',nargs='*');args=p.parse_args()
 if args.build:build()
 if args.reference:
  return command([r'C:\Program Files\nodejs\node.exe',str(ROOT/'tools/reference/full_algorithms.cjs'),str(ROOT/'.local/npm-elkjs/package'),str(SUITE),str(args.reference.resolve()/'observations')],args.reference)
 if args.native_capture:
  return command([sys.executable,str(Path(__file__).resolve()),'--native',str(args.native_capture.resolve()/'observations')]+(['--ids']+args.ids if args.ids else[]),args.native_capture)
 if args.native:asyncio.run(native(args.native,args.ids))
 if args.compare:return compare(*args.compare)
 return 0
if __name__=='__main__':raise SystemExit(main())
