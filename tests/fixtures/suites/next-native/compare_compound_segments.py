"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; real pre/post with supplied geometry."""
import hashlib
import json
from pathlib import Path
import sys

def main():
    source,request,oracle,report=map(Path,sys.argv[1:5]);source=source.resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before={p.resolve():sha(p)for p in source.rglob('*.py')};sys.path.insert(0,str(source))
    from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Vec2,set_port_owner,set_source,set_target
    from pyelk.algorithms.layered.native_import import LLabel
    from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
    from pyelk.algorithms.layered.compound_pre import CompoundGraphPreprocessor
    from pyelk.algorithms.layered.compound_post import compound_postprocessor
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.execution.node_micro import VectorChain
    from pyelk.execution.diagnostics import BasicProgressMonitor
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'));from layout_checks import diff
    raw=json.loads(oracle.read_bytes());assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert raw['requestSha256']==sha(request)and raw['probeSha256']==sha(request.with_name('compound-segments-probe.cjs'))
    inputs=json.loads(request.read_bytes());geometry=inputs['geometry'];cases=[]
    for spec in inputs['cases']:
        names={};graphs={};original=[];original_names={};label_names={}
        def graph(name):
            g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();g.properties['DIRECTION']='RIGHT';g.properties['GRAPH_PROPERTIES']=set();graphs[name]=g;names[g]=name;return g
        r=graph('r');a=graph('A');b=graph('B');r.offset=Vec2(*geometry['rootOffset'])
        def node(g,name,x,y):
            n=LNode(g,type='NORMAL',properties=CanonicalPropertyMap());n.labels=[];n.pos=Vec2(x,y);n.size=Vec2(60,40);g.layerless_nodes.append(n);names[n]=name;return n
        pa=node(r,'parentA',*geometry['A']['nodePos']);pb=node(r,'parentB',*geometry['B']['nodePos']);pa.nested_graph=a;a.parent_node=pa;pb.nested_graph=b;b.parent_node=pb
        for key in('A','B'):
            g=graphs[key];v=geometry[key];g.offset=Vec2(*v['offset']);g.padding.top,g.padding.right,g.padding.bottom,g.padding.left=v['padding']
        x=node(a,'x',7,9);y=node(b,'y',10,11);z=node(b,'z',23,17)
        def port(n,name,side):
            p=LPort(properties=CanonicalPropertyMap());p.labels=[];set_port_owner(p,n);set_side(p,side);p.pos=Vec2(2,3);p.size=Vec2(4,6);p.anchor=Vec2(2,3);names[p]=name;return p
        xp=port(x,'xp','EAST');yp=port(y,'yp','WEST');zp=port(z,'zp','WEST');back=port(z,'back','EAST');xin=port(x,'xin','WEST')
        def edge(name,source,target,placement):
            e=LEdge(properties=CanonicalPropertyMap());e.labels=[];set_source(e,source);set_target(e,target);e.properties['EDGE_THICKNESS']=5 if name=='e1'else 2;original.append(e);original_names[e]=name
            l=LLabel(text=name);l.size=Vec2(10,4);l.properties=CanonicalPropertyMap();l.properties['EDGE_LABELS_PLACEMENT']=placement;e.labels.append(l);label_names[l]=name+'-label';return e
        edge('e0',xp,yp,'CENTER');edge('e1',xp,zp,'TAIL');edge('e2',back,xin,'HEAD')
        prep=CompoundGraphPreprocessor();prep.process(r,monitor=BasicProgressMonitor());mapping=r.properties['CROSS_HIERARCHY_MAP'];tokens={}
        def port_name(p):return None if p is None else names[p]if p in names else names[p.owner]+':port'+str(p.owner.ports.index(p))
        records=[]
        for e in original:
            segments=[]
            for ch in mapping.values_for(e):
                if ch.new_edge not in tokens:tokens[ch.new_edge]=len(tokens)
                segments.append(dict(graph=names[ch.graph],type=ch.type,edgeToken=tokens[ch.new_edge],actualSource=port_name(ch.get_actual_source()),actualTarget=port_name(ch.get_actual_target()),labels=[label_names[l]for l in ch.new_edge.labels],thickness=ch.new_edge.properties['EDGE_THICKNESS']))
            records.append(dict(id=original_names[e],detached=e.source is None and e.target is None,labels=[label_names[l]for l in e.labels],segments=segments))
        for name,g in graphs.items():
            if name!='r':
                for n in g.layerless_nodes:
                    if n.type=='EXTERNAL_PORT':n.pos=Vec2(*geometry[name]['dummyPos'])
            for n in g.layerless_nodes:
                for p in n.ports:
                    for e in p.outgoing_edges:
                        if e not in tokens:continue
                        v=geometry[name];e.bend_points.clear();e.bend_points.extend(Vec2(*q)for q in v['bends']);e.properties['JUNCTION_POINTS']=VectorChain(Vec2(*q)for q in(v['junctions']if spec['junctions']else[]))
                        for l in e.labels:l.pos=Vec2(11,13)
        compound_postprocessor(r,monitor=BasicProgressMonitor())
        def points(chain):return [[v.x,v.y]for v in chain]if chain is not None else None
        after=[]
        for e in original:
            offset=e.properties['TARGET_OFFSET'];present='JUNCTION_POINTS'in e.properties
            after.append(dict(id=original_names[e],source=port_name(e.source),target=port_name(e.target),bends=points(e.bend_points),junctionPresent=present,junctions=points(e.properties['JUNCTION_POINTS'])if present else None,targetOffset=[offset.x,offset.y],labels=[dict(id=label_names[l],position=[l.pos.x,l.pos.y],originalEdge=l.properties.get('ORIGINAL_LABEL_EDGE')is e)for l in e.labels]))
        cases.append(dict(id=spec['id'],before=records,after=after,flags={k:sorted(g.properties['GRAPH_PROPERTIES'])for k,g in graphs.items()},allDummyEdgesDetached=all(e.source is None and e.target is None for e in tokens),persistentMapCleared=len(prep.dummy_node_map.keys.values())==0,preMapFieldCleared=prep.cross_hierarchy_map is None,geometrySupplied=True,routingExecuted=False,layoutExecuted=False))
    actual=dict(cases=cases,geometrySupplied=True,routingExecuted=False,layoutExecuted=False);comparison=diff(raw['observation'],actual,tolerant=False)
    imported={Path(m.__file__).resolve()for n,m in tuple(sys.modules.items())if(n=='pyelk'or n.startswith('pyelk.'))and getattr(m,'__file__',None)};unchanged=all(p in before and sha(p)==before[p]for p in imported)
    result=dict(passed=unchanged and comparison['passed'],actual=actual,expected=raw['observation'],comparison=comparison,sourceTreeUnchanged=unchanged,importedSourcesSha256={p.relative_to(source).as_posix():before[p]for p in imported},inputsSha256={str(p):sha(p)for p in(Path(__file__),request,oracle)},geometrySupplied=True,routingExecuted=False,layoutExecuted=False,fullValidation=False)
    with report.open('x',encoding='utf8')as h:json.dump(result,h,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],differences=len(comparison['differences']))));return 0 if result['passed']else 1

if __name__=='__main__':raise SystemExit(main())
