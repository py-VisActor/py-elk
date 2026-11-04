// Development-only read-only oracle: V8 precise coverage per actual processor.
// No original distribution/source file is edited. Never used by Python runtime.
// Usage: node tools/reference/trace_e04_slice.cjs PACKAGE REQUEST NEW_OUTPUT
// Captures three separate engine processes using the original layout arguments.
// Coverage is observational: missing V8 entries do not prove non-execution,
// and memberships/counts need not be identical across independent processes.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const Module = require('node:module');
const inspector = require('node:inspector');
const cp = require('node:child_process');
const util = require('node:util');
const ROOT = path.resolve(__dirname, '../..');
const lock = JSON.parse(fs.readFileSync(path.join(ROOT, 'UPSTREAM.json'), 'utf8'));
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const clone = v => JSON.parse(JSON.stringify(v));
const write = (p, v) => fs.writeFileSync(p, JSON.stringify(v, null, 2) + '\n', {flag:'wx'});
function verify(packageRoot) {
  for (const [name, value] of Object.entries(lock.distribution.sha256Files))
    if (sha(fs.readFileSync(path.join(packageRoot, name))) !== value) throw Error('Distribution SHA drift: ' + name);
}
function instrument(original) {
  const read = 'global.__E04Read = function(obj){const result={};for(const [label,property] of [["PORT_CONSTRAINTS",PORT_CONSTRAINTS_0],["LAYER_CONSTRAINT",LAYERING_LAYER_CONSTRAINT_0],["IN_LAYER_CONSTRAINT",IN_LAYER_CONSTRAINT],["REVERSED",REVERSED]]){if($hasProperty(obj,property)){const v=$getProperty(obj,property);result[label]=v && v.name_0!==undefined?v.name_0:v;}}return result;};';
  const specifications = [
    ['processor-call', '    processor.process(lgraph, monitor.subTask(monitorProgress));',
     '    '+read+'\n    global.__E04Before(processor,lgraph,$getName(getClass__Ljava_lang_Class___devirtual$(processor)),processor.crossMinType && processor.crossMinType.name_0,$getProperty(lgraph,($clinit_InternalProperties_1(),RANDOM_0)));\n    processor.process(lgraph, monitor.subTask(monitorProgress));\n    global.__E04After(lgraph);'],
    ['rng-before', 'function $nextInternal(this$static, bits){',
     'function $nextInternal(this$static, bits){\n  global.__E04Rng("before",bits,this$static);'],
    ['rng-after', '  this$static.seedlo = lo;\n  if (bits <= 24) {',
     '  this$static.seedlo = lo;\n  global.__E04Rng("after",bits,this$static);\n  if (bits <= 24) {'],
    ['rng-set-seed', '  this$static.seedlo = seedlo ^ $intern_81;\n}',
     '  this$static.seedlo = seedlo ^ $intern_81;\n  global.__E04Rng("setSeed",null,this$static,{seedhi,seedlo});\n}'],
  ];
  const patches = specifications.map(([id,match,replacement]) => {
    if (original.split(match).length !== 2) throw Error('Nonunique patch anchor: '+id);
    return {id, originalStart:original.indexOf(match), originalEnd:original.indexOf(match)+match.length, match,replacement};
  }).sort((a,b)=>a.originalStart-b.originalStart);
  let source='', previous=0;
  for (const patch of patches) {
    source += original.slice(previous,patch.originalStart);
    patch.compiledStart=source.length;
    source += patch.replacement;
    patch.compiledEnd=source.length;
    previous=patch.originalEnd;
  }
  source+=original.slice(previous);
  const originalOffset = offset => {
    let delta=0;
    for(const patch of patches) {
      if(offset>=patch.compiledEnd) delta += patch.replacement.length-patch.match.length;
      else if(offset>=patch.compiledStart) return patch.originalStart;
      else break;
    }
    return offset-delta;
  };
  return {source,patches,originalOffset};
}
function syncPost(session, name, args={}) {
  let returned=false, failure, result;
  session.post(name,args,(error,value)=>{returned=true;failure=error;result=value;});
  if(!returned) throw Error('Inspector callback is not synchronous; cannot attribute coverage to a processor');
  if(failure) throw failure;
  return result;
}
function snapshot(graph, random, identities) {
  const arr = value => value && Array.isArray(value.array) ? value.array : [];
  const id = value => {
    if(!value) return null;
    if(!identities.has(value)) identities.set(value,'o'+identities.size);
    return identities.get(value);
  };
  const vec = v => v ? {x:v.x_0,y:v.y_0} : null;
  const inset = v => v ? {top:v.top_0,right:v.right,bottom:v.bottom,left:v.left} : null;
  const properties = value => global.__E04Read(value);
  const sideIndices = value => value && Array.isArray(value.values) ? value.values.map((pair,index)=>pair ? {
    side:value.keySet.all[index].name_0,first:pair.first.value_0,last:pair.second.value_0}:null).filter(Boolean) : null;
  const layers = arr(graph.layers);
  const nodes = [...arr(graph.layerlessNodes),...layers.flatMap(layer=>arr(layer.nodes))];
  const node = n => ({identity:id(n),id:n.id_0,type:n.type_0 && n.type_0.name_0,
    position:vec(n.pos),size:vec(n.size_0),margin:inset(n.margin),padding:inset(n.padding),properties:properties(n),portSideIndices:sideIndices(n.portSideIndices),
    ports:arr(n.ports).map(p=>({identity:id(p),side:p.side && p.side.name_0,position:vec(p.pos),size:vec(p.size_0),anchor:vec(p.anchor),
      properties:properties(p),incoming:arr(p.incomingEdges).map(e=>({identity:id(e),source:id(e.source),target:id(e.target),properties:properties(e),bendPoints:e.bendPoints ? arr(e.bendPoints).map(vec):[]})),
      outgoing:arr(p.outgoingEdges).map(e=>({identity:id(e),source:id(e.source),target:id(e.target),properties:properties(e),bendPoints:e.bendPoints ? arr(e.bendPoints).map(vec):[]}))}))});
  return {layerless:arr(graph.layerlessNodes).map(id),layers:layers.map(l=>({nodes:arr(l.nodes).map(id),size:vec(l.size_0)})),
    nodes:nodes.map(node),size:vec(graph.size_0),offset:vec(graph.offset),padding:inset(graph.padding),
    random:random ? {seedhi:random.seedhi,seedlo:random.seedlo}:null};
}
async function child(kind,packageRoot,requestPath,outputPath) {
  verify(packageRoot);
  const bytes=fs.readFileSync(requestPath),request=JSON.parse(bytes);
  const graph=clone(request.graph),constructor=clone(request.constructor),args=clone(request.layoutArguments);
  const original=fs.readFileSync(path.join(packageRoot,'lib/elk-worker.js'),'utf8');
  const phases=[],rng=[],identities=new Map();
  let current=null,currentRandom=null,source=original,patches=[],mapped=offset=>offset,session;
  const starts=[0];for(let i=0;i<original.length;i++)if(original[i]==='\n')starts.push(i+1);
  const line = offset => {let lo=0,hi=starts.length;while(lo+1<hi){const middle=(lo+hi)>>1;if(starts[middle]<=offset)lo=middle;else hi=middle;}return lo+1;};
  function coverage() {
    const result=syncPost(session,'Profiler.takePreciseCoverage');
    const scripts=result.result.filter(script=>script.url.replaceAll('\\','/').endsWith('/elk-worker.js'));
    return scripts.flatMap(script=>script.functions.filter(f=>f.functionName && f.ranges[0].count>0).map(f=>{
      const start=mapped(f.ranges[0].startOffset),end=mapped(f.ranges[0].endOffset);
      return {name:f.functionName,startOffset:start,endOffset:end,startLine:line(start),endLine:line(end-1),
        sourceSha256:sha(Buffer.from(original.slice(start,end))),callCount:f.ranges[0].count,
        blocks:f.ranges.map(r=>({startOffset:mapped(r.startOffset),endOffset:mapped(r.endOffset),count:r.count}))};
    }));
  }
  let elk;
  if(kind==='bundled') {
    const ELK=require(path.join(packageRoot,'lib/elk.bundled.js'));
    elk=new ELK(constructor);
  } else {
    let Worker;
    if(kind==='instrumented') {
      const changed=instrument(original); source=changed.source; patches=changed.patches;mapped=changed.originalOffset;
      session=new inspector.Session();session.connect();syncPost(session,'Profiler.enable');
      syncPost(session,'Profiler.startPreciseCoverage',{callCount:true,detailed:true});
      global.__E04Before=(processor,g,name,strategy,random)=>{
        const before=snapshot(g,random,identities);
        coverage();
        currentRandom=random;
        current={index:phases.length,name,strategy:strategy || null,before,functions:[],after:null};
      };
      global.__E04After=g=>{
        current.functions=coverage();current.after=snapshot(g,currentRandom,identities);phases.push(current);current=null;currentRandom=null;
      };
      global.__E04Rng=(event,bits,r,seedInput)=>rng.push({index:rng.length,event,bits,seedhi:r.seedhi,seedlo:r.seedlo,
        phaseIndex:current && current.index,phaseName:current && current.name,seedInput:seedInput || null});
      const filename=path.join(packageRoot,'lib/elk-worker.js');
      const compiled=new Module(filename,module);compiled.filename=filename;compiled.paths=Module._nodeModulePaths(packageRoot);
      compiled._compile(source,filename);Worker=compiled.exports.Worker;
    } else Worker=require(path.join(packageRoot,'lib/elk-worker.js')).Worker;
    const ELK=require(path.join(packageRoot,'lib/elk-api.js')).default;
    elk=new ELK({...constructor,workerFactory:()=>new Worker()});
  }
  const result={schema:'py-elk-e04-phase-observation/v1',kind,requestSha256:sha(bytes),actualLayoutArguments:args,
    constructorInfrastructureOverride:kind==='bundled'?null:'workerFactory uses locked PRETTY Worker (instrumented in memory when selected)',
    workerSha256:sha(Buffer.from(original)),instrumentedSourceSha256:kind==='instrumented'?sha(Buffer.from(source)):null,
    toolSha256:sha(fs.readFileSync(__filename)),patches,phases,rng,pythonAlgorithmsVerified:0};
  try {result.result=await elk.layout(graph,args);result.outcome='returned';}
  catch(error){result.outcome='threw';result.error={name:error.name,message:error.message,stack:error.stack};}
  result.inputAfter=graph;
  try {elk.terminateWorker();result.termination={outcome:'returned'};}
  catch(error){result.termination={outcome:'threw',name:error.name,message:error.message};}
  if(session){syncPost(session,'Profiler.stopPreciseCoverage');session.disconnect();}
  write(outputPath,result);
}
async function main() {
  const argv=process.argv.slice(2);
  if(argv[0]==='--child') return child(argv[1],path.resolve(argv[2]),path.resolve(argv[3]),path.resolve(argv[4]));
  if(argv.length!==3) throw Error('Usage: node trace_e04_slice.cjs PACKAGE REQUEST NEW_OUTPUT');
  const [packageArg,requestArg,outArg]=argv;
  const packageRoot=path.resolve(packageArg),requestPath=path.resolve(requestArg),out=path.resolve(outArg);
  verify(packageRoot);fs.mkdirSync(out,{recursive:false});fs.copyFileSync(requestPath,path.join(out,'request.json'));
  const commands=[],observations={};
  for(const kind of ['bundled','pretty','instrumented']) {
    const observationPath=path.join(out,kind+'.json');
    const command=[__filename,'--child',kind,packageRoot,requestPath,observationPath];
    const execution=cp.spawnSync(process.execPath,command,{timeout:45000,encoding:'utf8',maxBuffer:32*1024*1024});
    fs.writeFileSync(path.join(out,kind+'-stdout.log'),execution.stdout || '',{flag:'wx'});
    fs.writeFileSync(path.join(out,kind+'-stderr.log'),execution.stderr || '',{flag:'wx'});
    commands.push({argv:[process.execPath,...command],cwd:process.cwd(),exitCode:execution.status,signal:execution.signal,error:execution.error?String(execution.error):null});
    write(path.join(out,kind+'-command.json'),commands.at(-1));
    if(execution.status!==0) throw Error('Trace child failed: '+kind);
    observations[kind]=JSON.parse(fs.readFileSync(observationPath,'utf8'));
  }
  const a=observations.bundled,b=observations.pretty,c=observations.instrumented;
  const summary={schema:'py-elk-e04-phase-trace/v1',requestSha256:sha(fs.readFileSync(requestPath)),workerSha256:c.workerSha256,toolSha256:sha(fs.readFileSync(__filename)),
    actualLayoutArguments:c.actualLayoutArguments,argumentOverrides:{layoutArguments:null,constructorWorkerFactory:'development PRETTY engine plumbing only'},
    prettyResultExactToBundled:util.isDeepStrictEqual(a.result,b.result),instrumentedResultExactToPretty:util.isDeepStrictEqual(b.result,c.result),
    prettyInputExactToBundled:util.isDeepStrictEqual(a.inputAfter,b.inputAfter),instrumentedInputExactToPretty:util.isDeepStrictEqual(b.inputAfter,c.inputAfter),
    outcomes:Object.fromEntries(Object.entries(observations).map(([k,v])=>[k,v.outcome])),
    calls:c.phases.map(p=>({index:p.index,name:p.name,strategy:p.strategy,observedFunctionCount:p.functions.length})),
    rngPrimitiveDraws:c.rng.filter(r=>r.event==='before').length,
    limitation:'Actual fixed generated worker behavior with per-processor V8 coverage, not exact Java build identity or Python layout acceptance. Coverage membership/counts can vary across independent processes; absence alone does not prove non-execution. Snapshots include selected fields only and equality does not prove a processor is a no-op.'};
  summary.passed=Object.values(summary.outcomes).every(v=>v==='returned') && summary.prettyResultExactToBundled && summary.instrumentedResultExactToPretty && summary.prettyInputExactToBundled && summary.instrumentedInputExactToPretty;
  write(path.join(out,'summary.json'),summary);console.log(JSON.stringify({passed:summary.passed,processorCalls:summary.calls.length,rngPrimitiveDraws:summary.rngPrimitiveDraws}));
  if(!summary.passed) process.exitCode=1;
}
main().catch(error=>{console.error(error.stack || error);process.exitCode=2;});
