from pathlib import Path
import sys,json,hashlib
source,request,original,out,probe=map(Path,sys.argv[1:6]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();raw=json.loads(original.read_text(encoding='utf8'))
assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'and raw['requestSha256']==sha(request)and raw['probeSha256']==sha(probe)
sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from pyelk.algorithms.layered.longest_path_general import LongestPathLayerer
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,set_source,set_target
from pyelk.execution.diagnostics import BasicProgressMonitor
from layout_checks import diff
def hashes():return {p.relative_to(source).as_posix():sha(p)for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();input=json.loads(request.read_text(encoding='utf8'));graph=LGraph(None,None,None);ports=[]
for i in range(input['nodeCount']):
 node=LNode(graph);graph.layerless_nodes.append(node);port=LPort(node);node.ports.append(port);ports.append(port)
for a,b in input['edges']:
 edge=LEdge();set_source(edge,ports[a]);set_target(edge,ports[b])
owner=LongestPathLayerer();monitor=BasicProgressMonitor(False,False);error=None
try:owner.process(graph,monitor)
except Exception as caught:error={'name':type(caught).__name__,'message':str(caught)}
actual={'failed':error is not None,'layerlessCount':len(graph.layerless_nodes),'layerCount':len(graph.layers),'ownerGraphRetained':owner.layered_graph is graph,'heights':owner.node_heights,'monitorRunning':monitor.is_running(),'monitorClosed':monitor._closed}
comparison=diff(raw['value'],actual);assert hashes()==before;assert error and error['name']=='RecursionError'
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'expected':raw['value'],'actual':actual,'originalRawError':raw['rawError'],'nativeRawError':error,'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':sha(original),'scope':'Sole new raw-cycle host failure boundary: finite failure/no geometry fallback/no successcleanup. Error classes/messages/timing are explicitly different; no public acyclic restriction introduced and no successful phase rerun.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
