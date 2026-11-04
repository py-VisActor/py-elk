from pathlib import Path
import sys,json,hashlib,re
source,request,original,worker,probe,out=map(Path,sys.argv[1:7]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
raw=json.loads(original.read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(worker)==raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert sha(probe)==raw['probeSha256'];assert sha(request)==raw['requestSha256']
rows=re.findall(r"new IntermediateProcessorStrategy(?:\$\d+)?\('([^']+)', (\d+)\)",worker.read_text(encoding='utf8'));assert len(rows)==59
ordinals={name:int(index)for name,index in rows};assert len(ordinals)==59
from pyelk.algorithms.layered.spline_general import SplineEdgeRouter
from pyelk.algorithms.layered.graph import LGraph
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from layout_checks import diff
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts};actual=[]
router=SplineEdgeRouter()
for input in json.loads(request.read_text(encoding='utf8'))['cases']:
 g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();g.properties['GRAPH_PROPERTIES']=set(input['flags']);config=router.get_layout_processor_configuration(g)
 actual.append([[p.name for p in sorted(values,key=lambda p:p.ordinal)]for values in config.list])
expected=[value['configuration']for value in raw['value']];raw_comparison=diff(expected,actual)
# Source assembler's accepted consumer sorts factory enums by actual ordinal.
# This projection is separate from the retained raw HashSet encounter order.
consumer_expected=[[sorted(values,key=ordinals.__getitem__)for values in config]for config in expected]
consumer_actual=[[sorted(values,key=ordinals.__getitem__)for values in config]for config in actual]
comparison=diff(consumer_expected,consumer_actual);assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
out.write_text(json.dumps({'passed':comparison['passed'],'consumerStrict':comparison['passed'],'rawStrict':raw_comparison['passed'],'comparison':comparison,'rawComparison':raw_comparison,'sourceRawConfiguration':expected,'nativeConfiguration':actual,'sourceConsumerConfiguration':consumer_expected,'nativeConsumerConfiguration':consumer_actual,'sourceOrdinalRows':rows,'workerSha256':sha(worker),'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':sha(original),'scope':'Only new affected configuration getter control after fixing NS_POST beforeP5; saved source configuration reused, no geometry/producer/rank/main calculations. Raw HashSet order parity remainsfalse; actual source assembler ordinal-sorted consumer projection is separately checked as approved by Root. No profile changes or old data rewritten.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'consumerStrict':comparison['passed'],'rawStrict':raw_comparison['passed'],'rawDifferences':len(raw_comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
