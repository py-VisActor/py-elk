// Actual GraphInfo initialization and internal EnumSet default; no sweep.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__graphInfo=function(s){
 getInstance();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_GraphProperties();$clinit_LayerSweepCrossingMinimizer$CrossMinType();
 const graph=new LGraph,other=new LGraph,nested=new LGraph,nodes={},ports={},names=new Map,sides={EAST:EAST_2,WEST:WEST_2};
 const defaultSet=$getProperty(graph,GRAPH_PROPERTIES),otherSet=$getProperty(other,GRAPH_PROPERTIES),defaultShared=defaultSet===otherSet,defaultCloneable=instanceOf(defaultSet,4);defaultSet.add_2(EXTERNAL_PORTS);const defaultMutationVisible=$getProperty(other,GRAPH_PROPERTIES).contains(EXTERNAL_PORTS);
 for(const item of s.nodes){const n=new LNode(graph);nodes[item.id]=n;names.set(n,item.id);if(s.nested.includes(item.id))n.nestedGraph=nested;for(const [id,side]of item.ports){const p=new LPort;$setNode(p,n);$setSide(p,sides[side]);ports[id]=p;}}
 const layers=s.layers.map((ids,i)=>{const l=new Layer(graph);$add_3(graph.layers,l);ids.forEach((id,j)=>$setLayer(nodes[id],j,l));return l;});
 for(const [a,b]of s.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}
 const rng=new Random_0(s.seed);$setProperty_0(graph,RANDOM_0,rng);const bits=[],real=$nextInternal;$nextInternal=function(r,b){bits.push(b);return real(r,b);};let info;
 try{info=new GraphInfoHolder(graph,BARYCENTER,new ArrayList);}finally{$nextInternal=real;}
 const heuristic=info.crossMinimizer,resolver=heuristic.constraintResolver,marker={};$setBestNodeNPortOrder(info,marker);$setCurrentlyBestNodeAndPortOrder(info,marker);
 const observation={defaultShared,defaultMutationVisible,defaultAbsent:!$hasProperty(graph,GRAPH_PROPERTIES)&&!$hasProperty(other,GRAPH_PROPERTIES),hasExternalPorts:info.hasExternalPorts,hasParent:info.hasParent,parentNull:info.parentGraphData==null,useBottomUp:info.useBottomUp,
 ownedRows:info.currentNodeOrder.every((row,i)=>row!==layers[i].nodes.array&&row.every((n,j)=>n===layers[i].nodes.array[j])),nodeIds:info.currentNodeOrder.map(row=>row.map(n=>n.id_0)),layerIds:layers.map(l=>l.id_0),portIds:Object.values(ports).map(p=>p.id_0),ports:info.nPorts,
 childGraphs:info.childGraphs.array.map(g=>g===nested),distributor:info.portDistributor instanceof NodeRelativePortDistributor?'NodeRelativePortDistributor':'LayerTotalPortDistributor',randomBits:bits,randomState:[rng.seedhi,rng.seedlo],minimizer:'BarycenterHeuristic',
 liveStates:heuristic.barycenterState===resolver.barycenterStates,liveRanks:heuristic.portRanks===info.portDistributor.portRanks,nodePositions:info.portDistributor.nodePositions.map(row=>Array.from(row)),portRanks:Array.from(info.portDistributor.portRanks),states:info.currentNodeOrder.flat().map(n=>{const state=resolver.barycenterStates[n.layer.id_0][n.id_0];return{id:names.get(n),degree:state.degree,weight:state.summedWeight,barycenter:state.barycenter??null};}),
 separateInfoBuffer:info.portPositions!==info.crossingsCounter.crossingCounter.portPositions,sharedChildBuffer:info.crossingsCounter.crossingCounter.portPositions===info.crossingsCounter.hyperedgeCrossingsCounter.portPos,snapshotAssignmentsKeepReference:info.bestNodeAndPortOrder===marker&&info.currentlyBestNodeAndPortOrder===marker,layoutExecuted:false};
 defaultSet.remove_1(EXTERNAL_PORTS);return{observation,sourceFacts:{defaultCloneable}};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const result=global.__graphInfo(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-graph-info-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,...result,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
