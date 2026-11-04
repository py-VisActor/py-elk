// Real nested TwoNode costs cause live WEST-view parent port swaps.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__greedyPorts=function(s){
 getInstance();$clinit_PortSide();$clinit_InternalProperties_1();$clinit_LNode$NodeType();
 const graph=new LGraph,parent=new LNode(graph),layer=new Layer(graph);$add_3(graph.layers,layer);$setLayer(parent,0,layer);
 const ports={},names=new Map;for(const id of s.parentPorts){const p=ports[id]=new LPort;$setNode(p,parent);$setSide(p,WEST_2);names.set(p,id);}
 const inner=new LGraph,nodes={},endpoints={};parent.nestedGraph=inner;inner.parentNode=parent;
 s.innerLayers.forEach((ids,i)=>{const l=new Layer(inner);l.id_0=i;$add_3(inner.layers,l);ids.forEach((id,j)=>{const n=nodes[id]=new LNode(inner);if(i===0)$setType(n,EXTERNAL_PORT);$setLayer(n,j,l);const p=endpoints[id]=new LPort;$setNode(p,n);$setSide(p,i===0?EAST_2:WEST_2);});});
 s.innerEdges.forEach(([a,b])=>{const e=new LEdge;$setSource_0(e,endpoints[a]);$setTarget_0(e,endpoints[b]);});
 s.dummyForPort.forEach(([p,n])=>$setProperty_0(ports[p],PORT_DUMMY,nodes[n]));
 const order=[[parent]],all=new AllCrossingsCounter(order),distributor=new GreedyPortDistributor,receivers=new ArrayList;$add_3(receivers,all);$add_3(receivers,distributor);init_0(receivers,order);
 const before=parent.ports.array.map(p=>names.get(p)),events=[],saved=[$countCrossingsBetweenPortsInBothOrders,$countBothSideCrossings,$switchPorts];
 $countCrossingsBetweenPortsInBothOrders=function(...args){const out=saved[0](...args);events.push(['local',names.get(args[1]),names.get(args[2]),out.first.value_0,out.second.value_0]);return out;};
 $countBothSideCrossings=function(...args){const out=saved[1](...args);events.push(['hierarchy',args[0].upperLowerCrossings,args[0].lowerUpperCrossings]);return out;};
 $switchPorts=function(...args){events.push(['switch',names.get(args[1]),names.get(args[2])]);return saved[2](...args);};
 let improved;try{improved=distributor.distributePortsWhileSweeping(order,0,s.forward);}finally{[$countCrossingsBetweenPortsInBothOrders,$countBothSideCrossings,$switchPorts]=saved;}
 return {before,after:parent.ports.array.map(p=>names.get(p)),improved,events,nPorts:distributor.nPorts,sharedSlots:distributor.crossingsCounter.portPositions===distributor.portPos,positions:s.parentPorts.map(id=>distributor.portPos[ports[id].id_0]),cacheFlag:parent.portSidesCached,hierarchicalPresent:distributor.hierarchicalCrossingsCounter!=null,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__greedyPorts(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-greedy-ports-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
