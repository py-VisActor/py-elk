const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__restoreDirector=function(request){
 $clinit_CoreOptions();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_PortConstraints();$clinit_Direction_0();$clinit_SelfLoopOrderingStrategy();$clinit_SelfLoopDistributionStrategy();
 const arr=list=>{const a=[],i=list.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;},sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2},result=[];
 for(const input of request.cases){
   const g=new LGraph,n=new LNode(g),other=new LNode(g),names=new Map,all=[];$add_3(g.layerlessNodes,n);$add_3(g.layerlessNodes,other);$setProperty_0(g,DIRECTION,RIGHT_6);$setProperty_0(g,RANDOM_0,new Random_0(7));
   const constraints=input.constraints==='FREE'?FREE:FIXED_SIDE;$setProperty_0(n,PORT_CONSTRAINTS_0,constraints);$setProperty_0(n,ORIGINAL_PORT_CONSTRAINTS,constraints);$setProperty_0(n,EDGE_ROUTING_SELF_LOOP_DISTRIBUTION_0,input.distribution==='NORTH'?NORTH_2:EQUALLY);$setProperty_0(n,EDGE_ROUTING_SELF_LOOP_ORDERING_0,{STACKED,REVERSE_STACKED,SEQUENCED}[input.ordering]);
   let edgeId=0;
   input.loops.forEach((sequence,i)=>{const ps=sequence.map((side,j)=>{const p=new LPort;$setNode(p,n);$setSide(p,sides[side]);names.set(p,'loop'+i+'.'+j);all.push(p);return p;});for(let j=0;j<ps.length-1;j++){const e=new LEdge;e.id_0=edgeId++;$setSource_0(e,ps[j]);$setTarget_0(e,ps[j+1]);}});
   for(const side of ['NORTH','EAST','SOUTH','WEST']){const p=new LPort,t=new LPort;$setNode(p,n);$setNode(t,other);$setSide(p,sides[side]);names.set(p,'visible-'+side);all.push(p);const e=new LEdge;e.id_0=edgeId++;$setSource_0(e,p);$setTarget_0(e,t);}
   $process_49(g,new BasicProgressMonitor);const holder=$getProperty(n,SELF_LOOP_HOLDER);n.ports.sort_0(new LGraphAdapters$PortComparator);const layer=new Layer(g);$add_3(g.layers,layer);$setLayer(n,0,layer);$setLayer(other,1,layer);g.layerlessNodes.array.length=0;
   const monitor=new BasicProgressMonitor;$process_47(new SelfLoopPortRestorer,g,monitor);const restored=n.ports.array.map(p=>names.get(p)),director=new RoutingDirector;$determineLoopRoutes(director,holder);
   result.push({name:input.name,restored,ports:all.map(p=>({name:names.get(p),owner:p.owner===n,id:p.id_0,side:p.side.name_0})),hidden:arr((new AbstractMap$2(holder.slPorts)).this$01.entrySet_0()).map(e=>({name:names.get(e.getKey()),hidden:e.getValue().isHidden})),portsHidden:holder.arePortsHidden,monitorRunning:monitor.isRunning(),penaltiesCleared:director.portPenalties==null,loops:holder.slHyperLoops.array.map(loop=>({type:loop.selfLoopType.name_0,ports:loop.slPorts.array.map(p=>names.get(p.lPort)),left:names.get(loop.leftmostPort.lPort),right:names.get(loop.rightmostPort.lPort),occupied:arr(loop.occupiedPortSides).map(s=>s.name_0),groups:arr($keySet(loop.slPortsBySide)).map(side=>[side.name_0,arr($get(loop.slPortsBySide,side)).map(p=>names.get(p.lPort))])}))});
 }
 return result;
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(fs.readFileSync(requestPath)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__restoreDirector(request),actualPreRestorerDirector:true,layoutExecuted:false,nativeExecuted:false},null,2)+'\n',{flag:'wx'});
