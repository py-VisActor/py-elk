const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),req=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__hierarchyResize=function(request){
 registerLayoutAlgorithms(['layered']);$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_GraphProperties();
 const list=c=>{const a=[],i=c.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;};
 const num=v=>Number.isNaN(v)?'NaN':!Number.isFinite(v)?String(v):Object.is(v,-0)?'-0':v,vec=v=>[num(v.x_0),num(v.y_0)];
 const props=g=>list($getProperty(g,GRAPH_PROPERTIES)).map(x=>x.name_0);
 const empty=()=>{const a=$getEnumConstants(Lorg_eclipse_elk_alg_layered_options_GraphProperties_2_classLit);return new EnumSet$EnumSetImpl(a,createFrom(a,a.length),0);};
 return request.cases.map(c=>{
  const outer=new LGraph,parent=new LNode(outer),g=new LGraph;
  $setProperty_0(outer,GRAPH_PROPERTIES,empty());$add_3(outer.layerlessNodes,parent);
  parent.size_0.x_0=c.parentSize[0];parent.size_0.y_0=c.parentSize[1];
  if(c.parent)g.parentNode=parent;
  g.size_0.x_0=c.size[0];g.size_0.y_0=c.size[1];g.offset.x_0=3;g.offset.y_0=4;
  [g.padding.top_0,g.padding.right,g.padding.bottom,g.padding.left]=[1,2,3,4];
  const cfg=optsToCfg(new JSONObject_0(c.options));$applyProperties(cfg,g,$configure(cfg,Lorg_eclipse_elk_graph_ElkNode_2_classLit));
  const gp=empty();if(c.external)gp.add_2(EXTERNAL_PORTS);$setProperty_0(g,GRAPH_PROPERTIES,gp);
  const sides=[NORTH_3,EAST_2,SOUTH_2,WEST_2],ports=[],nodes=[],layers=[];
  for(let i=0;i<4;i++){
   const p=new LPort;$setNode(p,parent);p.size_0.x_0=2;p.size_0.y_0=4;p.pos.x_0=2+i;p.pos.y_0=3+i;p.anchor.x_0=9;p.anchor.y_0=11;$setSide(p,sides[i]);ports.push(p);
   const n=new LNode(g);n.id_0=i;n.type_0=EXTERNAL_PORT;n.pos.x_0=7+i;n.pos.y_0=9+i;n.size_0.x_0=4;n.size_0.y_0=6;
   $setProperty_0(n,EXT_PORT_SIDE,sides[i]);$setProperty_0(n,PORT_BORDER_OFFSET,2.5);$setProperty_0(n,ORIGIN_0,p);nodes.push(n);
   if(i<2)$add_3(g.layerlessNodes,n);else{const l=new Layer(g);layers.push(l);$add_3(g.layers,l);$setLayer(n,0,l);}
  }
  const ignored=new LNode(g);ignored.id_0=4;$setProperty_0(ignored,ORIGIN_0,{pos:{x_0:999,y_0:999}});$add_3(g.layerlessNodes,ignored);nodes.push(ignored);
  const labels=[[9,1,2,2],[1,19,2,2],[1,1,2,2],[9,19,2,2],[-8,30,2,2],[30,-8,2,2]];
  for(const [x,y,w,h] of labels){const l=new LLabel;l.pos.x_0=x;l.pos.y_0=y;l.size_0.x_0=w;l.size_0.y_0=h;$add_3(parent.labels,l);}
  const refs={layers:g.layers,layerless:g.layerlessNodes,size:g.size_0,offset:g.offset,parentSize:parent.size_0,ports:ports.map(p=>p.pos),labels:parent.labels.array.map(l=>l.pos)};
  const monitor=new BasicProgressMonitor;new HierarchicalNodeResizingProcessor().process(g,monitor);
  const minimum=$hasProperty(g,NODE_SIZE_MINIMUM_0)?$getProperty(g,NODE_SIZE_MINIMUM_0):null;
  return {name:c.name,size:vec(g.size_0),offset:vec(g.offset),minimum:minimum?vec(minimum):null,
   nodes:g.layerlessNodes.array.map(n=>({id:n.id_0,pos:vec(n.pos),layerNull:n.layer===null})),layers:g.layers.array.length,oldLayerCounts:layers.map(l=>l.nodes.array.length),
   parentSize:vec(parent.size_0),portConstraints:$getProperty(parent,PORT_CONSTRAINTS_0).name_0,parentConstraints:list($getProperty(parent,NODE_SIZE_CONSTRAINTS_1)).map(x=>x.name_0),outerProperties:props(outer),
   ports:ports.map(p=>({pos:vec(p.pos),anchor:vec(p.anchor),side:p.side.name_0})),labels:parent.labels.array.map(l=>vec(l.pos)),monitorFinished:!monitor.isRunning(),
   references:[refs.layers===g.layers,refs.layerless===g.layerlessNodes,refs.size===g.size_0,refs.offset===g.offset,refs.parentSize===parent.size_0,...ports.map((p,i)=>p.pos===refs.ports[i]),...parent.labels.array.map((l,i)=>l.pos===refs.labels[i])]};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(req),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__hierarchyResize(JSON.parse(req)),actualHierarchicalResize:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
