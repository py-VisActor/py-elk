from pathlib import Path
import sys,json,hashlib,copy
source,request,original,out,probe=map(Path,sys.argv[1:6]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();raw=json.loads(original.read_text(encoding='utf8'))
assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'and raw['requestSha256']==sha(request)and raw['probeSha256']==sha(probe)
sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from pyelk.algorithms.layered.simple_placement import SimpleNodePlacer
from pyelk.algorithms.layered.graph import LGraph,LNode,Layer,Vec2,Insets,set_layer
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.spacings import Spacings,_PROPERTIES
from pyelk.execution.diagnostics import BasicProgressMonitor
from layout_checks import diff
def hashes():return {p.relative_to(source).as_posix():sha(p)for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();owner=SimpleNodePlacer();result=[];initial_configuration=None
for case in json.loads(request.read_text(encoding='utf8'))['cases']:
 graph=LGraph(None,None,None,properties=CanonicalPropertyMap());graph.size=Vec2(321,654);graph.properties['GRAPH_PROPERTIES']=set(case['flags']);nodes=[]
 if 'spacings'in case:
  for key,value in case['spacings'].items():graph.properties[_PROPERTIES[key].native_key]=value
  graph.properties['SPACINGS']=Spacings(graph)
 for item in case['layers']:
  layer=Layer(graph);graph.layers.append(layer);layer.size=Vec2(item['width'],789)
  for value in item['nodes']:
   node=LNode(graph,properties=CanonicalPropertyMap());node.type=value['type'];node.pos=Vec2(value['x'],-100);node.size=Vec2(value['width'],value['height']);node.margin=Insets(*value['margin']);set_layer(node,layer)
   if 'individual'in value:node.properties['SPACING_INDIVIDUAL']={_PROPERTIES[key].canonical_id:v for key,v in value['individual'].items()}
   nodes.append((value['name'],node))
 cfg=owner.get_layout_processor_configuration(graph)
 if cfg is not None:initial_configuration=cfg
 monitor=BasicProgressMonitor(False,False);owner.process(graph,monitor)
 result.append({'name':case['name'],'graphSize':[graph.size.x,graph.size.y],'layerSizes':[[layer.size.x,layer.size.y]for layer in graph.layers],'nodes':[{'name':name,'position':[node.pos.x,node.pos.y],'size':[node.size.x,node.size.y]}for name,node in nodes],'spacingHas':'SPACINGS'in graph.properties,'monitor':{'name':monitor.task_name,'running':monitor.is_running(),'closed':monitor._closed},'configurationByOrdinal':None if cfg is None else[[p.name for p in sorted(slot,key=lambda p:p.ordinal)]for slot in cfg.list],'sameConfiguration':None if cfg is None else SimpleNodePlacer().get_layout_processor_configuration(graph)is initial_configuration})
expected=copy.deepcopy(raw['value']);raw_configs=[item.pop('rawConfiguration')for item in expected];comparison=diff(expected,result);assert hashes()==before
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':result,'expected':expected,'sourceRawConfigurations':raw_configs,'rawSetOrderEquivalenceClaimed':False,'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':sha(original),'scope':'First new actual SimpleNodePlacer two prepared inputs: real typed/individual Spacings+mixed node types/asymmetric margins/twopass center, then missing nullable Spacings with singleton/empty. Actual sizes/XY/monitor/nohas/config checked, no old groups/full executed.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
