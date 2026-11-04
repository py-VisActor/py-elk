const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__labelObservations=function(request){
 $clinit_CoreOptions();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_Direction_0();$clinit_SelfLoopOrderingStrategy();
 const sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2},result=[];
 for(const input of request.cases){
  const g=new LGraph,n=new LNode(g),holder=new SelfLoopHolder(n);$add_3(g.layerlessNodes,n);$setProperty_0(g,DIRECTION,RIGHT_6);$setProperty_0(n,EDGE_ROUTING_SELF_LOOP_ORDERING_0,input.ordering==='SEQUENCED'?SEQUENCED:STACKED);n.size_0.x_0=123.5;n.size_0.y_0=67.25;
  for(const [i,item] of input.loops.entries()){
   const loop=new SelfHyperLoop(holder);$add_3(holder.slHyperLoops,loop);
   for(const [j,side] of item.sides.entries()){const p=new LPort;$setNode(p,n);$setSide(p,sides[side]);p.id_0=n.ports.array.length-1;p.pos.x_0=11+i*9+j*3;p.pos.y_0=40-i*2-j*5;p.anchor.x_0=.25+j;p.anchor.y_0=.75-j;const sp=new SelfLoopPort(p);$add_3(loop.slPorts,sp);}
   $computePortsPerSide(loop);loop.leftmostPort=loop.slPorts.array[0];loop.rightmostPort=loop.slPorts.array[loop.slPorts.array.length-1];for(const side of item.occupied)$add_5(loop.occupiedPortSides,sides[side]);
   const labels=new SelfHyperLoopLabels(loop),label=new LLabel;label.size_0.x_0=10+i*2;label.size_0.y_0=4+i;$setProperty_0(label,EDGE_LABELS_INLINE_0,item.inline?true:false);$add_3(labels.lLabels,label);labels.size_0.x_0=label.size_0.x_0;labels.size_0.y_0=label.size_0.y_0;labels.position.x_0=71.5;labels.position.y_0=-31.25;loop.slLabels=labels;
  }
  $placeLabels_1(holder);
  result.push({name:input.name,loops:holder.slHyperLoops.array.map((loop,i)=>({name:input.loops[i].name,type:loop.selfLoopType.name_0,side:loop.slLabels.side.name_0,alignment:loop.slLabels.alignment.name_0,reference:loop.slLabels.alignmentReferenceSLPort?loop.slLabels.alignmentReferenceSLPort.lPort.id_0:null,position:[loop.slLabels.position.x_0,loop.slLabels.position.y_0],inlinePresent:$hasProperty(loop.slLabels.lLabels.array[0],EDGE_LABELS_INLINE_0),inline:$booleanValue(castToBoolean($getProperty(loop.slLabels.lLabels.array[0],EDGE_LABELS_INLINE_0)))}))});
 }
 return result;
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(fs.readFileSync(requestPath)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__labelObservations(request),actualLabelPlacerExecuted:true,preparedNativeModels:true,layoutExecuted:false,nativeExecuted:false},null,2)+'\n',{flag:'wx'});
