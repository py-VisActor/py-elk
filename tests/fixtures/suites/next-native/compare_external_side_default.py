"""PRIVATE_SRC ORIGINAL NEW_REPORT: only new actual default-side CC callers."""
import hashlib,json,math,sys
from pathlib import Path
source,original_path,out=map(Path,sys.argv[1:4]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.connected_compactor import ComponentsCompactor,InternalExternalExtension
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,Vec2,set_port_owner
from pyelk.algorithms.layered.native_adapters import _read_property,_has_property
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap,canonical_property_key
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads(original_path.read_bytes());assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['probeSha256']==sha(Path(__file__).with_name('external-side-default-probe.cjs'))
def number(v):return '-0' if v==0 and math.copysign(1,v)<0 else v
def point(v):return [number(v.x),number(v.y)]
actual=[]
for physical_null in(False,True):
    graph=LGraph(None,None,None);graph.properties=CanonicalPropertyMap();node=LNode(graph,type='EXTERNAL_PORT',properties=CanonicalPropertyMap());node.pos=Vec2(5.0,7.0);graph.layerless_nodes.append(node)
    port=LPort(properties=CanonicalPropertyMap());set_port_owner(port,node)
    if physical_null:node.properties._values[canonical_property_key('EXT_PORT_SIDE')]=None
    before=_has_property(node,'EXT_PORT_SIDE');original_pos=node.pos;owner=ComponentsCompactor();owner.compact([graph],3)
    edge=port.outgoing_edges[0];extension=InternalExternalExtension(edge)
    actual.append({'physicalNull':physical_null,'before':before,'after':_has_property(node,'EXT_PORT_SIDE'),'side':_read_property(node,'EXT_PORT_SIDE'),'extensionSide':extension.external_port_side,'extensionDirection':extension.get_direction(),'representorNullish':extension.get_representor() is None,
        'size':point(owner.compacted_graph_size),'offset':point(owner.yet_another_offset),'nodes':[{'type':n.type,'pos':point(n.pos),'size':point(n.size)}for n in graph.layerless_nodes],'bends':[point(v)for v in edge.bend_points],'originalPosSame':node.pos is original_pos,'graphConnectionsAbsent':not _has_property(graph,'EXT_PORT_CONNECTIONS')})
comparison=diff(original['value'],actual,tolerant=False)
module=source/'pyelk/algorithms/layered/connected_compactor.py'
with out.open('x',encoding='utf8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceFilesSha256':{'pyelk/algorithms/layered/connected_compactor.py':sha(module)},'originalSha256':sha(original_path),'checkerSha256':sha(Path(__file__)),
    'scope':'Only missing/physical-null EXT_PORT_SIDE in constructor/dummy/clamp paths through two new outer-only real CC objects. No old successes replayed.','layoutExecuted':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
