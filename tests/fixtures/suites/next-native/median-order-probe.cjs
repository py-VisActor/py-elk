const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__medianOrder=function(s){
 getInstance();$clinit_PortSide();$clinit_InternalProperties_1();
 const g=new LGraph,nodes={},names=new Map;for(const id of s.nodes){const n=nodes[id]=new LNode(g);names.set(n,id);}
 const order=s.layers.map((ids,i)=>{const l=new Layer(g);l.id_0=i;$add_3(g.layers,l);ids.forEach((id,j)=>$setLayer(nodes[id],j,l));return ids.map(id=>nodes[id]);});
 for(const [a,b] of s.edges){const p=new LPort,q=new LPort,e=new LEdge;$setNode(p,nodes[a]);$setSide(p,EAST_2);$setNode(q,nodes[b]);$setSide(q,WEST_2);$setSource_0(e,p);$setTarget_0(e,q);}
 const rng=new Random_0(s.seed),before=[rng.seedhi,rng.seedlo],hostOriginal=$wnd.Math.random;let hostDraws=0,heuristic;
 $wnd.Math.random=function(){hostDraws++;return hostOriginal();};try{heuristic=new MedianHeuristic(rng);}finally{$wnd.Math.random=hostOriginal;}
 const afterConstructor=[rng.seedhi,rng.seedlo],missingSelf=lambda$0_32(nodes.isolated,nodes.isolated),missingPair=lambda$0_32(nodes.u,nodes.v),row0=order[0],row1=order[1];
 const firstResult=heuristic.setFirstLayerOrder(order,true),afterFirst=order.map(row=>row.map(n=>names.get(n))),firstWeights=s.nodes.map(id=>$hasProperty(nodes[id],WEIGHT)?$getProperty(nodes[id],WEIGHT):null);
 const secondResult=heuristic.minimizeCrossings(order,1,true,false);
 return {hostDraws,seedBefore:before,seedAfterConstructor:afterConstructor,seedAfter:[rng.seedhi,rng.seedlo],missingSelf,missingPair,firstResult,secondResult,afterFirst,firstWeights,order:order.map(row=>row.map(n=>names.get(n))),weights:s.nodes.map(id=>$hasProperty(nodes[id],WEIGHT)?$getProperty(nodes[id],WEIGHT):null),sameRows:order[0]===row0&&order[1]===row1,deterministic:heuristic.isDeterministic(),alwaysImproves:heuristic.alwaysImproves(),layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__medianOrder(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-median-order-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
