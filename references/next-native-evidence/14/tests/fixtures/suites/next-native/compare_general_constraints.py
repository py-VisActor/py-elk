"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; actual constraint helpers only."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path,sys.argv[1:5])
    source=source.resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={p.resolve():sha(p)for p in source.rglob('*.py')}
    sys.path.insert(0,str(source))
    from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,set_port_owner,set_source,set_target,set_layer
    from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered import constraint_processors as phase
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
    from layout_checks import diff
    original=json.loads(oracle.read_bytes())
    assert original['requestSha256']==sha(request)
    assert original['probeSha256']==sha(request.with_name('general-constraints-probe.cjs'))
    assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    results=[]
    for item in json.loads(request.read_bytes())['cases']:
        graph=LGraph(None,None,None);graph.properties=CanonicalPropertyMap()
        nodes,ports,edges={},{},{}
        for row in item['nodes']:
            node=nodes[row['id']]=LNode(graph);node.properties=CanonicalPropertyMap()
            node.type=row.get('type','NORMAL');graph.layerless_nodes.append(node)
            if 'constraint'in row:node.properties['LAYERING_LAYER_CONSTRAINT']=row['constraint']
            if 'portConstraints'in row:node.properties['PORT_CONSTRAINTS']=row['portConstraints']
            port=ports[row['id']]=LPort();port.properties=CanonicalPropertyMap()
            set_side(port,'EAST');set_port_owner(port,node)
        for values in item['edges']:
            name,a,b,*reversed_flag=values;edge=edges[name]=LEdge();edge.properties=CanonicalPropertyMap()
            set_source(edge,ports[a])
            if b is not None:set_target(edge,ports[b])
            if reversed_flag and reversed_flag[0]:edge.properties['REVERSED']=True
        node_names={v:k for k,v in nodes.items()};port_names={v:k+':p'for k,v in ports.items()};edge_names={v:k for k,v in edges.items()}
        def view():
            return dict(layerless=[node_names[n]for n in graph.layerless_nodes],
                layers=[[node_names[n]for n in l.nodes]for l in graph.layers],
                nodes=[dict(id=row['id'],hasConstraint='LAYERING_LAYER_CONSTRAINT'in nodes[row['id']].properties,
                    constraint=phase._layer_constraint(nodes[row['id']]),edgeConstraint=nodes[row['id']].properties.get('EDGE_CONSTRAINT'),
                    connection=nodes[row['id']].properties.get('separateLayerConnections'),
                    incoming=[edge_names[e]for e in ports[row['id']].incoming_edges],outgoing=[edge_names[e]for e in ports[row['id']].outgoing_edges])for row in item['nodes']],
                edges=[dict(id=values[0],source=port_names.get(edges[values[0]].source),target=port_names.get(edges[values[0]].target),
                    reversed=edges[values[0]].properties.get('REVERSED'),originalOpposite=port_names.get(edges[values[0]].properties.get('ORIGINAL_OPPOSITE_PORT')))for values in item['edges']],
                hidden=[node_names[n]for n in graph.properties['HIDDEN_NODES']]if'HIDDEN_NODES'in graph.properties else None)
        events=[]
        class Monitor:
            def begin(self,name,total):events.append(dict(kind='begin',name=name,total=total))
            def done(self):events.append(dict(kind='done'))
        before_post=None;visits=[]
        if item['kind']=='reverse':phase.edge_and_layer_constraint_edge_reverser(graph,monitor=Monitor())
        else:
            if item['kind']=='hideRestore':
                phase.layer_constraint_preprocessor(graph,monitor=Monitor());before_post=view()
                layer=Layer(graph);graph.layers.append(layer)
                for node in list(graph.layerless_nodes):set_layer(node,layer)
                graph.layerless_nodes.clear()
            else:
                graph.properties['HIDDEN_NODES']=[nodes['F']]
                edges['loop'].properties['ORIGINAL_OPPOSITE_PORT']=ports['F'];graph.layerless_nodes.clear()
            saved=phase._connected_edges
            def traced(node):
                for edge in saved(node):
                    if item['kind']=='postSelfLoop':visits.append(edge_names[edge])
                    yield edge
            phase._connected_edges=traced
            try:phase.layer_constraint_postprocessor(graph,monitor=Monitor())
            finally:phase._connected_edges=saved
        results.append(dict(id=item['id'],events=events,beforePost=before_post,after=view(),visits=visits,
            suppliedPostLayers=item['kind']=='hideRestore',preparedHiddenNodes=item.get('preparedHiddenNodes',False)))
    actual=dict(cases=results,layoutExecuted=False,workingGraphHelpersExecuted=True)
    comparison=diff(original['observation'],actual,tolerant=False)
    imported={Path(m.__file__).resolve()for name,m in tuple(sys.modules.items())if(name=='pyelk'or name.startswith('pyelk.'))and getattr(m,'__file__',None)}
    unchanged=all(p in before and sha(p)==before[p]for p in imported)
    result=dict(passed=unchanged and comparison['passed'],actual=actual,expected=original['observation'],comparison=comparison,
        sourceTreeUnchanged=unchanged,importedSourcesSha256={p.relative_to(source).as_posix():before[p]for p in imported},
        inputsSha256={str(p):sha(p)for p in(Path(__file__),request,oracle)},checkerSha256=sha(Path(__file__)),
        layoutExecuted=False,workingGraphHelpersExecuted=True,fullValidation=False)
    with report.open('x',encoding='utf-8')as handle:json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],differences=len(comparison['differences']))))
    return 0 if result['passed']else 1


if __name__=='__main__':raise SystemExit(main())
