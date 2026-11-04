"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; split/join with supplied segment geometry."""
import hashlib
import json
from pathlib import Path
import sys

def main():
    source,request,oracle,report=map(Path,sys.argv[1:5]);source=source.resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={p.resolve():sha(p)for p in source.rglob('*.py')};sys.path.insert(0,str(source))
    from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,set_layer,set_port_owner,set_source,set_target
    from pyelk.algorithms.layered.native_import import LLabel
    from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.execution.node_micro import VectorChain
    from pyelk.algorithms.layered import long_edges_general as phase
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'));from layout_checks import diff
    original=json.loads(oracle.read_bytes());assert original['requestSha256']==sha(request)
    assert original['probeSha256']==sha(request.with_name('general-long-edge-probe.cjs'))
    assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    cases=[]
    for spec in json.loads(request.read_bytes())['cases']:
        graph=LGraph(None,None,None,properties=CanonicalPropertyMap());nodes=[];names={};edge_names={};events=[];dummies=[]
        for index in range(4):
            layer=Layer(graph);graph.layers.append(layer);node=LNode(graph,properties=CanonicalPropertyMap());set_layer(node,layer);nodes.append(node);names[node]='n'+str(index)
            port=LPort(properties=CanonicalPropertyMap());set_side(port,'WEST'if index==3 else'EAST');set_port_owner(port,node);names[port]='p'+str(index)
        port=lambda index:nodes[index].ports[0]
        edge=LEdge(properties=CanonicalPropertyMap());edge.labels=[];adjacent=LEdge(properties=CanonicalPropertyMap());adjacent.labels=[]
        set_source(edge,port(0));set_target(edge,port(3));set_source(adjacent,port(2));set_target(adjacent,port(3))
        edge_names[edge]='edge';edge_names[adjacent]='adjacent';all_edges=[edge,adjacent]
        edge.properties['EDGE_THICKNESS']=spec['thickness'];graph.properties['UNNECESSARY_BENDPOINTS']=spec['unnecessary']
        initial_junctions=VectorChain([Vec2(1,2)]);edge.properties['JUNCTION_POINTS']=initial_junctions
        label_names={}
        for name,placement,marker in [('tail','TAIL',False),('head','HEAD',False),('keptHead','HEAD',True),('center','CENTER',False)]:
            label=LLabel(name,properties=CanonicalPropertyMap());label_names[label]=name;label.properties['EDGE_LABELS_PLACEMENT']=placement
            if marker:label.properties['END_LABEL_EDGE']=adjacent
            edge.labels.append(label)
        class Monitor:
            def begin(self,name,total):events.append(dict(kind='begin',name=name,total=total))
            def done(self):events.append(dict(kind='done'))
        phase.long_edge_splitter(graph,monitor=Monitor())
        for layer in graph.layers:
            for node in layer.nodes:
                if node.type=='LONG_EDGE':
                    index=len(dummies);dummies.append(node);names[node]='d'+str(index)
                    for j,p in enumerate(node.ports):names[p]='d'+str(index)+'.p'+str(j)
                    generated=node.ports[1].outgoing_edges[0];edge_names[generated]='generated'+str(index);all_edges.append(generated)
        def view():
            labels=list(edge.labels)
            for node in dummies:
                for generated in node.ports[1].outgoing_edges:labels.extend(generated.labels)
            return dict(layers=[[names[node]for node in layer.nodes]for layer in graph.layers],edges=[dict(id=edge_names[e],source=names.get(e.source),target=names.get(e.target),labels=[label_names[l]for l in e.labels],junctionPresent='JUNCTION_POINTS'in e.properties,junctions=[[p.x,p.y]for p in e.properties.get('JUNCTION_POINTS',[])],bends=[[p.x,p.y]for p in e.bend_points])for e in all_edges],dummies=[dict(id=names[n],height=n.size.y,ports=[dict(id=names[p],side=p.side,y=p.pos.y)for p in n.ports],source=names.get(n.properties.get('LONG_EDGE_SOURCE')),target=names.get(n.properties.get('LONG_EDGE_TARGET')),origin=edge_names.get(n.properties.get('ORIGIN')),labelDummies=n.properties.get('LONG_EDGE_HAS_LABEL_DUMMIES',False))for n in dummies],headMarkers=[dict(label=label_names[l],edge=edge_names.get(l.properties.get('END_LABEL_EDGE')))for l in labels if label_names[l]in('head','keptHead')],targetIncoming=[edge_names[e]for e in port(3).incoming_edges],originalJunctionIdentity=phase.get_junction_points(edge)is initial_junctions)
        split=view();supplied_points=[]
        for index,node in enumerate(dummies):
            node.pos.x=10+20*index;node.pos.y=20+20*index;generated=node.ports[1].outgoing_edges[0];p=Vec2(11+20*index,22+20*index);generated.bend_points.append(p);supplied_points.append(p)
            if index==len(dummies)-1:
                p=Vec2(9,8);generated.properties['JUNCTION_POINTS']=VectorChain([p]);supplied_points.append(p)
        phase.long_edge_joiner(graph,monitor=Monitor());joined=view()
        cases.append(dict(id=spec['id'],events=events,split=split,joined=joined,removedDummiesRetainLayer=all(n.layer is not None for n in dummies),droppedEdgesDetached=all(e.source is None and e.target is None for e in all_edges[2:]),copiedPointsFresh=all(all(p is not original for original in supplied_points)for p in edge.bend_points+list(phase.get_junction_points(edge))),dummyCoordinatesSupplied=True,segmentGeometrySupplied=True,layoutExecuted=False))
    actual=dict(cases=cases,layoutExecuted=False);comparison=diff(original['observation'],actual,tolerant=False)
    imported={Path(m.__file__).resolve()for n,m in tuple(sys.modules.items())if(n=='pyelk'or n.startswith('pyelk.'))and getattr(m,'__file__',None)}
    unchanged=all(p in before and sha(p)==before[p]for p in imported)
    result=dict(passed=unchanged and comparison['passed'],actual=actual,expected=original['observation'],comparison=comparison,sourceTreeUnchanged=unchanged,importedSourcesSha256={p.relative_to(source).as_posix():before[p]for p in imported},inputsSha256={str(p):sha(p)for p in(Path(__file__),request,oracle)},checkerSha256=sha(Path(__file__)),dummyCoordinatesSupplied=True,segmentGeometrySupplied=True,layoutExecuted=False,fullValidation=False)
    with report.open('x',encoding='utf-8')as h:json.dump(result,h,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],differences=len(comparison['differences']))));return 0 if result['passed']else 1

if __name__=='__main__':raise SystemExit(main())
