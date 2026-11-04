// Real default phase factory configurations; no phase math is executed.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__phaseFactoryConfigurations=function(s){
 getInstance();$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_IntermediateProcessorStrategy();$clinit_LayerSweepCrossingMinimizer$CrossMinType();$clinit_EdgeRouting();
 const enums=castTo($getEnumConstants(Lorg_eclipse_elk_alg_layered_intermediate_IntermediateProcessorStrategy_2_classLit),10),flags=castTo($getEnumConstants(Lorg_eclipse_elk_alg_layered_options_GraphProperties_2_classLit),10);
 const cfgView=c=>c===null?null:c.list.array.map(bucket=>bucket===null?null:enums.filter(v=>$contains_6(bucket,v)).map(v=>v.name_0));
 const main=[new GreedyCycleBreaker,new NetworkSimplexLayerer,new LayerSweepCrossingMinimizer(BARYCENTER),new BKNodePlacer,new OrthogonalEdgeRouter];
 const observations=s.cases.map(item=>{
  const g=new LGraph;if(item.flags!==null){const all=flags,p=new EnumSet$EnumSetImpl(all,castTo(createFrom(all,all.length),10),0);for(const name of item.flags)p.add_2(flags.find(v=>v.name_0===name));$setProperty_0(g,GRAPH_PROPERTIES,p);}
  $setProperty_0(g,FEEDBACK_EDGES_0,item.feedback);
  const results=main.map(p=>{let reads=0;const saved=$getProperty;$getProperty=function(holder,prop){if(holder===g&&prop===FEEDBACK_EDGES_0)reads++;return saved(holder,prop);};
   let a,b;try{a=p.getLayoutProcessorConfiguration(g);b=p.getLayoutProcessorConfiguration(g);}finally{$getProperty=saved;}
   return {configuration:cfgView(a),sameConfiguration:a===b,bucketsIndependent:a===null?null:a.list.array.every((bucket,i)=>bucket!==b.list.array[i]),feedbackReads:reads};
  });
  return {id:item.id,phases:results,graphPropertiesPresent:$hasProperty(g,GRAPH_PROPERTIES)};
 });
 const undefinedFactory=factoryFor(UNDEFINED_3),orthoFactory=factoryFor(ORTHOGONAL),polylineFactory=factoryFor(POLYLINE);
 return {cases:observations,edgeFactoryIdentity:{sameUndefined:undefinedFactory===factoryFor(UNDEFINED_3),undefinedVsOrthoDistinct:undefinedFactory!==orthoFactory,orthoVsPolylineDistinct:orthoFactory!==polylineFactory},sourceObjectApi:true,phaseMathExecuted:false,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__phaseFactoryConfigurations(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-phase-factory-configurations/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
