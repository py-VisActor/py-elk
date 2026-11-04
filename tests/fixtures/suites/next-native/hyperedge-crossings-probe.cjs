// Real HyperedgeCrossingsCounter; array observation delegates the source call.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__hyperCrossings=function(s){
 getInstance();$clinit_PortSide();const g=new LGraph,nodes={},ports={},names=new Map,edges=[],sides={NORTH:NORTH_3,EAST:EAST_2,WEST:WEST_2};
 for(const item of s.nodes){const n=new LNode(g);nodes[item.id]=n;for(const [id,side]of item.ports){const p=new LPort;$setNode(p,n);$setSide(p,sides[side]);p.id_0=Object.keys(ports).length;ports[id]=p;names.set(p,id);}}
 const order=s.layers.map((ids,i)=>{const layer=new Layer(g);$add_3(g.layers,layer);layer.id_0=i;return ids.map((id,j)=>{const n=nodes[id];n.id_0=j;$setLayer(n,j,layer);return n;});});
 for(const [a,b]of s.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);edges.push(e);}
 const positions=Array(Object.keys(ports).length).fill(17),counter=new HyperedgeCrossingsCounter(positions),original=$toArray_0;let observed=[];
 $toArray_0=function(owner,array){const result=original(owner,array);if(result.length&&instanceOf(result[0],485))observed=result.slice();return result;};
 let count;try{count=$countCrossings_1(counter,order[0],order[1]);}finally{$toArray_0=original;}
 return {count,positions:Object.entries(ports).map(([id,p])=>({id,value:positions[p.id_0]})),positionBufferShared:counter.portPos===positions,bundles:observed.map(he=>({ports:he.ports.array.map(p=>names.get(p)),edges:he.edges.array.map(e=>edges.indexOf(e)),bounds:[he.upperLeft,he.lowerLeft,he.upperRight,he.lowerRight]})),observerDelegated:true,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__hyperCrossings(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-hyperedge-crossings-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
