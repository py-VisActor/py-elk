"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; import only, no layout scheduling."""
import copy
import hashlib
import json
from pathlib import Path
import sys

def main():
    source,request,oracle,report=map(Path,sys.argv[1:5]);source=source.resolve()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={p.resolve():sha(p) for p in source.rglob('*.py')};sys.path.insert(0,str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.execution.metadata_service import NativeMetadataService
    from pyelk.algorithms.layered.native_import_hierarchical import HierarchicalElkGraphImporter
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'));from layout_checks import diff
    original=json.loads(oracle.read_bytes())
    assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256']==sha(request) and original['probeSha256']==sha(request.with_name('hierarchical-import-probe.cjs'))
    cases=[];preserved=True
    for spec in json.loads(request.read_bytes())['cases']:
        saved=copy.deepcopy(spec['graph']);state=JsonLayoutSession(spec['graph'],metadata=NativeMetadataService(['layered']))
        raw_nodes=[];raw_edges=[]
        def visit(n):
            raw_nodes.append(n);raw_edges.extend(state.contained_edges(n))
            for child in n.get('children',[]):visit(child)
        visit(state.graph)
        events=[];native_edges=[]
        class Importer(HierarchicalElkGraphImporter):
            def create_lgraph(self,n):events.append('graph:'+n['id']);return super().create_lgraph(n)
            def transform_node(self,n,g):events.append('node:'+n['id']);return super().transform_node(n,g)
            def check_edge_validity(self,e):events.append('check:'+e['id']);return super().check_edge_validity(e)
            def transform_edge(self,e,p,g):
                events.append('edge:'+e['id']);v=super().transform_edge(e,p,g);native_edges.append((e,v,g));return v
        importer=Importer(state);graph=importer.import_graph(state.graph)
        def graph_id(g):return g.properties['ORIGIN']['id'] if g is not None else None
        def order(n):return state.property_snapshot(n).get_native('modelOrder')
        nodes=[]
        for n in raw_nodes[1:]:
            v=importer.lookup(n);nested=getattr(v,'nested_graph',None) if v is not None else None
            nodes.append(dict(id=n['id'],imported=v is not None,graph=graph_id(v.graph) if v is not None else None,nested=graph_id(nested),nestedDirection=nested.properties['DIRECTION'] if nested is not None else None,parentIdentity=nested is not None and nested.parent_node is v))
        cases.append(dict(id=spec['id'],events=events,rawOrders=[dict(id=n['id'],order=order(n))for n in raw_nodes+raw_edges],maxOrder=graph.properties['MAX_MODEL_ORDER_NODES'],groups=graph.properties['CB_NUM_MODEL_ORDER_GROUPS'],nodes=nodes,edges=[dict(id=e['id'],graph=graph_id(g),coordinateOrigin=graph_id(v.properties.get('COORDINATE_SYSTEM_ORIGIN')),coordinatePresent='COORDINATE_SYSTEM_ORIGIN'in v.properties)for e,v,g in native_edges],layoutExecuted=False))
        preserved=preserved and diff(saved,spec['graph'],tolerant=False)['passed']
    actual=dict(cases=cases,layoutExecuted=False);comparison=diff(original['observation'],actual,tolerant=False)
    imported={Path(m.__file__).resolve()for n,m in tuple(sys.modules.items())if(n=='pyelk'or n.startswith('pyelk.'))and getattr(m,'__file__',None)}
    unchanged=all(p in before and sha(p)==before[p]for p in imported)
    result=dict(passed=unchanged and preserved and comparison['passed'],actual=actual,expected=original['observation'],comparison=comparison,sourceTreeUnchanged=unchanged,originalInputPreserved=preserved,importedSourcesSha256={p.relative_to(source).as_posix():before[p]for p in imported},inputsSha256={str(p):sha(p)for p in(Path(__file__),request,oracle)},layoutExecuted=False,fullValidation=False)
    with report.open('x',encoding='utf8')as h:json.dump(result,h,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],differences=len(comparison['differences']))));return 0 if result['passed']else 1

if __name__=='__main__':raise SystemExit(main())
