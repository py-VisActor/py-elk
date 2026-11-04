// Real traversal/dispatch on new intermediate objects; observers delegate.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__allCrossings=function(s){
 getInstance();$clinit_PortSide();$clinit_LNode$NodeType();const g=new LGraph,nodes={},ports={},edges=[],sides={EAST:EAST_2,WEST:WEST_2};
 for(const item of s.nodes){const n=new LNode(g);nodes[item.id]=n;if(item.type==='NORTH_SOUTH_PORT')n.type_0=NORTH_SOUTH_PORT;for(const [id,side]of item.ports){const p=new LPort;$setNode(p,n);$setSide(p,sides[side]);ports[id]=p;}}
 const order=s.layers.map((ids,i)=>{const layer=new Layer(g);$add_3(g.layers,layer);layer.id_0=i;return ids.map((id,j)=>{const n=nodes[id];$setLayer(n,j,layer);return n;});});
 for(const [a,b]of s.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);edges.push(e);}
 const counters=[new AllCrossingsCounter(order),new AllCrossingsCounter(order)],before=counters.map(c=>({ns:Array.from(c.hasNorthSouthPorts),hyper:Array.from(c.hasHyperEdgesEastOfIndex),inLayer:Array.from(c.inLayerEdgeCounts),ports:c.nPorts})),events=[];
 counters.forEach((c,index)=>{const real=c.initAtEdgeLevel;c.initAtEdgeLevel=function(l,n,p,e,edge,all){events.push([index,l,n,p,e,edges.indexOf(edge)]);return real.call(this,l,n,p,e,edge,all);};});
 const receivers=new ArrayList;counters.forEach(c=>$add_3(receivers,c));init_0(receivers,order);
 const after=counters.map(c=>({ns:Array.from(c.hasNorthSouthPorts),hyper:Array.from(c.hasHyperEdgesEastOfIndex),inLayer:Array.from(c.inLayerEdgeCounts),ports:c.nPorts}));
 const calls=[],saved=[$countInLayerCrossingsOnSide,$countCrossings_1,$countNorthSouthPortCrossingsInLayer];
 $countInLayerCrossingsOnSide=function(...args){calls.push('inLayer:'+args[2].name_0);return saved[0](...args);};
 $countCrossings_1=function(...args){calls.push('hyper');return saved[1](...args);};
 $countNorthSouthPortCrossingsInLayer=function(...args){calls.push('northSouth');return saved[2](...args);};
 let count;try{count=$countAllCrossings(counters[0],order);}finally{[$countInLayerCrossingsOnSide,$countCrossings_1,$countNorthSouthPortCrossingsInLayer]=saved;}
 return {before,after,events,calls,count,portIds:Object.entries(ports).map(([id,p])=>({id,value:p.id_0})),sharedBuffers:counters.map(c=>c.crossingCounter.portPositions===c.hyperedgeCrossingsCounter.portPos),layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__allCrossings(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-all-crossings-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
