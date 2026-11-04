// Real source BIT/basic counters with supplied intermediate layered objects.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__basicCrossings=function(spec,s){
 if(s.operation==='bit'){
  const tree=new BinaryIndexedTree(s.max),states=[],snapshot=()=>({size:tree.size_0,sums:Array.from(tree.binarySums),multiplicities:Array.from(tree.numsPerIndex)});let clearFresh=null;
  for(const [op,index]of s.steps){let returned=null;if(op==='add')$add_16(tree,index);else if(op==='remove')$removeAll_3(tree,index);else if(op==='rank')returned=$rank(tree,index);else{const sums=tree.binarySums,nums=tree.numsPerIndex;$clear_9(tree);clearFresh={sums:sums!==tree.binarySums,multiplicities:nums!==tree.numsPerIndex};}states.push({operation:op,index:index??null,returned,state:snapshot()});}
  return {states,clearFresh,layoutExecuted:false};
 }
 getInstance();$clinit_PortSide();const g=new LGraph,nodes={},ports={},names=new Map,sides={EAST:EAST_2,WEST:WEST_2};
 for(const item of spec.nodes){const n=new LNode(g);nodes[item.id]=n;for(const [id,side]of item.ports){const p=new LPort;$setNode(p,n);$setSide(p,sides[side]);p.id_0=Object.keys(ports).length;ports[id]=p;names.set(p,id);}}
 const order=spec.layers.map((ids,i)=>{const layer=new Layer(g);$add_3(g.layers,layer);layer.id_0=i;return ids.map((id,j)=>{const n=nodes[id];n.id_0=j;$setLayer(n,j,layer);return n;});});
 for(const [a,b]of spec.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}
 const positions=Array(Object.keys(ports).length).fill(-1),counter=new CrossingsCounter(positions),ends=counter.ends;
 const count=s.operation==='between'?$countCrossingsBetweenLayers(counter,order[0],order[1]):$countInLayerCrossingsOnSide(counter,order[1],WEST_2);
 return {count,positions:Object.entries(ports).map(([id,p])=>({id,value:positions[p.id_0]})),positionBufferShared:counter.portPositions===positions,endsIdentityPreserved:counter.ends===ends,endsEmpty:$isEmpty(counter.ends),cardinalities:counter.nodeCardinalities?Array.from(counter.nodeCardinalities):null,tree:{size:counter.indexTree.size_0,sums:Array.from(counter.indexTree.binarySums),multiplicities:Array.from(counter.indexTree.numsPerIndex)},nodes:Object.entries(nodes).map(([id,n])=>({id,cached:!!n.portSidesCached,ports:n.ports.array.map(p=>names.get(p))})),layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const spec=JSON.parse(requestRaw),results=spec.cases.map(s=>({id:s.id,value:global.__basicCrossings(spec,s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-basic-crossings-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
