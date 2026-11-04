const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__polyline=function(request){
 $clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_GraphProperties();
 const types={NORMAL,LONG_EDGE,NORTH_SOUTH_PORT,LABEL,EXTERNAL_PORT},sides={WEST:WEST_2,EAST:EAST_2},flags={NORTH_SOUTH_PORTS,SELF_LOOPS,CENTER_LABELS,END_LABELS},arr=list=>{const a=[],it=list.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;},xy=p=>[p.x_0,p.y_0],router=new PolylineEdgeRouter,initialSet=router.createdJunctionPoints,records=[];
 for(const input of request.cases){
  const g=new LGraph,nodes=new Map,ports=new Map,edges=[];
  if(input.zone!==undefined)$setProperty_0(g,EDGE_ROUTING_POLYLINE_SLOPED_EDGE_ZONE_WIDTH_0,input.zone);
  const actualFlags=$getProperty(g,GRAPH_PROPERTIES);for(const name of input.flags)$add_5(actualFlags,flags[name]);
  for(const l of input.layers){const layer=new Layer(g);$add_3(g.layers,layer);layer.size_0.x_0=l.width;for(const item of l.nodes){const n=new LNode(g);n.type_0=types[item.type||'NORMAL'];n.pos.y_0=item.y;n.size_0.x_0=item.width;n.size_0.y_0=10;$set_6(n.margin,1,2.25,1.5,1.5);$setLayer(n,layer.nodes.array.length,layer);nodes.set(item.name,n);if(item.externalSide)$setProperty_0(n,EXT_PORT_SIDE,sides[item.externalSide]);for(const name of ['WEST','EAST']){const p=new LPort;$setNode(p,n);$setSide(p,sides[name]);p.pos.x_0=name==='WEST'?0:item.width;p.pos.y_0=5;ports.set(item.name+':'+name,p);}}}
  for(const l of input.layers)for(const item of l.nodes)if(item.origin)for(const side of ['WEST','EAST'])$setProperty_0(ports.get(item.name+':'+side),ORIGIN_0,ports.get(item.origin));
  input.edges.forEach((item,index)=>{const e=new LEdge;e.id_0=index;$setSource_0(e,ports.get(item.source));$setTarget_0(e,ports.get(item.target));for(const p of item.bends||[])$add_7(e.bendPoints,new KVector_1(...p));if(item.junctions){const chain=new KVectorChain;for(const p of item.junctions)$add_7(chain,new KVector_1(...p));$setProperty_0(e,JUNCTION_POINTS,chain);}edges.push(e);});
  const cfg=$getLayoutProcessorConfiguration_1(g),configurationRaw=cfg.list.array.map(s=>arr(s).map(v=>({name:v.name_0,ordinal:v.ordinal}))),configurationByOrdinal=configurationRaw.map(s=>s.slice().sort((a,b)=>a.ordinal-b.ordinal).map(v=>v.name));
  const before=edges.map(e=>({bends:arr(e.bendPoints).map(xy),junctionPresent:$hasProperty(e,JUNCTION_POINTS)})),monitor=new BasicProgressMonitor;
  $process_85(router,g,monitor);
  records.push({name:input.name,width:g.size_0.x_0,nodes:[...nodes].map(([name,n])=>({name,position:xy(n.pos)})),before,edges:edges.map(e=>({id:e.id_0,bends:arr(e.bendPoints).map(xy),junctionPresent:$hasProperty(e,JUNCTION_POINTS),junctions:$hasProperty(e,JUNCTION_POINTS)?arr($getProperty(e,JUNCTION_POINTS)).map(xy):null})),configurationRaw,configurationByOrdinal,monitorRunning:monitor.isRunning(),monitorClosed:monitor.closed_0,samePersistentSet:router.createdJunctionPoints===initialSet,junctionSetSize:initialSet.map_0.size_1()});
 }
 const empty=new LGraph;empty.size_0.x_0=123;const monitor=new BasicProgressMonitor;let reads=0;const realGet=$getProperty;$getProperty=function(o,p){if(o===empty)reads++;return realGet(o,p);};try{$process_85(router,empty,monitor);}finally{$getProperty=realGet;}
 return {cases:records,empty:{width:empty.size_0.x_0,optionReads:reads,running:monitor.isRunning(),closed:monitor.closed_0,samePersistentSet:router.createdJunctionPoints===initialSet,junctionSetSize:initialSet.map_0.size_1()}};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(fs.readFileSync(requestPath)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__polyline(request),actualProcess85Executed:true,layoutExecuted:false,nativeExecuted:false},null,2)+'\n',{flag:'wx'});
