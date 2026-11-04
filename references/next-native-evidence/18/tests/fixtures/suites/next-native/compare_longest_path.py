from pathlib import Path
import sys,json,hashlib,copy
source,request,original,out,probe=map(Path,sys.argv[1:6]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
raw=json.loads(original.read_text(encoding='utf8'));assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert raw['requestSha256']==sha(request)and raw['probeSha256']==sha(probe)
sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from pyelk.algorithms.layered.longest_path_general import LongestPathLayerer,LongestPathSourceLayerer
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Vec2,set_source,set_target
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.ports import set_side
from pyelk.execution.diagnostics import BasicProgressMonitor
from layout_checks import diff
def hashes():return {p.relative_to(source).as_posix():sha(p)for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
initial_hashes=hashes();input=json.loads(request.read_text(encoding='utf8'));result=[];configurations=[];class_cache_controls=[]
for variant in input['variants']:
 graph=LGraph(None,None,None);graph.properties=CanonicalPropertyMap();nodes={};ports={}
 for name in input['nodeOrder']:
  node=LNode(graph);node.properties=CanonicalPropertyMap();graph.layerless_nodes.append(node);nodes[name]=node
  for side in ['in','out']:
   port=LPort(node);port.properties=CanonicalPropertyMap();node.ports.append(port);set_side(port,'WEST'if side=='in'else'EAST');ports[name+':'+side]=port
 for index,(a,b)in enumerate(input['edges']):
  edge=LEdge(id=index);edge.properties=CanonicalPropertyMap();set_source(edge,ports[a+':out']);set_target(edge,ports[b+':in'])
 layerless=graph.layerless_nodes;layers=graph.layers;cls=LongestPathLayerer if variant=='LONGEST_PATH'else LongestPathSourceLayerer;owner=cls();cfg=owner.get_layout_processor_configuration(graph);configurations.append(cfg)
 class_cache_controls.append(owner.get_layout_processor_configuration(graph)is cfg and cls().get_layout_processor_configuration(graph)is cfg)
 configuration=[[p.name for p in sorted(slot,key=lambda p:p.ordinal)]for slot in cfg.list]
 monitor=BasicProgressMonitor(False,False);owner.process(graph,monitor);names={id(node):name for name,node in nodes.items()}
 result.append({'variant':variant,'layers':[[names[id(node)]for node in layer.nodes]for layer in graph.layers],'ids':[{'name':name,'id':node.id,'layer':graph.layers.index(node.layer)}for name,node in nodes.items()],'sameLayerless':layerless is graph.layerless_nodes,'sameLayers':layers is graph.layers,'layerlessCount':len(graph.layerless_nodes),'ownerGraphCleared':owner.layered_graph is None,'ownerHeightsCleared':owner.node_heights is None,'monitorName':monitor.task_name,'monitorRunning':monitor.is_running(),'monitorClosed':monitor._closed,'configurationByOrdinal':configuration})
expected=copy.deepcopy(raw['value']);raw_configs=[item.pop('rawConfiguration')for item in expected];comparison=diff(expected,result);assert hashes()==initial_hashes
assert all(class_cache_controls)and configurations[0]is not configurations[1]
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':result,'expected':expected,'sourceRawConfigurations':raw_configs,'rawSetOrderEquivalenceClaimed':False,'nativeExtraControl':{'sameClassPersistentConfiguration':all(class_cache_controls),'differentClassDistinctConfiguration':configurations[0]is not configurations[1]},'sourceFilesSha256':initial_hashes,'sourceTreeUnchanged':True,'originalSha256':sha(original),'scope':'First actual new two real longest-path variants on shared-source request DAG/parallel/selfloop/disconnected/encounter-order graph. All node scratch IDs/layer order/list identities/successcleanup/monitor compare; actual ordinal assembler consumption separate from source raw HashSet encounter. No old group/full/public layout executed.'},indent=2)+'\n',encoding='utf8')
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
