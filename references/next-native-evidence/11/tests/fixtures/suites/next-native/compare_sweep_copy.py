"""Compare saved source capture aliases or NS-aware live order restoration.

Usage: python -I compare_sweep_copy.py PRIVATE_SRC REQUEST ORACLE REPORT copy|transfer
Supplied intermediate order is not a calculated crossing result.
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5]); mode=sys.argv[5]
    assert mode in ('copy','transfer')
    source=source.resolve(); sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={p.resolve():sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0,str(source))
    from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,Layer,set_layer,set_port_owner
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.sweep_copy import SweepCopy
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
    from layout_checks import diff
    original=json.loads(oracle.read_bytes())
    assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256']==sha(request)
    assert original['probeSha256']==sha(request.with_name('sweep-'+mode+'-probe.cjs'))
    rows=[]
    for case,expected in zip(json.loads(request.read_bytes())['cases'],original['results'],strict=True):
        assert case['id']==expected['id']
        graph=LGraph(None,None,None)
        if mode=='copy':
            nodes={};node_names={};port_names={};order=[]
            for li,names in enumerate(case['layers']):
                layer=Layer(graph,id=li);graph.layers.append(layer);row=[]
                for name in names:
                    node=LNode(graph);nodes[name]=node;node_names[node]=name;set_layer(node,layer);row.append(node)
                    for pid in case['ports'][name]:
                        port=LPort();set_port_owner(port,node);port_names[port]=pid
                order.append(row)
            first=SweepCopy(order);second=SweepCopy(first)
            node_order=lambda c:[[node_names[n] for n in layer] for layer in c.node_order]
            port_orders=lambda c:[[[port_names[p] for p in ps] for ps in layer] for layer in c.port_orders]
            initial=dict(nodeOrder=node_order(first),portOrders=port_orders(first),inputOuterIndependent=first.node_order is not order,
                         inputLayerIndependent=first.node_order[0] is not order[0],sameNode=first.node_order[0][0] is nodes['a'],
                         copyNodeOuterIndependent=second.node_order is not first.node_order,
                         copyNodeLayerIndependent=second.node_order[0] is not first.node_order[0],
                         copyPortOuterIndependent=second.port_orders is not first.port_orders,
                         copyPortLayerShared=second.port_orders[0] is first.port_orders[0],
                         copyPortListShared=second.port_orders[0][0] is first.port_orders[0][0])
            order[0].reverse();nodes['a'].ports.reverse()
            edited=dict(firstNodes=node_order(first),firstPorts=port_orders(first),inputNodes=[[node_names[n] for n in l] for l in order],
                        originalAPorts=[port_names[p] for p in nodes['a'].ports])
            extra=LPort();port_names[extra]='capturedOnly';first.port_orders[0][0].append(extra);first.port_orders.append([]);first.node_order[0].reverse()
            value=dict(before=initial,afterOriginalEdits=edited,afterCopyEdits=dict(firstNodes=node_order(first),secondNodes=node_order(second),
                       firstPorts=port_orders(first),secondPorts=port_orders(second),originalAPorts=[port_names[p] for p in nodes['a'].ports]),
                       transferExecuted=False,counterExecuted=False,layoutExecuted=False)
        else:
            layer=Layer(graph);graph.layers.append(layer)
            owner,dummy=LNode(graph),LNode(graph,type='NORTH_SOUTH_PORT');set_layer(owner,layer);set_layer(dummy,layer)
            active,other,dp=LPort(),LPort(),LPort();set_port_owner(active,owner);set_port_owner(other,owner);set_port_owner(dp,dummy)
            active.size.x,active.size.y=case['size'];active.explicitly_supplied_port_anchor=True;active.anchor.x,active.anchor.y=case['anchor']
            set_side(active,case['side']);set_side(other,'EAST');set_side(dp,'EAST')
            owner.properties['PORT_CONSTRAINTS']=case['constraint'];dummy.properties['IN_LAYER_LAYOUT_UNIT']=owner;dp.properties['ORIGIN']=active
            captured=SweepCopy([[owner,dummy] if case['ownerFirst'] else [dummy,owner]])
            layer_list,owner_ports,dummy_ports=layer.nodes,owner.ports,dummy.ports;owner.ports.reverse()
            captured.transfer_node_and_port_orders_to_graph(graph)
            names={owner:'owner',dummy:'dummy',active:'active',other:'other',dp:'dummyPort'}
            def node(n):
                return dict(name=names[n],id=n.id,constraint=n.properties['PORT_CONSTRAINTS'],
                            ports=[dict(name=names[p],side=p.side,anchor=[p.anchor.x,p.anchor.y]) for p in n.ports],
                            cached=n.port_sides_cached,ranges={k:list(v) for k,v in n.port_side_indices.items()},
                            graphRetained=n.graph is graph,layerRetained=n.layer is layer)
            value=dict(order=[names[n] for n in layer.nodes],owner=node(owner),dummy=node(dummy),layerListIdentity=layer.nodes is layer_list,
                       ownerPortListIdentity=owner.ports is owner_ports,dummyPortListIdentity=dummy.ports is dummy_ports,
                       orderSupplied=True,counterExecuted=False,layoutExecuted=False)
        rows.append(dict(id=case['id'],actual=value,expected=expected['value'],differences=diff(expected['value'],value)['differences']))
    imported={Path(m.__file__).resolve() for name,m in tuple(sys.modules.items()) if (name=='pyelk' or name.startswith('pyelk.')) and getattr(m,'__file__',None)}
    unchanged=all(sha(p)==before[p] for p in imported)
    result=dict(passed=unchanged and all(not row['differences'] for row in rows),rows=rows,sourceTreeUnchanged=unchanged,
                importedSourcesSha256={p.relative_to(source).as_posix():before[p] for p in imported},
                inputsSha256={str(p):sha(p) for p in (Path(__file__),request,oracle)},mode=mode,layoutExecuted=False,
                scope='Capture alias depth or live restore/NS side-anchor math on supplied intermediate objects only; no crossing score or scheduler')
    with report.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],cases=len(rows))))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
