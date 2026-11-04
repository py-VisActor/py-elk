from pathlib import Path
import sys,json,hashlib,copy
source,request,original,out,probe=map(Path,sys.argv[1:6])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
raw=json.loads(original.read_text(encoding='utf8'))
assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert raw['requestSha256']==sha(request) and raw['probeSha256']==sha(probe)
sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from pyelk.algorithms.layered.polyline_general import PolylineEdgeRouter
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,Insets,set_source,set_target,set_layer
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.ports import set_side
from pyelk.algorithms.layered.graph_info import get_graph_properties
from pyelk.execution.diagnostics import BasicProgressMonitor
from layout_checks import diff

def hashes():return {p.relative_to(source).as_posix():sha(p)for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before_hashes=hashes();router=PolylineEdgeRouter();initial_set=router.created_junction_points;results=[]
xy=lambda point:[point.x,point.y]
for case in json.loads(request.read_text(encoding='utf8'))['cases']:
 g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();nodes={};ports={};edges=[]
 if 'zone'in case:g.properties['EDGE_ROUTING_POLYLINE_SLOPED_EDGE_ZONE_WIDTH']=case['zone']
 get_graph_properties(g).update(case['flags'])
 for item_layer in case['layers']:
  layer=Layer(g);g.layers.append(layer);layer.size.x=item_layer['width']
  for item in item_layer['nodes']:
   node=LNode(g);node.properties=CanonicalPropertyMap();node.type=item.get('type','NORMAL');node.pos.y=item['y'];node.size=Vec2(item['width'],10);node.margin=Insets(1,2.25,1.5,1.5);set_layer(node,layer);nodes[item['name']]=node
   if 'externalSide'in item:node.properties['EXT_PORT_SIDE']=item['externalSide']
   for side in ['WEST','EAST']:
    port=LPort(node);port.properties=CanonicalPropertyMap();node.ports.append(port);set_side(port,side);port.pos=Vec2(0 if side=='WEST'else item['width'],5);ports[item['name']+':'+side]=port
 for item_layer in case['layers']:
  for item in item_layer['nodes']:
   if 'origin'in item:
    for side in ['WEST','EAST']:ports[item['name']+':'+side].properties['ORIGIN']=ports[item['origin']]
 for index,item in enumerate(case['edges']):
  edge=LEdge(id=index);edge.properties=CanonicalPropertyMap();set_source(edge,ports[item['source']]);set_target(edge,ports[item['target']]);edge.bend_points.extend(Vec2(*v)for v in item.get('bends',[]))
  if 'junctions'in item:edge.properties['JUNCTION_POINTS']=[Vec2(*v)for v in item['junctions']]
  edges.append(edge)
 cfg=router.get_layout_processor_configuration(g);configuration=[[p.name for p in sorted(slot,key=lambda p:p.ordinal)]for slot in cfg.list]
 before=[{'bends':list(map(xy,e.bend_points)),'junctionPresent':'JUNCTION_POINTS'in e.properties}for e in edges]
 monitor=BasicProgressMonitor(False,False);router.process(g,monitor)
 results.append({'name':case['name'],'width':g.size.x,'nodes':[{'name':name,'position':xy(node.pos)}for name,node in nodes.items()],'before':before,'edges':[{'id':e.id,'bends':list(map(xy,e.bend_points)),'junctionPresent':'JUNCTION_POINTS'in e.properties,'junctions':list(map(xy,e.properties['JUNCTION_POINTS']))if'JUNCTION_POINTS'in e.properties else None}for e in edges],'configurationByOrdinal':configuration,'monitorRunning':monitor.is_running(),'monitorClosed':monitor._closed,'samePersistentSet':router.created_junction_points is initial_set,'junctionSetSize':len(initial_set)})
class ObservedProperties(CanonicalPropertyMap):
 def get(self,key,default=None):self.reads+=1;return super().get(key,default)
empty=LGraph(None,None,None);empty.size.x=123;empty.properties=ObservedProperties();empty.properties.reads=0;monitor=BasicProgressMonitor(False,False);router.process(empty,monitor)
actual={'cases':results,'empty':{'width':empty.size.x,'optionReads':empty.properties.reads,'running':monitor.is_running(),'closed':monitor._closed,'samePersistentSet':router.created_junction_points is initial_set,'junctionSetSize':len(initial_set)}}
expected=copy.deepcopy(raw['value']);raw_configurations=[case.pop('configurationRaw')for case in expected['cases']]
comparison=diff(expected,actual);assert hashes()==before_hashes
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':expected,'sourceRawConfigurations':raw_configurations,'sourceRawConfigurationOrderCertified':False,'configurationScope':'Actual assembler ordinal consumer projection checked separately; no raw HashSet/native set iteration parity claim. All original raw configuration bytes retained.','sourceFilesSha256':before_hashes,'sourceTreeUnchanged':True,'originalSha256':sha(original),'scope':'Only first new actual PolylineEdgeRouter.process2 prepared graphs plus empty3optionReads/successcleanup. Same-layer E/W/long dummy, NS actual origin port, exact value-junction suppression, old bends/chain, external/empty layer. No public whole pipeline or old successful groups executed.'},indent=2)+'\n',encoding='utf8')
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
