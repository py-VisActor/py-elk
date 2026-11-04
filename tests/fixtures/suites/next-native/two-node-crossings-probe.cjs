const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__twoNode=function(s){
 getInstance();$clinit_PortSide();const g=new LGraph,nodes={},ports={};
 for(const [id,ps] of s.nodes){const n=nodes[id]=new LNode(g);for(const [pid,side]of ps){const p=ports[pid]=new LPort;$setNode(p,n);$setSide(p,side==='EAST'?EAST_2:WEST_2);}}
 const order=s.layers.map((ids,i)=>{const l=new Layer(g);$add_3(g.layers,l);l.id_0=i;return ids.map((id,j)=>{const n=nodes[id];$setLayer(n,j,l);return n;});});
 function edge(a,b){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}s.edges.forEach(args=>edge(...args));
 const c=new BetweenLayerEdgeTwoNodeCrossingsCounter(order,s.freeLayer),events=[];
 function state(map){return s.layers[s.freeLayer].map(id=>{const n=nodes[id];if(!$containsKey_3(map,n))return {id,present:false};const a=$get_10(map,n);return {id,present:true,size:a.size_0,currentSize:a.currentSize,index:a.currentIndex,entries:a.adjacencyList.array.map(x=>[x.position,x.cardinality,x.currentCardinality])};});}
 let cacheIdentity=true,saved=null;
 s.queries.forEach(([side,a,b],i)=>{if(side==='BOTH')$countBothSideCrossings(c,nodes[a],nodes[b]);else $countEasternEdgeCrossings(c,nodes[a],nodes[b]);events.push({counts:[c.upperLowerCrossings,c.lowerUpperCrossings],east:state(c.easternAdjacencies),west:state(c.westernAdjacencies)});if(i===s.lateEdgeAfter){saved=$get_10(c.easternAdjacencies,nodes.w);edge(...s.lateEdge);}else if(saved)cacheIdentity=cacheIdentity&&saved===$get_10(c.easternAdjacencies,nodes.w);});
 return {positions:Object.entries(ports).filter(([id,p])=>$containsKey_3(c.portPositions,p)).map(([id,p])=>[id,$get_10(c.portPositions,p).value_0]),events,cacheIdentity,orderIdentity:c.currentNodeOrder===order,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__twoNode(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-two-node-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
