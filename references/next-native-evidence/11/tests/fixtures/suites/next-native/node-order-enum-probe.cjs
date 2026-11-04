// One previous-layer predecessor forces the real canonical enum fallback.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__nodeOrderEnum=function(s){
 getInstance();$clinit_PortSide();$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_OrderingStrategy();$clinit_LongEdgeOrderingStrategy();
 const graph=new LGraph,prior=new LNode(graph),upper=new LNode(graph),lower=new LNode(graph),l0=new Layer(graph),l1=new Layer(graph);l0.id_0=0;l1.id_0=1;$add_3(graph.layers,l0);$add_3(graph.layers,l1);$setLayer(prior,0,l0);$setLayer(upper,0,l1);$setLayer(lower,1,l1);
 const p=new LPort,q=new LPort,e=new LEdge;$setNode(p,prior);$setNode(q,upper);$setSide(p,EAST_2);$setSide(q,WEST_2);$setSource_0(e,p);$setTarget_0(e,q);$setProperty_0(e,MODEL_ORDER_2,valueOf_3(s.edgeModelOrder));
 return {results:s.strategies.map(name=>{const type=name==='DUMMY_NODE_OVER'?DUMMY_NODE_OVER:DUMMY_NODE_UNDER,c=new ModelOrderNodeComparator_1(graph,[prior],PREFER_EDGES,type);return {strategy:name,value:$compare_17(c,upper,lower)};}),sourceDefault:$getProperty(graph,CONSIDER_MODEL_ORDER_LONG_EDGE_STRATEGY_0).name_0,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__nodeOrderEnum(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-node-order-enum-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
