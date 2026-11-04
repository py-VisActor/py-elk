"""PRIVATE_SRC REQUEST ORACLE REPORT: first real BIT/basic counter objects.

The graph, port order and scratch IDs are supplied intermediate state. Expected
scores and internal state come from the separately captured fixed worker.
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
    original=json.loads(oracle.read_bytes());spec=json.loads(request.read_bytes())
    assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256']==sha(request)
    assert original['probeSha256']==sha(request.with_name('basic-crossings-probe.cjs'))
    def tree_snapshot(tree):return dict(size=tree.size,sums=list(tree.binary_sums),multiplicities=list(tree.nums_per_index))
    rows=[]
    for case,expected in zip(spec['cases'],original['results'],strict=True):
        assert case['id']==expected['id']
        if case['operation']=='bit':
            tree=BinaryIndexedTree(case['max']);states=[];fresh=None
            for step in case['steps']:
                op=step[0];index=step[1] if len(step)>1 else None;returned=None
                if op=='add':tree.add(index)
                elif op=='remove':tree.remove_all(index)
                elif op=='rank':returned=tree.rank(index)
                else:
                    sums,nums=tree.binary_sums,tree.nums_per_index;tree.clear()
                    fresh=dict(sums=sums is not tree.binary_sums,multiplicities=nums is not tree.nums_per_index)
                states.append(dict(operation=op,index=index,returned=returned,state=tree_snapshot(tree)))
            value=dict(states=states,clearFresh=fresh,layoutExecuted=False)
        else:
            graph=LGraph(None,None,None);nodes={};ports={};names={}
            for item in spec['nodes']:
                node=LNode(graph);nodes[item['id']]=node
                for name,side in item['ports']:
                    port=LPort(id=len(ports));set_port_owner(port,node);set_side(port,side);ports[name]=port;names[port]=name
            order=[]
            for li,ids in enumerate(spec['layers']):
                layer=Layer(graph,id=li);graph.layers.append(layer);row=[]
                for ni,name in enumerate(ids):node=nodes[name];node.id=ni;set_layer(node,layer);row.append(node)
                order.append(row)
            for a,b in spec['edges']:
                edge=LEdge();set_source(edge,ports[a]);set_target(edge,ports[b])
            positions={port:-1 for port in ports.values()};counter=CrossingsCounter(positions);ends=counter.ends
            count=counter.count_crossings_between_layers(order[0],order[1]) if case['operation']=='between' else counter.count_in_layer_crossings_on_side(order[1],'WEST')
            cardinalities=getattr(counter,'node_cardinalities',None)
            value=dict(count=count,positions=[dict(id=name,value=positions[port]) for name,port in ports.items()],
                       positionBufferShared=counter.port_positions is positions,endsIdentityPreserved=counter.ends is ends,endsEmpty=not counter.ends,
                       cardinalities=[cardinalities[n] for n in order[1]] if cardinalities is not None else None,
                       tree=tree_snapshot(counter.index_tree),nodes=[dict(id=name,cached=node.port_sides_cached,ports=[names[p] for p in node.ports]) for name,node in nodes.items()],layoutExecuted=False)
        rows.append(dict(id=case['id'],actual=value,expected=expected['value'],differences=diff(expected['value'],value)['differences']))
    imported={Path(m.__file__).resolve() for name,m in tuple(sys.modules.items()) if (name=='pyelk' or name.startswith('pyelk.')) and getattr(m,'__file__',None)}
    unchanged=all(sha(p)==before[p] for p in imported)
    result=dict(passed=unchanged and all(not row['differences'] for row in rows),rows=rows,sourceTreeUnchanged=unchanged,
                importedSourcesSha256={p.relative_to(source).as_posix():before[p] for p in imported},
                inputsSha256={str(p):sha(p) for p in (Path(__file__),request,oracle)},layoutExecuted=False,
                scope='Real BIT/basic between and in-layer scores on supplied intermediate objects; no NS/hyperedge dispatcher or complete sweep')
    with report.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],cases=len(rows))))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
