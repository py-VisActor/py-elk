// Actual predicate and flat importer producer, without layout execution.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__modelOrderProducer=function(){
 registerLayoutAlgorithms(['layered']);
 const make=input=>{const ji=new JsonImporter,json=new JSONObject_0(input),root=$transformNode_0(ji,json,null);$transformEdges_2(ji,json);return root;};
 const cases=[{},...['MODEL_ORDER','BFS_NODE_ORDER','DFS_NODE_ORDER','GREEDY_MODEL_ORDER','SCC_CONNECTIVITY','SCC_NODE_TYPE'].map(v=>({'elk.layered.cycleBreaking.strategy':v})),
  ...['BF_MODEL_ORDER','DF_MODEL_ORDER'].map(v=>({'elk.layered.layering.strategy':v})),
  ...['MODEL_ORDER_LEFT_TO_RIGHT','MODEL_ORDER_RIGHT_TO_LEFT'].map(v=>({'elk.layered.layering.nodePromotion.strategy':v})),
  {'elk.layered.crossingMinimization.forceNodeModelOrder':true},{'elk.layered.considerModelOrder.strategy':'NODES_AND_EDGES'},
  {'elk.layered.considerModelOrder.components':'MODEL_ORDER'},{'elk.layered.considerModelOrder.crossingCounterNodeInfluence':1},
  {'elk.layered.considerModelOrder.crossingCounterPortInfluence':-1}];
 const predicates=cases.map(options=>({options,needed:$needsModelOrderBasedOnParent(make({id:'r',layoutOptions:options}))}));
 const input={id:'r',layoutOptions:{'elk.layered.crossingMinimization.forceNodeModelOrder':true},children:[
  {id:'skip',layoutOptions:{'elk.noLayout':true}},
  {id:'excluded',layoutOptions:{'elk.layered.considerModelOrder.noModelOrder':true},ports:[{id:'xp'}]},
  {id:'c',ports:[{id:'p0',layoutOptions:{'elk.noLayout':true}},{id:'p1'}]},
  {id:'d'}],edges:[{id:'e0',sources:['c'],targets:['d'],layoutOptions:{'elk.noLayout':true}},
                 {id:'e1',sources:['c'],targets:['d']}]};
 const root=make(input),g=$createLGraph(root);$importFlatGraph(new ElkGraphImporter,root,g);
 const list=l=>{const a=[],it=l.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const order=n=>$hasProperty_0(n,MODEL_ORDER_2)?$getProperty_0(n,MODEL_ORDER_2).value_0:null;
 const children=list($getChildren(root));
 return {predicates,nodes:children.map(n=>[n.identifier,order(n)]),ports:children.flatMap(n=>list($getPorts_3(n)).map(p=>[p.identifier,order(p)])),
  edges:list(root.containedEdges).map(e=>[e.identifier,order(e)]),maximum:$getProperty(g,MAX_MODEL_ORDER_NODES).value_0,
  importedNodeCount:g.layerlessNodes.array.length};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const observation=global.__modelOrderProducer();fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),
 pid:process.pid,parentPid:process.ppid,observation,layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
