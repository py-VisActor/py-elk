// One original working-graph witness: real targets, both comparators and costs.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__modelOrderCost=function(s){
 getInstance();$clinit_PortSide();$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_OrderingStrategy();$clinit_LayerSweepCrossingMinimizer$CrossMinType();
 const g=new LGraph,nodes={},ports={},nodeIds=new Map;
 for(const item of s.nodes){const n=new LNode(g);nodes[item.id]=n;nodeIds.set(n,item.id);$setProperty_0(n,MODEL_ORDER_2,valueOf_3(item.modelOrder));
  for(const [id,side,order] of item.ports){const p=new LPort;ports[id]=p;$setNode(p,n);$setSide(p,side==='EAST'?EAST_2:WEST_2);$setProperty_0(p,MODEL_ORDER_2,valueOf_3(order));}}
 s.layers.forEach((ids,i)=>{const layer=new Layer(g);layer.id_0=i;$add_3(g.layers,layer);ids.forEach((id,j)=>$setLayer(nodes[id],j,layer));});
 s.edges.forEach(([a,b,order])=>{const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);$setProperty_0(e,MODEL_ORDER_2,valueOf_3(order));});
 const strategy=PREFER_NODES;$setProperty_0(g,MAX_MODEL_ORDER_NODES,valueOf_3(s.nodes.length));$setProperty_0(g,RANDOM_0,new Random_0(s.seed));$setProperty_0(g,CONSIDER_MODEL_ORDER_STRATEGY_0,strategy);$setProperty_0(g,CONSIDER_MODEL_ORDER_PORT_MODEL_ORDER_0,true);
 $setProperty_0(g,CONSIDER_MODEL_ORDER_CROSSING_COUNTER_NODE_INFLUENCE_0,s.nodeInfluence);$setProperty_0(g,CONSIDER_MODEL_ORDER_CROSSING_COUNTER_PORT_INFLUENCE_0,s.portInfluence);
 const controller=new LayerSweepCrossingMinimizer(BARYCENTER),holders=new ArrayList,data=new GraphInfoHolder(g,BARYCENTER,holders);$add_3(holders,data);controller.graphInfoHolders=holders;
 const nodeCost=$countModelOrderNodeChanges(g,data.currentNodeOrder,strategy),portCost=$countModelOrderPortChanges(g,data.currentNodeOrder),events=[],saved=[$countModelOrderNodeChanges,$countModelOrderPortChanges,$countAllCrossings];
 $countModelOrderNodeChanges=function(...args){events.push('node-cost');return saved[0](...args);};$countModelOrderPortChanges=function(...args){events.push('port-cost');return saved[1](...args);};$countAllCrossings=function(...args){events.push('all');return saved[2](...args);};
 let score;try{score=$countCurrentNumberOfCrossingsNodePortOrder(controller,data);}finally{[$countModelOrderNodeChanges,$countModelOrderPortChanges,$countAllCrossings]=saved;}
 const pc=new ModelOrderPortComparator_0(g,data.currentNodeOrder[0],strategy,null,false),selfResults=[$compare_19(pc,ports[s.selfPort],ports[s.selfPort]),$compare_19(pc,ports[s.selfPort],ports[s.selfPort])];
 const targets=s.nodes.map(item=>{const n=nodes[item.id],map=longEdgeTargetNodePreprocessing(n);return {id:item.id,memoIdentity:map===longEdgeTargetNodePreprocessing(n),values:s.nodes.map(t=>$containsKey_3(map,nodes[t.id])?$get_10(map,nodes[t.id]).value_0:null)};});
 const portTargets=Object.entries(ports).map(([id,p])=>[id,$hasProperty(p,LONG_EDGE_TARGET_NODE)?nodeIds.get($getProperty(p,LONG_EDGE_TARGET_NODE)):null]);
 return {nodeCost,portCost,score,events,selfResults,selfCache:$contains_6($get_10(pc.biggerThan,ports[s.selfPort]),ports[s.selfPort]),targets,portTargets,nodeOrder:data.currentNodeOrder.map(row=>row.map(n=>nodeIds.get(n))),layoutExecuted:false,suppliedInternalModelOrder:true};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__modelOrderCost(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-model-order-cost-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
