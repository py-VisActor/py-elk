from pathlib import Path
import sys,json,hashlib,copy
source,request,original,out,probe=map(Path,sys.argv[1:6]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();raw=json.loads(original.read_text(encoding='utf8'))
assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'and raw['requestSha256']==sha(request)and raw['probeSha256']==sha(probe)
sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from pyelk.algorithms.layered.coffman_graham_general import CoffmanGrahamLayerer
from pyelk.algorithms.layered.integer_box_tokens import value_of_integer_box
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,set_source,set_target
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.ports import set_side
from pyelk.execution.diagnostics import BasicProgressMonitor
from layout_checks import diff
def hashes():return {p.relative_to(source).as_posix():sha(p)for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();input=json.loads(request.read_text(encoding='utf8'));comparators=[]
for item in input['comparatorProbes']:
 graph=LGraph(None,None,None);left=LNode(graph,id=0);right=LNode(graph,id=1);owner=CoffmanGrahamLayerer();shared=value_of_integer_box(128)if item.get('sharedLarge')else None
 for number in item['left']:owner.in_topological.put(left,value_of_integer_box(number)if shared is None else shared)
 for number in item['right']:owner.in_topological.put(right,value_of_integer_box(number)if shared is None else shared)
 comparators.append({'name':item['name'],'value':owner._compare_nodes_in_topological(left,right),'scope':'Instrumented private inTopo objects, not an ordinary layout request.'})
owner=CoffmanGrahamLayerer();initial_map=owner.in_topological;cases=[]
for width in input['widths']:
 graph=LGraph(None,None,None,properties=CanonicalPropertyMap());graph.properties['LAYERING_COFFMAN_GRAHAM_LAYER_BOUND']=width;nodes={};ports={};edges=[]
 for name in input['nodeOrder']:
  node=LNode(graph,properties=CanonicalPropertyMap());graph.layerless_nodes.append(node);nodes[name]=node
  for kind in ['in','out']:
   port=LPort(node,properties=CanonicalPropertyMap());node.ports.append(port);set_side(port,'WEST'if kind=='in'else'EAST');ports[name+':'+kind]=port
 for i,(first,second)in enumerate(input['edges']):
  edge=LEdge(id=100+i,properties=CanonicalPropertyMap());set_source(edge,ports[first+':out']);set_target(edge,ports[second+':in']);edges.append(edge)
 layers=graph.layers;layerless=graph.layerless_nodes;monitor=BasicProgressMonitor(False,False);owner.process(graph,monitor);names={id(node):name for name,node in nodes.items()};cfg=owner.get_layout_processor_configuration(graph)
 cases.append({'width':width,'layers':[[names[id(node)]for node in layer.nodes]for layer in graph.layers],'nodes':[{'name':name,'id':node.id,'layer':graph.layers.index(node.layer)}for name,node in nodes.items()],'edgeIds':[edge.id for edge in edges],'nodeMark':owner.node_mark,'edgeMark':owner.edge_mark,'inDegree':owner.in_degree,'outDegree':owner.out_degree,'topologicalOrder':owner.topological_order,'sameLayers':layers is graph.layers,'sameLayerless':layerless is graph.layerless_nodes,'layerlessCount':len(graph.layerless_nodes),'sameInTopoMap':owner.in_topological is initial_map,'monitor':{'name':monitor.task_name,'running':monitor.is_running(),'closed':monitor._closed},'configurationByOrdinal':[[p.name for p in sorted(slot,key=lambda p:p.ordinal)]for slot in cfg.list]})
class ObservedProperties(CanonicalPropertyMap):
 def get(self,key,default=None):self.reads+=1;return super().get(key,default)
old_arrays=[owner.node_mark,owner.edge_mark,owner.in_degree,owner.out_degree,owner.topological_order];empty=LGraph(None,None,None,properties=ObservedProperties());empty.properties.reads=0;monitor=BasicProgressMonitor(False,False);owner.process(empty,monitor)
actual={'comparators':comparators,'cases':cases,'empty':{'optionReads':empty.properties.reads,'oldArraysRetained':all(a is b for a,b in zip(old_arrays,[owner.node_mark,owner.edge_mark,owner.in_degree,owner.out_degree,owner.topological_order])),'sameInTopoMap':owner.in_topological is initial_map,'layerCount':len(empty.layers),'monitor':{'name':monitor.task_name,'running':monitor.is_running(),'closed':monitor._closed},'sameClassConfiguration':CoffmanGrahamLayerer().get_layout_processor_configuration(empty)is owner.get_layout_processor_configuration(empty)}}
expected=copy.deepcopy(raw['value']);raw_configurations=[case.pop('rawConfiguration')for case in expected['cases']];comparison=diff(expected,actual);assert hashes()==before
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':expected,'sourceRawConfigurations':raw_configurations,'rawSetOrderEquivalenceClaimed':False,'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':sha(original),'scope':'First actual candidate complete CoffmanGrahamLayerer on two saved8nodeDAG widths2/0 plus sameownerempty; seven separately instrumented actual boxed comparator probes. No public whole caller, old groups or full validation.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
