"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; actual outer import without provider math."""
import hashlib
import json
from pathlib import Path
import sys

def main():
    source,request,oracle,report=map(Path,sys.argv[1:5]);source=source.resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={p.resolve():sha(p)for p in source.rglob('*.py')};sys.path.insert(0,str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.execution.node_micro import _PropertyReader
    from pyelk.execution.metadata_service import NativeMetadataService
    from pyelk.algorithms.layered.native_import_full import FullElkGraphImporter
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'));from layout_checks import diff
    original=json.loads(oracle.read_bytes());assert original['requestSha256']==sha(request)and original['probeSha256']==sha(request.with_name('native-outer-import-probe.cjs'))
    assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    cases=[]
    for spec in json.loads(request.read_bytes())['cases']:
        state=JsonLayoutSession(spec['graph'],metadata=NativeMetadataService(['layered']));raw=state.graph['children'][0]if spec['selectChild']else state.graph
        events=[]
        class Importer(FullElkGraphImporter):
            def create_lgraph(self,node):events.append('create');return super().create_lgraph(node)
            def check_external_ports(self,node,flags):events.append('checkExternal');return super().check_external_ports(node,flags)
            def calculate_minimum_graph_size(self,node,graph):events.append('minimum');return super().calculate_minimum_graph_size(node,graph)
            def import_flat_graph(self,node,graph):events.append('flat');return super().import_flat_graph(node,graph)
        graph=Importer(state).import_graph(raw);reader=_PropertyReader(state);minimum=graph.properties.get('NODE_SIZE_MINIMUM')
        cases.append(dict(id=spec['id'],events=events,padding=[graph.padding.top,graph.padding.right,graph.padding.bottom,graph.padding.left],direction=graph.properties['DIRECTION'],flags=sorted(graph.properties['GRAPH_PROPERTIES']),nativeConstraints=sorted(graph.properties['NODE_SIZE_CONSTRAINTS']),rawConstraints=sorted(reader.get(raw,'node','nodeSize.constraints')),minimum=[minimum.x,minimum.y]if minimum is not None else None,rawPortConstraintsPresent=reader.has(raw,'node','portConstraints'),rawPortConstraints=reader.get(raw,'node','portConstraints'),nodes=[dict(id=n.properties['ORIGIN']['id'],type=n.type,pos=[n.pos.x,n.pos.y],size=[n.size.x,n.size.y])for n in graph.layerless_nodes],rawLabels=[dict(id=l['id'],x=l['x'],y=l['y'],width=l['width'],height=l['height'])for l in raw.get('labels',[])],layoutExecuted=False))
    actual=dict(cases=cases,layoutExecuted=False);comparison=diff(original['observation'],actual,tolerant=False)
    imported={Path(m.__file__).resolve()for n,m in tuple(sys.modules.items())if(n=='pyelk'or n.startswith('pyelk.'))and getattr(m,'__file__',None)}
    unchanged=all(p in before and sha(p)==before[p]for p in imported)
    result=dict(passed=unchanged and comparison['passed'],actual=actual,expected=original['observation'],comparison=comparison,sourceTreeUnchanged=unchanged,importedSourcesSha256={p.relative_to(source).as_posix():before[p]for p in imported},inputsSha256={str(p):sha(p)for p in(Path(__file__),request,oracle)},checkerSha256=sha(Path(__file__)),layoutExecuted=False,fullValidation=False)
    with report.open('x',encoding='utf8')as h:json.dump(result,h,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],differences=len(comparison['differences']))));return 0 if result['passed']else 1

if __name__=='__main__':raise SystemExit(main())
