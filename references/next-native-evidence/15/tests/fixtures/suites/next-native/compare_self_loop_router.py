from pathlib import Path
import sys,json,hashlib
from types import SimpleNamespace
source,request,original,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from layout_checks import diff
from pyelk.algorithms.layered.self_loops_general import self_loop_preprocessor,self_loop_port_restorer,self_loop_router
from pyelk.algorithms.layered.spline_math import NubSpline
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,Insets,set_source,set_target,set_layer
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.ports import set_side
from pyelk.algorithms.layered.phases import JavaRandom
from pyelk.execution.diagnostics import BasicProgressMonitor
from pyelk.algorithms.layered.native_adapters import _has_property
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
vec=lambda p:[p.x,p.y]
before=hashes();request=json.loads(request.read_text(encoding='utf8'));results=[]
for mode in request['routes']:
 g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();n=LNode(g);n.properties=CanonicalPropertyMap();g.layerless_nodes.append(n);n.size=Vec2(120.5,80.25);n.margin=Insets(3,4,5,6);margin=n.margin;edges=[];ports=[]
 g.properties['DIRECTION']='RIGHT';g.properties['EDGE_ROUTING']=mode;g.properties['RANDOM']=JavaRandom(7);n.properties['PORT_CONSTRAINTS']='FIXED_ORDER';n.properties['ORIGINAL_PORT_CONSTRAINTS']='FIXED_ORDER'
 for i,side in enumerate(request['sides']):
  p=LPort(n);p.labels=[];p.properties=CanonicalPropertyMap();n.ports.append(p);set_side(p,side);p.id=i;p.pos=Vec2(120.5 if side=='EAST'else 0 if side=='WEST'else 10+(i%5)*20,0 if side=='NORTH'else 80.25 if side=='SOUTH'else 5+(i%5)*14);p.anchor=Vec2(.5,.25);ports.append(p)
 for i,group in enumerate(request['groups']):
  for j in range(len(group)-1):
   e=LEdge(id=len(edges));e.properties=CanonicalPropertyMap();e.labels=[];edges.append(e);set_source(e,ports[group[j]]);set_target(e,ports[group[j+1]]);e.bend_points.append(Vec2(999,-777))
   if j==0:
    label=SimpleNamespace(pos=Vec2(),size=Vec2(12+i*3,5+i),properties=CanonicalPropertyMap());label.properties['EDGE_LABELS_INLINE']=i==2;e.labels.append(label)
 refs=[e.bend_points for e in edges];self_loop_preprocessor(g);layer=Layer(g);g.layers.append(layer);set_layer(n,layer);g.layerless_nodes.clear();self_loop_port_restorer(g)
 monitor=BasicProgressMonitor(False,False);self_loop_router(g,monitor=monitor);holder=n.properties['SELF_LOOP_HOLDER']
 results.append({'mode':mode,'margin':[n.margin.top,n.margin.right,n.margin.bottom,n.margin.left],'sameMargin':n.margin is margin,'sameBendChains':[e.bend_points is refs[i]for i,e in enumerate(edges)],'edges':[{'id':e.id,'bends':[vec(p)for p in e.bend_points],'labels':[{'position':vec(l.pos),'inlinePresent':_has_property(l,'EDGE_LABELS_INLINE')}for l in e.labels]}for e in edges],'loops':[{'kind':loop.self_loop_type,'routing':loop.routing_slot,'labels':None if loop.sl_labels is None else{'side':loop.sl_labels.side,'alignment':loop.sl_labels.alignment,'position':vec(loop.sl_labels.position)}}for loop in holder.sl_hyper_loops],'slotCount':holder.routing_slot_count,'monitorFinished':not monitor.is_running()})
actual={'routes':results};expected={'routes':json.loads(original.read_text(encoding='utf8'))['value']['routes']}
# Original01 probe negated the isRunning method object, not its call. Preserve
# its raw false values and isolate that observer defect from geometry.
rawcomparison=diff(expected,actual);geometry_expected=json.loads(json.dumps(expected));geometry_actual=json.loads(json.dumps(actual))
for value in[geometry_expected,geometry_actual]:
 for route in value['routes']:del route['monitorFinished']
comparison=diff(geometry_expected,geometry_actual);assert hashes()==before
out.write_text(json.dumps({'passed':comparison['passed'],'geometryStrict':comparison['passed'],'rawStrict':rawcomparison['passed'],'comparison':comparison,'rawComparison':rawcomparison,'rawMonitorObserverDefect':'Original01 !monitor.isRunning negated method object; raw false retained, not source completion evidence. Excluded only this field from geometry/object parity. Native records actual monitor.is_running() after execution.','actual':actual,'expected':expected,'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'Only new prepared true SelfLoopRouter fourth phase 3modes/8edges; prior successful NubSpline primitive group not re-executed. Actual margins/bends/slotcounts/labelaxis/objectidentity/mutablechains/knots/controlpoints/refretention. No full layout/API/backend/previous group rerun.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences']),'rawDifferences':len(rawcomparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
