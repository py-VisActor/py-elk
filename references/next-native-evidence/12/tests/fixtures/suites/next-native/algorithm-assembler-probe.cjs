// Real source assembler with explicitly supplied factory/config callback fixtures.
// No supplied callback runs layout math; this does not approve phase factories.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__algorithmAssembler=function(s){
 getInstance();$clinit_LayeredPhases();$clinit_IntermediateProcessorStrategy();$clinit_CycleBreakingStrategy();
 const phases=[P1_CYCLE_BREAKING,P2_LAYERING,P3_NODE_ORDERING,P4_NODE_PLACEMENT,P5_EDGE_ROUTING],graph=new LGraph;
 const events=[],counts={},bodies=new Map,factories={};
 const cfg=rows=>{const c=new LayoutProcessorConfiguration;for(const [when,p,name] of rows)(when==='before'?$addBefore:$addAfter)(c,phases[p],factories[name]);return c;};
 const create=(name)=>{counts[name]=(counts[name]||0)+1;events.push({kind:'create',name});if(name==='NULL')return null;
  const p=new GreedyCycleBreaker;bodies.set(p,name+'#'+counts[name]);p.getLayoutProcessorConfiguration=function(g){events.push({kind:'config',name,graphIdentity:g===graph});return cfg(s.configurations[name]||[]);};return p;};
 const names=[...new Set(s.mainFactories.filter(x=>x!==null))];
 names.forEach((name,i)=>{const f=new CycleBreakingStrategy(name,i);f.create_1=()=>create(name);factories[name]=f;});
 s.processorFactories.forEach((name,i)=>{const f=new IntermediateProcessorStrategy(name,i);f.create_1=()=>create(name);factories[name]=f;});
 const assembler=new AlgorithmAssembler(Lorg_eclipse_elk_alg_layered_LayeredPhases_2_classLit);
 const configure=names=>names.forEach((name,i)=>$setPhase(assembler,phases[i],name===null?null:factories[name]));
 configure(s.mainFactories);$addProcessorConfiguration(assembler,cfg(s.additional));
 const build=()=>{const start=events.length,algorithm=$build_0(assembler,graph).array;return {events:events.slice(start),algorithm:algorithm.map(p=>bodies.get(p))};};
 const first=build(),second=build(),list=assembler.list,cache=assembler.cache,additional=assembler.additionalProcessors;
 const reset=$reset_4(assembler),resetState={returnSelf:reset===assembler,listIdentity:assembler.list===list,cacheIdentity:assembler.cache===cache,additionalIdentity:assembler.additionalProcessors===additional,configured:assembler.configuredPhases.size_0,listLength:assembler.list.array.length,additionalLength:additional.list.array.length};
 configure(s.resetMainFactories);const afterReset=build();
 const f=factories[s.uncachedFactory],cached=$retrieveProcessor(assembler,f),start=events.length;assembler.enableCaching=false;
 const one=$retrieveProcessor(assembler,f),two=$retrieveProcessor(assembler,f);assembler.enableCaching=true;
 const after=$retrieveProcessor(assembler,f),uncached={events:events.slice(start),bodies:[bodies.get(one),bodies.get(two)],distinct:one!==two,oldCacheRestored:cached===after};
 const nullFactory=factories.NULL,firstNull=$retrieveProcessor(assembler,nullFactory),secondNull=$retrieveProcessor(assembler,nullFactory);
 const missing=new AlgorithmAssembler(Lorg_eclipse_elk_alg_layered_LayeredPhases_2_classLit),eventCount=events.length;let missingRejected=false;try{$build_0(missing,graph);}catch(e){missingRejected=true;}
 return {first,second,resetState,afterReset,uncached,cachedNull:firstNull===null&&secondNull===null,nullCreates:counts.NULL,missingRejected,missingCreatesNothing:events.length===eventCount,layoutExecuted:false,suppliedFactoryCallbacks:true};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__algorithmAssembler(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-algorithm-assembler-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
