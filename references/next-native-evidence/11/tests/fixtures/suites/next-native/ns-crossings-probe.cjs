// Actual NS position/weighted score with observer-only init/add wrappers.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__nsCrossings=function(s){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_PortSide();$clinit_LNode$NodeType();
 const g=new LGraph,layer=new Layer(g);$add_3(g.layers,layer);layer.id_0=0;
 const nodes={},ports={},names=new Map,sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2},types={NORMAL,LONG_EDGE,NORTH_SOUTH_PORT,LABEL};
 for(const spec of s.nodes){const n=new LNode(g);n.type_0=types[spec.type];nodes[spec.id]=n;for(const[id,side]of spec.ports){const p=new LPort;$setNode(p,n);$setSide(p,sides[side]);p.id_0=Object.keys(ports).length;ports[id]=p;names.set(p,id);}}
 const order=s.order.map((id,i)=>{const n=nodes[id];n.id_0=i;$setLayer(n,i,layer);return n;});
 for(const spec of s.nodes)if(spec.unit)$setProperty_0(nodes[spec.id],IN_LAYER_LAYOUT_UNIT,nodes[spec.unit]);
 for(const[id,node]of Object.entries(s.dummies))$setProperty_0(ports[id],PORT_DUMMY,nodes[node]);
 for(const[id,port]of Object.entries(s.origins))$setProperty_0(ports[id],ORIGIN_0,ports[port]);
 for(const[a,b]of s.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}
 const positions=Array(Object.keys(ports).length).fill(-1),counter=new CrossingsCounter(positions),ends=counter.ends,adds=[];let constructed=[];
 const init=$initPositionsForNorthSouthCounting,add=$add_16;
 $initPositionsForNorthSouthCounting=function(c,nodes){const result=init(c,nodes);constructed=result.array.map(p=>names.get(p));return result;};
 $add_16=function(tree,index){adds.push(index);return add(tree,index);};
 let count;try{count=$countNorthSouthPortCrossingsInLayer(counter,order);}finally{$initPositionsForNorthSouthCounting=init;$add_16=add;}
 return {count,constructedPortOrder:constructed,positions:Object.entries(ports).map(([id,p])=>({id,value:positions[p.id_0]})),queuedEndpointAddOrder:adds,endsIdentityPreserved:counter.ends===ends,endsEmpty:$isEmpty(counter.ends),tree:{size:counter.indexTree.size_0,sums:Array.from(counter.indexTree.binarySums),multiplicities:Array.from(counter.indexTree.numsPerIndex)},cacheFlags:Object.entries(nodes).map(([id,n])=>({id,cached:!!n.portSidesCached})),observerOnlyWrappers:true,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__nsCrossings(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-ns-crossings-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
