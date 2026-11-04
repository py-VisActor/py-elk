"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: only canonical enum fallback delta."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve(); sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import (LGraph, LNode, LPort, LEdge, Layer,
        set_layer, set_port_owner, set_source, set_target)
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.model_order_nodes import ModelOrderNodeComparator
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s, original = json.loads(request.read_bytes()), json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('node-order-enum-probe.cjs'))
    graph = LGraph(None, None, None); prior, upper, lower = LNode(graph), LNode(graph), LNode(graph)
    l0, l1 = Layer(graph, id=0), Layer(graph, id=1); graph.layers.extend([l0,l1])
    set_layer(prior,l0);set_layer(upper,l1);set_layer(lower,l1)
    p,q,edge=LPort(),LPort(),LEdge();set_port_owner(p,prior);set_port_owner(q,upper)
    set_side(p,'EAST');set_side(q,'WEST');set_source(edge,p);set_target(edge,q)
    edge.properties['MODEL_ORDER']=s['edgeModelOrder']
    results=[dict(strategy=name,value=ModelOrderNodeComparator(graph,[prior],'PREFER_EDGES',name).compare(upper,lower)) for name in s['strategies']]
    # The source default is separately sealed, not read from a fabricated native graph property.
    actual=dict(results=results,layoutExecuted=False)
    expected={key:value for key,value in original['observation'].items() if key!='sourceDefault'}
    comparison=diff(expected,actual,tolerant=False)
    imported={Path(m.__file__).resolve() for name,m in tuple(sys.modules.items()) if (name=='pyelk' or name.startswith('pyelk.')) and getattr(m,'__file__',None)}
    unchanged=all(p in before and sha(p)==before[p] for p in imported)
    result=dict(passed=unchanged and comparison['passed'],actual=actual,expected=expected,comparison=comparison,
        sourceDefaultObservation=original['observation']['sourceDefault'],sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix():before[p] for p in imported},
        inputsSha256={str(p):sha(p) for p in (Path(__file__),request,oracle)},layoutExecuted=False,fullValidation=False,
        scope='Only corrected canonical DUMMY_NODE_OVER/UNDER keys in one-predecessor connected-edge fallback; source default separately observed, no native runtime owner-default claim')
    with report.open('x',encoding='utf8')as handle:json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],differences=len(comparison['differences']))));return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
