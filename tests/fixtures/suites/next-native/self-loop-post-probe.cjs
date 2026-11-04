const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__selfLoopPost=function(){
 $clinit_CoreOptions();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_Direction_0();$clinit_SelfHyperLoopLabels$Alignment();
 const arr=list=>{const a=[],i=list.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;},vec=v=>[v.x_0,v.y_0];
 const g=new LGraph,layer=new Layer(g);$add_3(g.layers,layer);$setProperty_0(g,DIRECTION,RIGHT_6);const n=new LNode(g),other=new LNode(g);$setLayer(n,0,layer);$setLayer(other,1,layer);n.pos.x_0=11;n.pos.y_0=17;
 const p=new LPort,q=new LPort,t=new LPort;$setNode(p,n);$setNode(q,n);$setNode(t,other);p.side=NORTH_3;q.side=NORTH_3;
 const edge=new LEdge;edge.id_0=7;$setSource_0(edge,p);$setTarget_0(edge,q);$add_7(edge.bendPoints,new KVector_1(-8,-4));$add_7(edge.bendPoints,new KVector_1(30,-4));
 const label=new LLabel;label.pos.x_0=999;label.pos.y_0=888;label.size_0.x_0=12;label.size_0.y_0=5;$add_3(edge.labels,label);
 const otherEdge=new LEdge;otherEdge.id_0=8;$setSource_0(otherEdge,p);$setTarget_0(otherEdge,t);const holder=new SelfLoopHolder(n);$initialize_3(holder);$setProperty_0(n,SELF_LOOP_HOLDER,holder);const loop=holder.slHyperLoops.array[0];loop.slLabels.position.x_0=2;loop.slLabels.position.y_0=-9;loop.slLabels.alignment=LEFT_1;loop.slLabels.side=NORTH_3;
 const before=p.outgoingEdges.array.map(e=>e.id_0),monitor=new BasicProgressMonitor;$process_48(g,monitor);
 return {before,outgoing:p.outgoingEdges.array.map(e=>e.id_0),incoming:q.incomingEdges.array.map(e=>e.id_0),sameEndpoints:edge.source===p&&edge.target===q,bends:edge.bendPoints.toArray().map(vec),label:vec(label.pos),holderSame:$getProperty(n,SELF_LOOP_HOLDER)===holder,portsHidden:holder.arePortsHidden,loopCount:holder.slHyperLoops.array.length,nodePosition:vec(n.pos),monitorRunning:monitor.isRunning(),otherUnchanged:otherEdge.source===p&&otherEdge.target===t};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__selfLoopPost(),preparedRoutedDto:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
