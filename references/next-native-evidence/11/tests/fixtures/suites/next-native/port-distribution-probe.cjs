// Real rank producer plus real source port distribution, no supplied ranks.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__portDistribution=function(spec,s){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_PortSide();$clinit_PortType();
 const graph=new LGraph,nodes={},ports={},names=new Map,portNames=new Map,side={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2};
 const layers=spec.layers.map((ids,i)=>{const l=new Layer(graph);l.id_0=i;return l;});
 for(const item of spec.nodes){const n=new LNode(graph);nodes[item.id]=n;names.set(n,item.id);for(const [id,s] of item.ports){const p=new LPort;$setNode(p,n);$setSide(p,side[s]);ports[id]=p;portNames.set(p,id);}}
 const order=spec.layers.map((ids,i)=>ids.map((name,n)=>{const node=nodes[name];$setLayer(node,n,layers[i]);return node;}));
 for(const [a,b] of spec.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}
 $setProperty_0(ports[spec.dummy.port],PORT_DUMMY,nodes[spec.dummy.node]);for(const id of spec.dummy.originPorts)$setProperty_0(ports[id],ORIGIN_0,ports[spec.dummy.port]);
 const d=s.kind==='NodeRelative'?new NodeRelativePortDistributor(order.length):new LayerTotalPortDistributor(order.length);
 order.forEach((layer,l)=>{d.initAtLayerLevel(l,order);layer.forEach((node,n)=>{d.initAtNodeLevel(l,n,order);node.ports.array.forEach((_,p)=>d.initAtPortLevel(l,n,p,order));});});d.initAfterTraversal();
 for(const [id,value] of Object.entries(spec.oldBarycenters))d.portBarycenter[ports[id].id_0]=value;
 const snapshot=()=>({ranks:Object.entries(ports).map(([id,p])=>({id,value:d.portRanks[p.id_0]})),barycenters:Object.entries(ports).map(([id,p])=>({id,value:d.portBarycenter[p.id_0]})),portOrder:Object.entries(nodes).map(([id,n])=>({id,ports:n.ports.array.map(p=>portNames.get(p))})),positions:d.nodePositions.map(a=>Array.from(a)),min:d.minBarycenter,max:d.maxBarycenter});
 const stages=[snapshot()];let returned=null;
 if(s.operation==='rank'){$calculatePortRanks(d,order[1],INPUT);stages.push(snapshot());$calculatePortRanks(d,order[0],OUTPUT);stages.push(snapshot());$calculatePortRanks(d,order[1],INPUT);stages.push(snapshot());}
 else{returned=d.distributePortsWhileSweeping(order,1,true);stages.push(snapshot());}
 return{stages,returned,rankProducerExecuted:true,fullLayoutValidated:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const spec=JSON.parse(requestRaw),results=spec.cases.map(s=>({id:s.id,value:global.__portDistribution(spec,s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-port-distribution-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
