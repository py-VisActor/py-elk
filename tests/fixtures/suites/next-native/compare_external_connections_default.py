"""PRIVATE_SRC ORIGINAL NEW_REPORT: missing/null default plus new CT receiver."""
import hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
source,original_path,out=map(Path,sys.argv[1:4]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.graph import LGraph
from pyelk.algorithms.layered.cell_layout import Rectangle
from pyelk.algorithms.layered.native_adapters import _read_property,_has_property
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap,canonical_property_key
from pyelk.algorithms.layered.component_compaction import ComponentsToCGraphTransformer
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads(original_path.read_bytes())
assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['probeSha256']==sha(Path(__file__).with_name('external-connections-default-probe.cjs'))
graphs=[LGraph(None,None,None)for _ in range(4)]
for g in graphs:g.properties=CanonicalPropertyMap()
# The original directly puts null into the backing HashMap, bypassing the
# logical null-removing setter. Match that prepared state at the same level.
graphs[2].properties._values[canonical_property_key('EXT_PORT_CONNECTIONS')]=None
empty=set();graphs[3].properties['EXT_PORT_CONNECTIONS']=empty
before=[_has_property(g,'EXT_PORT_CONNECTIONS')for g in graphs]
a,b,c,d=[_read_property(g,'EXT_PORT_CONNECTIONS')for g in graphs]
component=SimpleNamespace(graph=graphs[0],rectilinear_convex_hull=[Rectangle(1.0,2.0,3.0,4.0)],external_extensions=[])
graph=ComponentsToCGraphTransformer(5).transform(SimpleNamespace(components=[component]));node=graph.nodes[0]
actual={'before':before,'after':[_has_property(g,'EXT_PORT_CONNECTIONS')for g in graphs],
 'sameShared':a is b and a is c and a is _read_property(graphs[0],'EXT_PORT_CONNECTIONS'),'explicitSame':d is empty,'explicitDistinct':d is not a,'allEmpty':[not v for v in(a,b,c,d)],
 'defaultCloneType':False,'lock':[node.lock.left,node.lock.right,node.lock.up,node.lock.down],'transformCounts':[len(graph.groups),len(graph.nodes)],'stillAbsentAfterTransform':not _has_property(graphs[0],'EXT_PORT_CONNECTIONS')}
comparison=diff(original['value'],actual,tolerant=False)
paths=[source/'pyelk/algorithms/layered'/name for name in('native_adapters.py','component_compaction.py','connected_compactor.py','component_groups.py')]
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceFilesSha256':{p.relative_to(source).as_posix():sha(p)for p in paths},'originalSha256':sha(original_path),'checkerSha256':sha(Path(__file__)),
 'scope':'Only newly supported EXT_PORT_CONNECTIONS missing/null/nonclone shared default and affected CT read. No old working-graph/layout groups replayed. defaultCloneType is existing native nonclone hosting policy.',
 'layoutExecuted':False,'fullValidation':False}
with out.open('x',encoding='utf8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
