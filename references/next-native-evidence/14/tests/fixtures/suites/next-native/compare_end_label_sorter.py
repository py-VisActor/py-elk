"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; actual prepared cells, no producer claim."""
import hashlib
import json
from pathlib import Path
import sys

def main():
    source,request,oracle,report=map(Path,sys.argv[1:5]);source=source.resolve()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={p.resolve():sha(p)for p in source.rglob('*.py')};sys.path.insert(0,str(source))
    from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,set_layer,set_port_owner,set_source,set_target
    from pyelk.algorithms.layered.native_import import LLabel
    from pyelk.algorithms.layered.native_adapters import LLabelAdapter
    from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
    from pyelk.algorithms.layered.cell_layout import LabelCell
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered import end_labels_general as phase
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'));from layout_checks import diff
    expected=json.loads(oracle.read_bytes())
    assert expected['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert expected['requestSha256']==sha(request)and expected['probeSha256']==sha(request.with_name('end-label-sorter-probe.cjs'))
    spec=json.loads(request.read_bytes());graph=LGraph(None,None,None,properties=CanonicalPropertyMap())
    layers=[Layer(graph),Layer(graph)];graph.layers=layers;nodes,ports,edges,labels={},{},{},{}
    for row in spec['nodes']:
        node=nodes[row['id']]=LNode(graph,properties=CanonicalPropertyMap());set_layer(node,layers[row['layer']]);node.id=99
        for name in row['ports']:
            port=ports[name]=LPort(properties=CanonicalPropertyMap());set_side(port,'WEST'if row['id']=='b'else'EAST');set_port_owner(port,node);port.id=99
    for name,a,b in spec['edges']:
        edge=edges[name]=LEdge(properties=CanonicalPropertyMap());edge.labels=[];set_source(edge,ports[a]);set_target(edge,ports[b])
    for name,edge,placement in spec['labels']:
        label=labels[name]=LLabel(name,properties=CanonicalPropertyMap());label.properties['EDGE_LABELS_PLACEMENT']=placement;label.properties['END_LABEL_EDGE']=edges[edge];edges[edge].labels.append(label)
    cells=[]
    for row in spec['cells']:
        cell=LabelCell(0);cell.labels=[LLabelAdapter(labels[name])for name in row['labels']]
        nodes[row['node']].properties.setdefault('END_LABELS',{})[ports[row['port']]]=cell;cells.append((row,cell,cell.labels,list(cell.labels)))
    events=[];initializations=[]
    class Monitor:
        def begin(self,name,total):events.append(dict(kind='begin',name=name,total=total))
        def done(self):events.append(dict(kind='done'))
    original=phase.initialize
    def initialize(g):initializations.append(g is graph);return original(g)
    phase.initialize=initialize
    try:phase.end_label_sorter(graph,monitor=Monitor())
    finally:phase.initialize=original
    actual=dict(events=events,initializations=initializations,cells=[dict(port=row['port'],labels=[a.element.text for a in cell.labels],sameList=cell.labels is saved,sameAdapters=all(any(a is b for b in refs)for a in cell.labels))for row,cell,saved,refs in cells],ids=[dict(node=row['id'],id=nodes[row['id']].id,ports=[dict(port=p,id=ports[p].id)for p in row['ports']])for row in spec['nodes']],edgeLabels=[dict(edge=row[0],labels=[l.text for l in edges[row[0]].labels])for row in spec['edges']],geometry=[dict(label=row[0],x=labels[row[0]].pos.x,y=labels[row[0]].pos.y,width=labels[row[0]].size.x,height=labels[row[0]].size.y)for row in spec['labels']],preparedCells=True,layoutExecuted=False)
    comparison=diff(expected['observation'],actual,tolerant=False)
    imported={Path(m.__file__).resolve()for n,m in tuple(sys.modules.items())if(n=='pyelk'or n.startswith('pyelk.'))and getattr(m,'__file__',None)}
    unchanged=all(p in before and sha(p)==before[p]for p in imported)
    result=dict(passed=unchanged and comparison['passed'],actual=actual,expected=expected['observation'],comparison=comparison,sourceTreeUnchanged=unchanged,importedSourcesSha256={p.relative_to(source).as_posix():before[p]for p in imported},inputsSha256={str(p):sha(p)for p in(Path(__file__),request,oracle)},checkerSha256=sha(Path(__file__)),layoutExecuted=False,preparedCells=True,fullValidation=False)
    with report.open('x',encoding='utf-8')as h:json.dump(result,h,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],differences=len(comparison['differences']))));return 0 if result['passed']else 1

if __name__=='__main__':raise SystemExit(main())
