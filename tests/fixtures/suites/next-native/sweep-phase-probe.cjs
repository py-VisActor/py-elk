// A full original crossing phase on supplied intermediate layered graph.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__sweepPhase=function(s){
 getInstance();$clinit_PortSide();$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_LayerSweepCrossingMinimizer$CrossMinType();
 const g=new LGraph,nodes={},ports={},names=new Map,portNames=new Map,sides={EAST:EAST_2,WEST:WEST_2};
 for(const item of s.nodes){const n=new LNode(g);nodes[item.id]=n;names.set(n,item.id);for(const [id,side]of item.ports){const p=new LPort;$setNode(p,n);$setSide(p,sides[side]);ports[id]=p;portNames.set(p,id);}}
 const layers=s.layers.map(ids=>{const layer=new Layer(g);$add_3(g.layers,layer);ids.forEach((id,j)=>$setLayer(nodes[id],j,layer));return layer;});
 for(const [a,b]of s.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}
 const rng=new Random_0(s.seed);$setProperty_0(g,RANDOM_0,rng);$setProperty_0(g,THOROUGHNESS_0,valueOf_3(s.thoroughness));
 const controller=new LayerSweepCrossingMinimizer(BARYCENTER),monitor=new BasicProgressMonitor,bits=[],counts=[],sweeps=[];
 const saved=[$nextInternal,$countAllCrossings,$sweepReducingCrossings];
 $nextInternal=function(random,b){bits.push(b);return saved[0](random,b);};
 $countAllCrossings=function(...args){const returned=saved[1](...args);counts.push(returned);return returned;};
 $sweepReducingCrossings=function(...args){const returned=saved[2](...args);sweeps.push({forward:args[2],first:args[3],returned});return returned;};
 try{$process_76(controller,g,monitor);}finally{[$nextInternal,$countAllCrossings,$sweepReducingCrossings]=saved;}
 const data=controller.graphInfoHolders.array[0],view=copy=>copy?{nodes:copy.nodeOrder.map(row=>row.map(p=>names.get(p))),ports:copy.portOrders.array.map(row=>row.array.map(list=>list.array.map(p=>portNames.get(p))))}:null;
 return {order:layers.map(layer=>layer.nodes.array.map(p=>names.get(p))),current:data.currentNodeOrder.map(row=>row.map(p=>names.get(p))),ports:Object.entries(nodes).map(([id,n])=>({id,ports:n.ports.array.map(p=>portNames.get(p)),constraint:$getProperty(n,PORT_CONSTRAINTS_0).name_0})),
  best:view(data.bestNodeAndPortOrder),currentlyBest:view(data.currentlyBestNodeAndPortOrder),bits,counts,sweeps,rngState:[rng.seedhi,rng.seedlo],monitor:{name:monitor.taskName,closed:monitor.closed_0},
  flags:{first:!!$getProperty(g,FIRST_TRY_WITH_INITIAL_ORDER),second:!!$getProperty(g,SECOND_TRY_WITH_INITIAL_ORDER)},layoutExecuted:false,crossingPhaseExecuted:true};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__sweepPhase(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-sweep-phase-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
