const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__portSides=function(){
 $clinit_CoreOptions();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_SelfLoopDistributionStrategy();
 const arr=list=>{const a=[],i=list.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;},result=[];
 for(const distribution of[EQUALLY,NORTH_2,NORTH_SOUTH]){
   const g=new LGraph,n=new LNode(g),other=new LNode(g),names=new Map,all=[];$add_3(g.layerlessNodes,n);$add_3(g.layerlessNodes,other);$setProperty_0(n,PORT_CONSTRAINTS_0,($clinit_PortConstraints(),FREE));$setProperty_0(n,EDGE_ROUTING_SELF_LOOP_DISTRIBUTION_0,distribution);
   let eid=0;
   for(let i=0;i<8;i++){
     const count=[3,2,5,2,4,3,4,2][i],ps=[];
     for(let j=0;j<count;j++){const p=new LPort;$setNode(p,n);p.side=WEST_2;p.size_0.x_0=4+j;p.size_0.y_0=6+j;if(j===count-1){p.explicitlySuppliedPortAnchor=true;p.anchor.x_0=9;p.anchor.y_0=8;}names.set(p,i+'.'+j);ps.push(p);all.push(p);}
     for(let j=0;j<count-1;j++){const e=new LEdge;e.id_0=eid++;$setSource_0(e,ps[j]);$setTarget_0(e,ps[j+1]);}
     // Real non-self incidence makes one source port remain visible.
     if(i%2===0){const t=new LPort;$setNode(t,other);const e=new LEdge;e.id_0=eid++;$setSource_0(e,ps[0]);$setTarget_0(e,t);}
   }
   $process_49(g,new BasicProgressMonitor);const holder=$getProperty(n,SELF_LOOP_HOLDER),before=holder.slHyperLoops.array.map(l=>l.slPorts.array.map(p=>names.get(p.lPort)));$assignPortSides(holder);
   result.push({strategy:distribution.name_0,before,after:holder.slHyperLoops.array.map(l=>l.slPorts.array.map(p=>names.get(p.lPort))),ports:all.map(p=>({name:names.get(p),side:p.side.name_0,anchor:[p.anchor.x_0,p.anchor.y_0],ownerPresent:!!p.owner})),visible:n.ports.array.map(p=>names.get(p)),hidden:arr((new AbstractMap$2(holder.slPorts)).this$01.entrySet_0()).map(e=>({name:names.get(e.getKey()),hidden:e.getValue().isHidden}))});
 }
 return result;
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__portSides(),actualPreprocessAndAssigner:true,layoutExecuted:false,nativeExecuted:false},null,2)+'\n',{flag:'wx'});
