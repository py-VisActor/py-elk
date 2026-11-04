// Supplied intermediate graph/strategy facts, real TypeDecider operations.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__sweepType=function(s){
 getInstance();$clinit_PortSide();$clinit_LNode$NodeType();$clinit_InternalProperties_1();$clinit_LayeredOptions();
 const g=new LGraph,outer=new LGraph,parent=new LNode(outer),nodes={},ports={},sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2},types={NORMAL,NORTH_SOUTH_PORT,EXTERNAL_PORT};
 for(const id of ['pe0','pe1','pw0','pw1']){const p=new LPort;$setNode(p,parent);$setSide(p,id[1]==='e'?EAST_2:WEST_2);ports[id]=p;}
 for(const item of s.nodes){const n=new LNode(g);n.type_0=types[item.type];nodes[item.id]=n;for(const [id,side]of item.ports){const p=new LPort;$setNode(p,n);$setSide(p,sides[side]);ports[id]=p;}}
 for(const item of s.nodes)if(item.origin)$setProperty_0(nodes[item.id],ORIGIN_0,ports[item.origin]);
 const order=s.layers.map(ids=>{const layer=new Layer(g);$add_3(g.layers,layer);return ids.map((id,j)=>{const n=nodes[id];$setLayer(n,j,layer);return n;});});
 const edges=[...s.edges];if(s.repeatEdge)for(let i=0;i<s.repeatEdge.count;i++)edges.push([s.repeatEdge.source,s.repeatEdge.target]);
 for(const [a,b]of edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}
 for(const [p,d]of s.portDummies)$setProperty_0(ports[p],PORT_DUMMY,nodes[d]);
 $setProperty_0(g,CROSSING_MINIMIZATION_HIERARCHICAL_SWEEPINESS_0,s.boundary);
 let deterministicCalls=0;const data={lGraph:g,parent_0:parent,hasParent:true,currentNodeOrder:order,crossMinimizer:{isDeterministic(){deterministicCalls++;return false;}}};
 const decider=new LayerSweepTypeDecider(data);
 for(let l=0;l<order.length;l++){decider.initAtLayerLevel(l,order);for(let n=0;n<order[l].length;n++)decider.initAtNodeLevel(l,n,order);}
 const decision=$useBottomUp(decider);
 return {decision,deterministicCalls,info:s.layers.map(ids=>ids.map(id=>{const node=nodes[id],i=decider.nodeInfo[node.layer.id_0][node.id_0];return {id,connected:i.connectedEdges,hierarchical:i.hierarchicalInfluence,random:i.randomInfluence};})),layoutExecuted:false,suppliedStrategyFact:'non-deterministic'};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const spec=JSON.parse(requestRaw),results=spec.cases.map(s=>({id:s.id,value:global.__sweepType(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-sweep-type-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
