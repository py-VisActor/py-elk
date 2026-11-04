const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__selfLoopFoundation=function(){
 $clinit_CoreOptions();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_Direction_0();$clinit_SelfHyperLoopLabels$Alignment();
 const arr=list=>{const a=[],i=list.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;},vec=v=>[v.x_0,v.y_0];
 const g=new LGraph,n=new LNode(g),other=new LNode(g);$add_3(g.layerlessNodes,n);$add_3(g.layerlessNodes,other);$setProperty_0(g,DIRECTION,RIGHT_6);$setProperty_0(g,SPACING_LABEL_LABEL,2);
 const ports=[];for(let i=0;i<6;i++){const p=new LPort;p.id_0=20+i;$setNode(p,i===5?other:n);p.side=i%2?EAST_2:WEST_2;ports.push(p);}
 const make=(id,a,b,w,h)=>{const e=new LEdge;e.id_0=id;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);if(w!==undefined){const l=new LLabel;l.id_0=id;l.size_0.x_0=w;l.size_0.y_0=h;$add_3(e.labels,l);}return e;};
 const e0=make(10,0,1,8,4),e1=make(11,1,2,10,3),e2=make(12,3,4,6,5),non=make(13,0,5),holder=new SelfLoopHolder(n);$initialize_3(holder);
 const views=arr((new AbstractMap$2(holder.slPorts)).this$01.entrySet_0());
 const sourcePorts=views.map(entry=>entry.getValue()),names=new Map(ports.map((p,i)=>[p,i]));
 const loops=holder.slHyperLoops.array.map(loop=>{const labels=loop.slLabels;labels.position.x_0=5;labels.position.y_0=6;labels.alignment=CENTER_2;labels.side=NORTH_3;$applyPlacement(labels,new KVector_1(2,3));return {ports:loop.slPorts.array.map(p=>names.get(p.lPort)),edges:arr(loop.slEdges).map(e=>e.lEdge.id_0),edgeLoopSame:arr(loop.slEdges).every(e=>e.slHyperLoop===loop),labels:{ids:labels.lLabels.array.map(l=>l.id_0),size:vec(labels.size_0),positions:labels.lLabels.array.map(l=>vec(l.pos))}};});
 return {holder:{ports:sourcePorts.map(p=>({port:names.get(p.lPort),id:p.lPort.id_0,incoming:p.incomingSLEdges.array.map(e=>e.lEdge.id_0),outgoing:p.outgoingSLEdges.array.map(e=>e.lEdge.id_0),hadOnlySelfLoops:p.hadOnlySelfLoops,isHidden:p.isHidden})),loops,routingSlots:Array.from(holder.routingSlotCount),portsHidden:holder.arePortsHidden,nodeSame:holder.lNode===n},nonSelfUnchanged:non.source===ports[0]&&non.target===ports[5],nodePortOrder:n.ports.array.map(p=>names.get(p)),needs:[needsSelfLoopProcessing(n),needsSelfLoopProcessing(other)]};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__selfLoopFoundation(),preparedViews:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
