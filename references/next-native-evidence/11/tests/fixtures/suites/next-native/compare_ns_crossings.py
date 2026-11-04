"""PRIVATE_SRC REQUEST ORACLE REPORT: new real NS position/weighted scores.

Init/add observers delegate unchanged code and retain their actual trace. Node
types, graph/adjacency and layout units are supplied intermediate state.
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source,request,oracle,report=map(Path,sys.argv[1:5]);source=source.resolve()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={p.resolve():sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0,str(source))
    from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,set_layer,set_port_owner,set_source,set_target
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.crossing_counter import BinaryIndexedTree,CrossingsCounter
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
    from layout_checks import diff
    original=json.loads(oracle.read_bytes());assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256']==sha(request)
    assert original['probeSha256']==sha(request.with_name('ns-crossings-probe.cjs'))
    rows=[]
    for case,expected in zip(json.loads(request.read_bytes())['cases'],original['results'],strict=True):
        assert case['id']==expected['id'];graph=LGraph(None,None,None);layer=Layer(graph);graph.layers.append(layer);nodes={};ports={};names={}
        for spec in case['nodes']:
            node=LNode(graph,type=spec['type']);nodes[spec['id']]=node
            for name,side in spec['ports']:
                port=LPort(id=len(ports));set_port_owner(port,node);set_side(port,side);ports[name]=port;names[port]=name
        order=[]
        for i,name in enumerate(case['order']):node=nodes[name];node.id=i;set_layer(node,layer);order.append(node)
        for spec in case['nodes']:
            if 'unit'in spec:nodes[spec['id']].properties['IN_LAYER_LAYOUT_UNIT']=nodes[spec['unit']]
        for name,node in case['dummies'].items():ports[name].properties['PORT_DUMMY']=nodes[node]
        for name,port in case['origins'].items():ports[name].properties['ORIGIN']=ports[port]
        for a,b in case['edges']:
            edge=LEdge();set_source(edge,ports[a]);set_target(edge,ports[b])
        positions={port:-1 for port in ports.values()};counter=CrossingsCounter(positions);ends=counter.ends;constructed=[];adds=[]
        old_init=counter._init_positions_for_north_south;old_add=BinaryIndexedTree.add
        def init_observer(nodes):
            result=old_init(nodes);constructed.extend(names[p] for p in result);return result
        def add_observer(tree,index):adds.append(index);return old_add(tree,index)
        counter._init_positions_for_north_south=init_observer;BinaryIndexedTree.add=add_observer
        try:count=counter.count_north_south_port_crossings_in_layer(order)
        finally:BinaryIndexedTree.add=old_add;counter._init_positions_for_north_south=old_init
        tree=counter.index_tree
        value=dict(count=count,constructedPortOrder=constructed,positions=[dict(id=name,value=positions[p]) for name,p in ports.items()],
                   queuedEndpointAddOrder=adds,endsIdentityPreserved=counter.ends is ends,endsEmpty=not counter.ends,
                   tree=dict(size=tree.size,sums=list(tree.binary_sums),multiplicities=list(tree.nums_per_index)),
                   cacheFlags=[dict(id=name,cached=node.port_sides_cached) for name,node in nodes.items()],observerOnlyWrappers=True,layoutExecuted=False)
        rows.append(dict(id=case['id'],actual=value,expected=expected['value'],differences=diff(expected['value'],value)['differences']))
    imported={Path(m.__file__).resolve() for name,m in tuple(sys.modules.items()) if (name=='pyelk' or name.startswith('pyelk.')) and getattr(m,'__file__',None)}
    unchanged=all(sha(p)==before[p] for p in imported)
    result=dict(passed=unchanged and all(not row['differences'] for row in rows),rows=rows,sourceTreeUnchanged=unchanged,
                importedSourcesSha256={p.relative_to(source).as_posix():before[p] for p in imported},
                inputsSha256={str(p):sha(p) for p in (Path(__file__),request,oracle)},layoutExecuted=False,
                scope='Actual NS position stack/weighted counter including duplicate LONG slots and zero-degree queue endpoints; no complete sweep/layout')
    with report.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],cases=len(rows))))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
