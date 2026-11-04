"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT: four real stages, supplied placement."""
import hashlib,json
from pathlib import Path
import sys
def main():
 source,request,oracle,out=map(Path,sys.argv[1:5]);source=source.resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={p.resolve():sha(p)for p in source.rglob('*.py')};sys.path.insert(0,str(source))
 from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,set_layer,set_port_owner,set_source,set_target
 from pyelk.algorithms.layered.native_import import LLabel
 from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
 from pyelk.algorithms.layered.ports import set_side
 from pyelk.algorithms.layered.phases import JavaRandom
 from pyelk.execution.diagnostics import BasicProgressMonitor
 from pyelk.algorithms.layered.hierarchical_port_constraints import hierarchical_port_constraints_processor
 from pyelk.algorithms.layered.hierarchical_port_size import hierarchical_port_dummy_size_processor
 from pyelk.algorithms.layered.hierarchical_port_position import hierarchical_port_position_processor
 from pyelk.algorithms.layered import hierarchical_port_ortho as ortho
 sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'));from layout_checks import diff
 original=json.loads(oracle.read_bytes());assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86';assert original['requestSha256']==sha(request)and original['probeSha256']==sha(request.with_name('hierarchy-port-phases-probe.cjs'))
 cases=[]
 for spec in json.loads(request.read_bytes())['cases']:
  names={};edge_names={};g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();layer=Layer(g);g.layers.append(layer);g.size=Vec2(100,80);g.offset=Vec2(3,5);g.padding.top,g.padding.right,g.padding.bottom,g.padding.left=2,4,6,8
  g.properties['PORT_CONSTRAINTS']=spec['constraints'];g.properties['NODE_SIZE_CONSTRAINTS']={'PORT_LABELS'};g.properties['PORT_LABELS_PLACEMENT']={'INSIDE'}
  for key,value in [('SPACING_EDGE_EDGE_BETWEEN_LAYERS',5),('SPACING_PORT_PORT',10),('SPACING_NODE_NODE',7),('SPACING_EDGE_EDGE',3)]:g.properties[key]=value
  g.properties['RANDOM']=JavaRandom(17)
  def port(n,side):
   p=LPort(properties=CanonicalPropertyMap());p.labels=[];set_port_owner(p,n);set_side(p,side);p.pos=Vec2(1,1);return p
  def ext(name,side,ratio):
   n=LNode(g,type='EXTERNAL_PORT',properties=CanonicalPropertyMap());n.labels=[];n.size=Vec2(6,4);set_layer(n,layer);names[n]=name;n.properties['EXT_PORT_SIDE']=side;n.properties['PORT_RATIO_OR_POSITION']=ratio;n.properties['PORT_ANCHOR']=Vec2(1,1)
   p=port(n,{'WEST':'EAST','EAST':'WEST','NORTH':'SOUTH','SOUTH':'NORTH'}[side]);n.properties['ORIGIN']=p
   if name not in('E','S'):n.properties['EXT_PORT_SIZE']=Vec2(6,4)
   if side in('NORTH','SOUTH'):
    l=LLabel(text=name+'-port');l.size=Vec2(10,4);l.properties=CanonicalPropertyMap();p.labels.append(l)
    for key,value in [('SPACING_LABEL_PORT_HORIZONTAL',2),('SPACING_LABEL_PORT_VERTICAL',3),('SPACING_LABEL_LABEL',2)]:n.properties[key]=value
   return n
  def normal(name,x,y):
   n=LNode(g,type='NORMAL',properties=CanonicalPropertyMap());n.labels=[];n.pos=Vec2(x,y);n.size=Vec2(10,8);names[n]=name;set_layer(n,layer);port(n,'WEST');port(n,'EAST');return n
  W=ext('W','WEST',.1);N0=ext('N0','NORTH',.25);N1=ext('N1','NORTH',.75);n0=normal('n0',30,20);n1=normal('n1',60,40);S=ext('S','SOUTH',.5);E=ext('E','EAST',1.2);original_nodes=[W,N0,N1,n0,n1,S,E];edges=[]
  def edge(a,ap,b,bp):
   e=LEdge(properties=CanonicalPropertyMap());e.labels=[];set_source(e,a.ports[ap]);set_target(e,b.ports[bp]);edge_names[e]='e'+str(len(edges));edges.append(e);e.bend_points.append(Vec2(11,13));return e
  edge(N0,0,n0,0);edge(N1,0,n1,0);edge(n0,1,S,0);edge(n1,1,S,0);edge(n0,1,n1,0);edge(W,0,n0,0);edge(n1,1,E,0);edge(W,0,E,0)
  def name(n):return None if n is None else names[n]if n in names else'replacement:'+names[n.properties['EXT_PORT_REPLACED_DUMMY']]
  def point(v):return[v.x,v.y]
  def layers():return[[name(n)for n in l.nodes]for l in g.layers]
  hierarchical_port_constraints_processor(g,monitor=BasicProgressMonitor());after_constraints=dict(layers=layers(),originalLayers=[g.layers.index(n.layer)if n.layer is not None else-1 for n in original_nodes],replaced=[name(n)for n in g.properties['EXT_PORT_REPLACED_DUMMIES']],successors=[name(n)for n in W.properties['IN_LAYER_SUCCESSOR_CONSTRAINTS']])
  set_layer(W,g.layers[0]);set_layer(E,g.layers[-1])
  for l in g.layers:
   for n in l.nodes:
    if 'EXT_PORT_REPLACED_DUMMY'in n.properties:
     old=n.properties['EXT_PORT_REPLACED_DUMMY'];n.pos=Vec2(*( (30,0)if old is N0 else(32,0)if old is N1 else(40,70)))
  hierarchical_port_dummy_size_processor(g,monitor=BasicProgressMonitor());after_size=[dict(name=name(n),width=n.size.x,portX=[p.pos.x for p in n.ports])for l in g.layers for n in l.nodes]
  hierarchical_port_position_processor(g,monitor=BasicProgressMonitor());after_position=[dict(name=name(n),pos=point(n.pos))for n in original_nodes]
  router=ortho.HierarchicalPortOrthogonalEdgeRouter();routes=[];saved=ortho.routing_generator
  def observe(direction,spacing):
   generator=saved(direction,spacing);route=generator.route
   def delegated(*args):
    slots=route(*args);routes.append(dict(direction=generator.source_side,slots=slots));return slots
   generator.route=delegated;return generator
  ortho.routing_generator=observe
  try:router.process(g,monitor=BasicProgressMonitor())
  finally:ortho.routing_generator=saved
  after_ortho=dict(layers=layers(),size=point(g.size),offset=point(g.offset),northHeight=router.northern_ext_port_edge_routing_height,routes=routes,nodes=[dict(name=name(n),pos=point(n.pos),margin=[n.margin.top,n.margin.right,n.margin.bottom,n.margin.left],ports=[dict(side=p.side,pos=point(p.pos),labels=[dict(text=l.text,pos=point(l.pos))for l in p.labels])for p in n.ports])for n in original_nodes],edges=[dict(id=edge_names[e],source=name(e.source.owner),target=name(e.target.owner),bends=[point(p)for p in e.bend_points])for e in edges],defaultSizePresence=['EXT_PORT_SIZE'in E.properties,'EXT_PORT_SIZE'in S.properties],defaultSizeDistinct=E.properties['EXT_PORT_SIZE']is not S.properties['EXT_PORT_SIZE'])
  cases.append(dict(id=spec['id'],afterConstraints=after_constraints,afterSize=after_size,afterPosition=after_position,afterOrtho=after_ortho,geometrySuppliedBetweenPhases=True,layoutExecuted=False))
 actual=dict(cases=cases,geometrySuppliedBetweenPhases=True,layoutExecuted=False);comparison=diff(original['observation'],actual,tolerant=False);imported={Path(m.__file__).resolve()for n,m in tuple(sys.modules.items())if(n=='pyelk'or n.startswith('pyelk.'))and getattr(m,'__file__',None)};unchanged=all(p in before and sha(p)==before[p]for p in imported)
 report=dict(passed=unchanged and comparison['passed'],comparison=comparison,actual=actual,expected=original['observation'],sourceTreeUnchanged=unchanged,importedSourcesSha256={p.relative_to(source).as_posix():before[p]for p in imported},geometrySuppliedBetweenPhases=True,layoutExecuted=False,fullValidation=False)
 with out.open('x',encoding='utf8')as f:json.dump(report,f,indent=2,allow_nan=False)
 print(json.dumps(dict(passed=report['passed'],differences=len(comparison['differences']))));return 0 if report['passed']else 1
if __name__=='__main__':raise SystemExit(main())
