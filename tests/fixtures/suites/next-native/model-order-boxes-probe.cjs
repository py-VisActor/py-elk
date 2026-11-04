// Original ModelOrder comparator only; specifically distinguish Integer boxes.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__modelOrderBoxes=function(s){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_GroupOrderStrategy();
 const graph=new LGraph,layer=new Layer(graph),a=new LNode(graph),b=new LNode(graph);layer.id_0=0;a.id_0=0;b.id_0=1;$setLayer(a,0,layer);$setLayer(b,1,layer);
 $setProperty_0(graph,MAX_MODEL_ORDER_NODES,valueOf_3(10));
 $setProperty_0(graph,CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CM_GROUP_ORDER_STRATEGY_0,ONLY_WITHIN_GROUP);
 $setProperty_0(a,MODEL_ORDER_2,valueOf_3(0));$setProperty_0(b,MODEL_ORDER_2,valueOf_3(1));
 const first=valueOf_3(s.group),second=s.shared?first:valueOf_3(s.group);
 $setProperty_0(a,CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CROSSING_MINIMIZATION_ID_0,first);$setProperty_0(b,CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CROSSING_MINIMIZATION_ID_0,second);
 const heuristic=new ModelOrderBarycenterHeuristic(null,null,null);heuristic.barycenterState=[[{barycenter:10},{barycenter:0}]];
 const sameBox=$getProperty(a,CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CROSSING_MINIMIZATION_ID_0)===$getProperty(b,CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CROSSING_MINIMIZATION_ID_0);
 return{sameBox,firstComparison:heuristic.barycenterStateComparator.compare_1(a,b),repeatedComparison:heuristic.barycenterStateComparator.compare_1(a,b),fullLayoutValidated:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__modelOrderBoxes(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-model-order-boxes-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
