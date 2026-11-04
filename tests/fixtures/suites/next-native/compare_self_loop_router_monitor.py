from pathlib import Path
import sys,json,hashlib
source,original,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from pyelk.algorithms.layered.graph import LGraph
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.self_loops_general import SelfLoopRouter
from pyelk.execution.diagnostics import BasicProgressMonitor
from layout_checks import diff
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();g.properties['EDGE_ROUTING']='ORTHOGONAL';monitor=BasicProgressMonitor(False,False);processor=SelfLoopRouter();director=processor.routing_director;slot=processor.routing_slot_assigner
running=monitor.is_running();processor.process(g,monitor=monitor)
actual={'beforeRunning':running,'afterRunning':monitor.is_running(),'closed':monitor._closed,'task':monitor.task_name,'emptyLayerCount':len(g.layers),'actualProcess50Executed':True}
expected=json.loads(original.read_text(encoding='utf8'))['value'];comparison=diff(expected,actual);assert before==hashes()
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':expected,'sameDirector':processor.routing_director is director,'sameSlotAssigner':processor.routing_slot_assigner is slot,'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'Only first native empty fourth-processor monitor control, against already saved correctly called source isRunning() tiny observation. Not filling/rewriting erroneous monitor fields in prior source3mode raw.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
