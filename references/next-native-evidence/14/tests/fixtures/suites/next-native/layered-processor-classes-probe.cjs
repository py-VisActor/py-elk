// Real factory construction + actual getClass/getName metadata, no process body.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__layeredProcessorClasses=function(s){
 getInstance();
 const families={
  CycleBreakingStrategy:[Lorg_eclipse_elk_alg_layered_options_CycleBreakingStrategy_2_classLit,$create_4],
  LayeringStrategy:[Lorg_eclipse_elk_alg_layered_options_LayeringStrategy_2_classLit,$create_5],
  CrossingMinimizationStrategy:[Lorg_eclipse_elk_alg_layered_options_CrossingMinimizationStrategy_2_classLit,$create_3],
  NodePlacementStrategy:[Lorg_eclipse_elk_alg_layered_options_NodePlacementStrategy_2_classLit,$create_6],
  EdgeRouting:[Lorg_eclipse_elk_core_options_EdgeRouting_2_classLit,v=>$create_7(factoryFor(v))],
  IntermediateProcessorStrategy:[Lorg_eclipse_elk_alg_layered_intermediate_IntermediateProcessorStrategy_2_classLit,v=>v.create_1()]
 };
 const rows=[];for(const family of s.families){const[klass,create]=families[family];for(const strategy of castTo($getEnumConstants(klass),10)){const processor=create(strategy);rows.push({family,name:strategy.name_0,ordinal:strategy.ordinal,className:$getName(getClass__Ljava_lang_Class___devirtual$(processor))});}}
 return{rows,uniqueClassNames:[...new Set(rows.map(v=>v.className))].sort(),metadataOnly:true,phaseMathExecuted:false,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__layeredProcessorClasses(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-layered-processor-classes-source-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
