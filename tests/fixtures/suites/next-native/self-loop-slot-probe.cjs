const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__slotObservations=function(request){
 $clinit_CoreOptions();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_PortConstraints();$clinit_Direction_0();
 const arr=list=>{const a=[],i=list.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;},sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2},result=[];
 for(const input of request.cases){
   const g=new LGraph,n=new LNode(g),ports=input.sides.map(side=>{const p=new LPort;$setNode(p,n);$setSide(p,sides[side]);return p;});$add_3(g.layerlessNodes,n);$setProperty_0(g,DIRECTION,RIGHT_6);$setProperty_0(n,PORT_CONSTRAINTS_0,FIXED_ORDER);$setProperty_0(n,ORIGINAL_PORT_CONSTRAINTS,FIXED_ORDER);
   let eid=0;input.groups.forEach((group,i)=>{for(let j=0;j<group.length-1;j++){const e=new LEdge;e.id_0=eid++;$setSource_0(e,ports[group[j]]);$setTarget_0(e,ports[group[j+1]]);if(input.labels&&j===0){const l=new LLabel;l.size_0.x_0=20+i;l.size_0.y_0=4+i;$add_3(e.labels,l);}}});
   let holder;
   if(input.groups.length){$process_49(g,new BasicProgressMonitor);holder=$getProperty(n,SELF_LOOP_HOLDER);}else holder=new SelfLoopHolder(n);
   const layer=new Layer(g);$add_3(g.layers,layer);$setLayer(n,0,layer);g.layerlessNodes.array.length=0;$process_47(new SelfLoopPortRestorer,g,new BasicProgressMonitor);$determineLoopRoutes(new RoutingDirector,holder);
   for(const loop of holder.slHyperLoops.array){if(loop.slLabels){loop.slLabels.side=NORTH_3;loop.slLabels.position.x_0=0;loop.slLabels.position.y_0=-8;}}
   const random=input.groups.length?new Random_0(7):null;if(random)$setProperty_0(g,RANDOM_0,random);const before=random?[random.seedhi,random.seedlo]:null,bounds=[],realNext=$nextInt,realGet=$getProperty;let reads=0;
   $nextInt=function(r,b){if(r===random)bounds.push(b);return realNext(r,b);};$getProperty=function(o,k){if(o===g&&k===RANDOM_0)reads++;return realGet(o,k);};const assigner=new RoutingSlotAssigner;
   try{$assignRoutingSlots(assigner,holder);}finally{$nextInt=realNext;$getProperty=realGet;}
   result.push({name:input.name,randomReads:reads,nextIntBounds:bounds,seedBefore:before,seedAfter:random?[random.seedhi,random.seedlo]:null,slots:holder.slHyperLoops.array.map(loop=>({ports:loop.slPorts.array.map(p=>p.lPort.id_0),occupied:arr(loop.occupiedPortSides).map(p=>p.name_0),routing:Array.from(loop.routingSlot),labelId:loop.slLabels?loop.slLabels.id_0:null})),slotCount:Array.from(holder.routingSlotCount),scratchCleared:assigner.hyperEdgeSegments==null&&assigner.slLoopToSegmentMap==null&&assigner.slLoopActivityOverPorts==null});
 }
 return result;
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(fs.readFileSync(requestPath)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__slotObservations(request),actualSlotAssignerExecuted:true,observerOnlyRandomGetterAndNextInt:true,layoutExecuted:false,nativeExecuted:false},null,2)+'\n',{flag:'wx'});
