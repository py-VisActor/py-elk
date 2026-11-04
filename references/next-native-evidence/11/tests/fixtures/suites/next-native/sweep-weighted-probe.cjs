// Real weighted NONE score reads and real AllCounter; no cost callback stub.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__weightedScore=function(s){
 getInstance();$clinit_PortSide();$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_OrderingStrategy();$clinit_LayerSweepCrossingMinimizer$CrossMinType();
 const g=new LGraph,nodes={},ports={};for(const item of s.nodes){const n=new LNode(g),p=new LPort;nodes[item.id]=n;ports[item.port]=p;$setNode(p,n);$setSide(p,item.side==='EAST'?EAST_2:WEST_2);}
 s.layers.forEach(ids=>{const layer=new Layer(g);$add_3(g.layers,layer);ids.forEach((id,j)=>$setLayer(nodes[id],j,layer));});
 s.edges.forEach(([a,b])=>{const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);});
 const rng=new Random_0(s.seed);$setProperty_0(g,RANDOM_0,rng);$setProperty_0(g,CONSIDER_MODEL_ORDER_STRATEGY_0,NONE_11);$setProperty_0(g,CONSIDER_MODEL_ORDER_CROSSING_COUNTER_NODE_INFLUENCE_0,s.nodeInfluence);$setProperty_0(g,CONSIDER_MODEL_ORDER_CROSSING_COUNTER_PORT_INFLUENCE_0,s.portInfluence);
 const controller=new LayerSweepCrossingMinimizer(BARYCENTER),holders=new ArrayList,data=new GraphInfoHolder(g,BARYCENTER,holders);$add_3(holders,data);controller.graphInfoHolders=holders;
 const tracked=new Map([[CONSIDER_MODEL_ORDER_STRATEGY_0,'strategy'],[CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CM_GROUP_ORDER_STRATEGY_0,'group'],[CONSIDER_MODEL_ORDER_CROSSING_COUNTER_NODE_INFLUENCE_0,'node'],[CONSIDER_MODEL_ORDER_CROSSING_COUNTER_PORT_INFLUENCE_0,'port']]),events=[],saved=[$getProperty,$countAllCrossings],counter=data.crossingsCounter.crossingCounter,beforeAbsent=counter.indexTree==null;
 $getProperty=function(...args){if(args[0]===g&&tracked.has(args[1]))events.push('read:'+tracked.get(args[1]));return saved[0](...args);};
 $countAllCrossings=function(...args){events.push('all');return saved[1](...args);};let score;try{score=$countCurrentNumberOfCrossingsNodePortOrder(controller,data);}finally{[$getProperty,$countAllCrossings]=saved;}
 return {score,events,beforeTreeAbsent:beforeAbsent,afterTreePresent:counter.indexTree!=null,positions:Array.from(counter.portPositions),layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__weightedScore(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-sweep-weighted-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
