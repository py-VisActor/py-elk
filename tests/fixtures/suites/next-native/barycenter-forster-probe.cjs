// Actual source calculator, resolver and base caller over supplied layer/rank DTOs.
// Rank production, crossing counts and full layout are not executed.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__barycenterForster=function(s){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();
 const graph=new LGraph,layers=[],nodes=[],byNode={},ports={},names=new Map,portRanks=[];
 $setProperty_0(graph,IN_LAYER_SUCCESSOR_CONSTRAINTS_BETWEEN_NON_DUMMIES,!!s.twoPass);
 $setProperty_0(graph,CROSSING_MINIMIZATION_FORCE_NODE_MODEL_ORDER_0,false);
 for(let i=0;i<s.layerCount;i++){const layer=new Layer(graph);layer.id_0=i;layers.push(layer);$add_3(graph.layers,layer);}
 let pi=0;
 for(const spec of s.nodes){const node=new LNode(graph);names.set(node,spec.id);byNode[spec.id]=node;nodes.push(node);$setType(node,{NORMAL,LONG_EDGE}[spec.type||'NORMAL']);node.id_0=layers[spec.layer].nodes.array.length;$setLayer(node,node.id_0,layers[spec.layer]);
  for(const item of spec.ports){const port=new LPort;$setNode(port,node);$setSide(port,{EAST:EAST_2,WEST:WEST_2}[item.side]);port.id_0=pi++;ports[item.id]=port;portRanks[port.id_0]=item.rank??0;}}
 for(const spec of s.nodes){const node=byNode[spec.id];for(const [dto,key]of [['associates',BARYCENTER_ASSOCIATES],['successors',IN_LAYER_SUCCESSOR_CONSTRAINTS]])if(spec[dto])$setProperty_0(node,key,newArrayList_1(spec[dto].map(id=>byNode[id])));if(spec.unit)$setProperty_0(node,IN_LAYER_LAYOUT_UNIT,byNode[spec.unit]);}
 for(const spec of s.edges){const edge=new LEdge;$setSource_0(edge,ports[spec.source]);$setTarget_0(edge,ports[spec.target]);}
 const order=layers.map(layer=>layer.nodes.array.slice()),resolver=new ForsterConstraintResolver(order);
 order.forEach((row,l)=>{resolver.initAtLayerLevel(l,order);row.forEach((_,i)=>resolver.initAtNodeLevel(l,i,order));});
 const state=node=>resolver.barycenterStates[node.layer.id_0][node.id_0],refs=nodes.map(state),random=new Random_0(s.seed),heuristic=new BarycenterHeuristic(resolver,random,{portRanks});heuristic.initAfterTraversal();
 for(const spec of s.nodes)if(spec.initialState){const st=state(byNode[spec.id]);st.barycenter=spec.initialState.barycenter;st.degree=spec.initialState.degree;st.summedWeight=spec.initialState.weight;}
 const work=newArrayList_1(s.work.map(id=>byNode[id]));
 if(s.operation==='calculate')$calculateBarycenters(heuristic,work,s.forward);
 else if(s.operation==='resolve')$processConstraints(resolver,work);
 else heuristic.minimizeCrossings_0(work,s.preOrdered,false,s.forward);
 return{order:work.array.map(node=>names.get(node)),states:nodes.map((node,i)=>{const st=state(node);return{id:names.get(node),degree:st.degree,summedWeight:st.summedWeight,barycenter:st.barycenter??null,visited:st.visited,identityPreserved:st===refs[i]};}),sharedState:heuristic.barycenterState===resolver.barycenterStates,sharedRanks:heuristic.portRanks===portRanks,nextRandom:$nextDouble(random),rankProducerExecuted:false,fullLayoutValidated:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__barycenterForster(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-barycenter-forster-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
