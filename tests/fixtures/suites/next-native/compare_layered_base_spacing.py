"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT: fixed real Layered spacing builder."""
import hashlib
import json
from pathlib import Path
import sys

def main():
    source,request,original_path,out=map(Path,sys.argv[1:5]);source=source.resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={p.resolve():sha(p)for p in source.rglob('*.py')};sys.path.insert(0,str(source))
    from pyelk.algorithms.layered.graph import LGraph
    from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
    from pyelk.algorithms.layered.base_spacing import LayeredSpacingsBuilder
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'));from layout_checks import diff
    original=json.loads(original_path.read_bytes())
    assert original['requestSha256']==sha(request)and original['probeSha256']==sha(request.with_name('layered-base-spacing-probe.cjs'))
    assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    cases=[]
    for spec in json.loads(request.read_bytes())['cases']:
        writes=[]
        class Stored(CanonicalPropertyMap):
            def __setitem__(self,key,value):writes.append(key);return super().__setitem__(key,value)
        graph=LGraph(None,None,None,properties=Stored());builder=LayeredSpacingsBuilder(spec['base'])
        if 'existingEdgeEdge'in spec:graph.properties['org.eclipse.elk.spacing.edgeEdge']=spec['existingEdgeEdge']
        writes.clear();keys=list(builder.factor_map)
        def snapshot():return [dict(id=key,present=key in graph.properties,value=graph.properties.get(key))for key in keys]
        factors=[dict(id=key,factor=value,default=builder.defaults[key])for key,value in builder.factor_map.items()]
        accepts=builder.filters[0](graph,keys[0]);initial=snapshot();filters_before=len(builder.filters)
        builder.apply(graph);first=snapshot();filters_first=len(builder.filters)
        builder.apply(graph);second=snapshot();filters_second=len(builder.filters)
        assert builder.filters[1]is builder.filters[2]
        cases.append(dict(id=spec['id'],factors=factors,acceptsProperty=accepts,before=initial,first=first,second=second,writes=writes,filtersBefore=filters_before,filtersAfterFirst=filters_first,filtersAfterSecond=filters_second,layoutExecuted=False))
    actual=dict(cases=cases,layoutExecuted=False);comparison=diff(original['observation'],actual,tolerant=False)
    imported={Path(m.__file__).resolve()for name,m in tuple(sys.modules.items())if(name=='pyelk'or name.startswith('pyelk.'))and getattr(m,'__file__',None)}
    unchanged=all(p in before and sha(p)==before[p]for p in imported)
    report=dict(passed=unchanged and comparison['passed'],comparison=comparison,actual=actual,expected=original['observation'],sourceTreeUnchanged=unchanged,importedSourcesSha256={p.relative_to(source).as_posix():before[p]for p in imported},requestSha256=sha(request),originalSha256=sha(original_path),checkerSha256=sha(Path(__file__)),layoutExecuted=False,fullValidation=False)
    with out.open('x',encoding='utf8')as h:json.dump(report,h,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=report['passed'],differences=len(comparison['differences']))));return 0 if report['passed']else 1

if __name__=='__main__':raise SystemExit(main())
