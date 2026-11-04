// Source-only intermediate objects and delegated observers; no layout execution.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__localCrossings=function(spec,operation){
 getInstance();$clinit_PortSide();const g=new LGraph,nodes={},ports={},names=new Map,sides={EAST:EAST_2,WEST:WEST_2};
 for(const item of spec.nodes){const n=new LNode(g);nodes[item.id]=n;for(const [id,side]of item.ports){const p=new LPort;$setNode(p,n);$setSide(p,sides[side]);p.id_0=Object.keys(ports).length;ports[id]=p;names.set(p,id);}}
 const order=spec.layers.map((ids,i)=>{const layer=new Layer(g);$add_3(g.layers,layer);return ids.map((id,j)=>{const n=nodes[id];n.id_0=j;$setLayer(n,j,layer);return n;});});
 for(const [a,b]of spec.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}
 const positions=Array(Object.keys(ports).length).fill(0),counter=new CrossingsCounter(positions),ends=counter.ends;
 if(operation==='undefined-side-no-view'){
  const n=new LNode(g),before={cached:!!n.portSidesCached,indices:Object.keys(n.portSideIndices||{})},real=$getPortSideView;let calls=0;
  $getPortSideView=function(...args){calls++;return real(...args);};let values;try{values=inNorthSouthEastWestOrder(n,UNDEFINED_5);}finally{$getPortSideView=real;}
  return {calls,empty:values.isEmpty(),before,after:{cached:!!n.portSidesCached,indices:Object.keys(n.portSideIndices||{})}};
 }
 if(operation==='ports-both-orders')$initForCountingBetween(counter,order[0],order[1]);else $initPortPositionsForInLayerCrossings(counter,order[1],WEST_2);
 const snapshot=()=>Object.entries(ports).map(([id,p])=>({id,value:positions[p.id_0]})),before=snapshot();
 const selected=operation==='ports-both-orders'?$connectedPortsSortedByPosition(counter,ports.a1,ports.a2):$connectedInLayerPortsSortedByPosition(counter,nodes.r,nodes.s,WEST_2);
 const events=[],saved=[$clear_9,$switchPorts,$switchNodes];
 $clear_9=function(...args){events.push('clear');return saved[0](...args);};
 $switchPorts=function(...args){events.push('switchPorts:'+names.get(args[1])+':'+names.get(args[2]));return saved[1](...args);};
 $switchNodes=function(...args){events.push('switchNodes:'+Object.keys(nodes).find(k=>nodes[k]===args[1])+':'+Object.keys(nodes).find(k=>nodes[k]===args[2]));return saved[2](...args);};
 let pair;try{pair=operation==='ports-both-orders'?$countCrossingsBetweenPortsInBothOrders(counter,ports.a1,ports.a2):$countInLayerCrossingsBetweenNodesInBothOrders(counter,nodes.r,nodes.s,WEST_2);}finally{[$clear_9,$switchPorts,$switchNodes]=saved;}
 return {selected:selected.array.map(p=>names.get(p)),before,after:snapshot(),pair:[pair.first,pair.second],events,
  tree:{size:counter.indexTree.size_0,sums:Array.from(counter.indexTree.binarySums),multiplicities:Array.from(counter.indexTree.numsPerIndex)},
  endsIdentity:counter.ends===ends,endsEmpty:$isEmpty(counter.ends),portOrders:Object.entries(nodes).map(([id,n])=>({id,ports:n.ports.array.map(p=>names.get(p))}))};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const spec=JSON.parse(requestRaw),results=spec.cases.map(id=>({id,value:global.__localCrossings(spec,id)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-local-crossings-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
