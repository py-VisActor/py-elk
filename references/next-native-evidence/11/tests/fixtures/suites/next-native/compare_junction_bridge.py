"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT [CASE_ID]; only changed junction paths."""
import hashlib,json,os,sys
from pathlib import Path
source,request_path,oracle_path,out_path=map(Path,sys.argv[1:5]);selected=sys.argv[5]if len(sys.argv)>5 else None
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.algorithms.box import _translate
from layout_checks import diff
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_text('utf-8'));oracle=json.loads(oracle_path.read_text('utf-8'));assert oracle['requestSha256']==sha(request_path)
rows=[]
for c in request['cases']:
 if selected and c['id']!=selected:continue
 graph={'id':'r','children':[{'id':'a'},{'id':'b'}],'edges':[{'id':'e','sources':['a'],'targets':['b'],'junctionPoints':[{'x':90,'y':91}]}]}
 if 'typed'in c:graph['edges'][0]['layoutOptions']={'elk.junctionPoints':c['typed']}
 state=JsonLayoutSession(graph);edge=state.edges[0]
 if c['operation']in('remove','rematerialize'):state.remove_option(edge,'junctionPoints')
 if c['operation']=='generated':state.set_generated_junction_points(edge,[dict(zip(('x','y'),p))for p in c['points']])
 if 'offset'in c:_translate(state.graph,*c['offset'],state)
 if c['operation']=='rematerialize':state.get_native_property(edge,'junctionPoints')
 present=state.has_option(edge,'junctionPoints');snapshot_has=state.property_snapshot(edge).has('junctionPoints')
 exported=state.export();rows.append({'id':c['id'],'present':present,'snapshotHas':snapshot_has,'points':exported['edges'][0]['junctionPoints']})
expected=[r for r in oracle['cases']if not selected or r['id']==selected];assert rows
comparison=diff(expected,rows);assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
report={'passed':comparison['passed'],'comparison':comparison,'actual':rows,'expected':expected,'sourceSha256':before,'pid':os.getpid(),'parentPid':os.getppid(),'requestSha256':sha(request_path),'oracleSha256':sha(oracle_path),'comparatorSha256':sha(Path(__file__)),'layoutExecuted':False,'fullValidation':False}
with out_path.open('x',encoding='utf-8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':report['passed'],'cases':len(rows),'differences':len(comparison['differences'])}));raise SystemExit(0 if report['passed']else 1)
