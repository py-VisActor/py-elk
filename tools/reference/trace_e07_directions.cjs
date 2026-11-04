// Development-only read-only oracle: V8 precise coverage per actual processor.
// No original distribution/source file is edited. Never used by Python runtime.
// Usage: node tools/reference/trace_e07_directions.cjs PACKAGE REQUEST NEW_OUTPUT
// Captures three separate engine processes using the original layout arguments.
// E07: actual direction mode/frame/mutable-property presence plus private NS
// component/previous-filling events. Property observers call getProperty only
// after hasProperty, never manufacture an absent mutable default. Observer
// property-query calls inside NS event hooks can appear in V8 helper counts;
// these counts are not pure algorithm reachability. Selected snapshots and
// three-engine public equality do not prove whole-private-state equivalence.
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
  const read = 'global.__E04Read = function(obj){const result={};for(const [label,property] of [["PORT_CONSTRAINTS",PORT_CONSTRAINTS_0],["LAYER_CONSTRAINT",LAYERING_LAYER_CONSTRAINT_0],["IN_LAYER_CONSTRAINT",IN_LAYER_CONSTRAINT],["REVERSED",REVERSED],["ORIGINAL_PORT_CONSTRAINTS",ORIGINAL_PORT_CONSTRAINTS],["INPUT_COLLECT",INPUT_COLLECT],["OUTPUT_COLLECT",OUTPUT_COLLECT]]){if($hasProperty(obj,property)){const v=$getProperty(obj,property);result[label]=v && v.name_0!==undefined?v.name_0:v;}}return result;};';
  const extraRead = 'global.__E05Facts=function(obj){const pairs=[["ORIGIN",ORIGIN_0],["LONG_EDGE_HAS_LABEL_DUMMIES",LONG_EDGE_HAS_LABEL_DUMMIES],["JUNCTION_POINTS",JUNCTION_POINTS],["LONG_EDGE_SOURCE",LONG_EDGE_SOURCE],["LONG_EDGE_TARGET",LONG_EDGE_TARGET],["LONG_EDGE_TARGET_NODE",LONG_EDGE_TARGET_NODE],["MODEL_ORDER",MODEL_ORDER_2],["WEIGHT",WEIGHT],["EDGE_THICKNESS",EDGE_THICKNESS_0],["PRIORITY_STRAIGHTNESS",PRIORITY_STRAIGHTNESS_0]];const origin=$hasProperty(obj,ORIGIN_0)?$getProperty(obj,ORIGIN_0):null;return {originIdentifier:origin && origin.identifier!==undefined?origin.identifier:null,properties:pairs.filter(pair=>$hasProperty(obj,pair[1])).map(pair=>[pair[0],$getProperty(obj,pair[1])])};};';
  const loopRead = 'global.__E06Holder=function(obj){return $hasProperty(obj,SELF_LOOP_HOLDER)?$getProperty(obj,SELF_LOOP_HOLDER):null;};';
  const directionRead = 'global.__E07Read=function(obj){const pairs=[["DIRECTION",DIRECTION],["DIRECTION_CONGRUENCY",DIRECTION_CONGRUENCY_0],["EDGE_LABELS_SIDE_SELECTION",EDGE_LABELS_SIDE_SELECTION_0],["NODE_LABELS_PADDING",NODE_LABELS_PADDING],["NODE_LABELS_PLACEMENT",NODE_LABELS_PLACEMENT_1],["NODE_SIZE_MINIMUM",NODE_SIZE_MINIMUM_0],["ALIGNMENT",ALIGNMENT],["POSITION",POSITION],["PORT_INDEX",PORT_INDEX]];return pairs.filter(pair=>$hasProperty(obj,pair[1])).map(pair=>[pair[0],$getProperty(obj,pair[1])]);};';
  const specifications = [
    ['ns-before-component', '    graph = $initialize_4(connComp);',
     '    global.__E07NS("before",connComp,null,previousLayeringNodeCounts,this$static.layeredGraph);\n    graph = $initialize_4(connComp);'],
    ['ns-after-component', '    layers = this$static.layeredGraph.layers;',
     '    global.__E07NS("after",connComp,graph,previousLayeringNodeCounts,this$static.layeredGraph);\n    layers = this$static.layeredGraph.layers;'],
    ['processor-call', '    processor.process(lgraph, monitor.subTask(monitorProgress));',
     '    '+read+extraRead+loopRead+directionRead+'\n    global.__E04Before(processor,lgraph,$getName(getClass__Ljava_lang_Class___devirtual$(processor)),processor.crossMinType && processor.crossMinType.name_0,$getProperty(lgraph,($clinit_InternalProperties_1(),RANDOM_0)));\n    processor.process(lgraph, monitor.subTask(monitorProgress));\n    global.__E04After(lgraph);'],
    ['rng-before', 'function $nextInternal(this$static, bits){',
     'function $nextInternal(this$static, bits){\n  global.__E04Rng("before",bits,this$static);'],
    ['rng-after', '  this$static.seedlo = lo;\n  if (bits <= 24) {',
     '  this$static.seedlo = lo;\n  global.__E04Rng("after",bits,this$static);\n  if (bits <= 24) {'],
    ['rng-set-seed', '  this$static.seedlo = seedlo ^ $intern_81;\n}',
     '  this$static.seedlo = seedlo ^ $intern_81;\n  global.__E04Rng("setSeed",null,this$static,{seedhi,seedlo});\n}'],
    ['greedy-before-cleanup', '  this$static.indeg = null;\n  this$static.outdeg = null;\n  this$static.mark = null;',
     '  global.__E05Greedy(this$static);\n  this$static.indeg = null;\n  this$static.outdeg = null;\n  this$static.mark = null;'],
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
  const arr = value => {
    if(Array.isArray(value))return value;
    if(value && Array.isArray(value.array))return value.array;
    if(value && value.header && value.tail && Number.isInteger(value.size_0)){
      const result=[];let cursor=value.header.next_0;
      for(let i=0;i<value.size_0;i++){
        if(!cursor || cursor===value.tail)throw Error('Observed linked-list size mismatch');
        result.push(cursor.value_0);cursor=cursor.next_0;
      }
      if(cursor!==value.tail)throw Error('Observed linked-list tail mismatch');
      return result;
    }
    return [];
  };
  const id = value => {
    if(!value) return null;
    if(!identities.has(value)) identities.set(value,'o'+identities.size);
    return identities.get(value);
  };
  const vec = v => v ? {x:v.x_0,y:v.y_0} : null;
  const inset = v => v ? {top:v.top_0,right:v.right,bottom:v.bottom,left:v.left} : null;
  const properties = value => global.__E04Read(value);
  const facts = value => {
    const source=global.__E05Facts(value);
    const scalarOrReference = item => {
      if(item===null || typeof item!=='object')return item;
      if(item.name_0!==undefined)return {enum:item.name_0};
      if(item.value_0!==undefined)return item.value_0;
      if(item.header && item.tail && Number.isInteger(item.size_0))return {identity:id(item),chainSize:item.size_0,chainValues:arr(item).map(vec)};
      return {identity:id(item)};
    };
    return {originIdentifier:source.originIdentifier,sourceProperties:Object.fromEntries(source.properties.map(([key,value])=>[key,scalarOrReference(value)]))};
  };
  const directionFacts = value => Object.fromEntries(global.__E07Read(value).map(([key,item])=> {
    let result=item;
    if(item!==null && typeof item==='object') {
      if(item.name_0!==undefined) result={identity:id(item),enum:item.name_0};
      else if(item.value_0!==undefined) result=item.value_0;
      else if(item.x_0!==undefined && item.y_0!==undefined) result={identity:id(item),vector:vec(item)};
      else if(item.top_0!==undefined) result={identity:id(item),insets:inset(item)};
      else result={identity:id(item)};
    }
    return [key,result];
  }));
  const sideIndices = value => value && Array.isArray(value.values) ? value.values.map((pair,index)=>pair ? {
    side:value.keySet.all[index].name_0,first:pair.first.value_0,last:pair.second.value_0}:null).filter(Boolean) : null;
  const layers = arr(graph.layers);
  const nodes = [...arr(graph.layerlessNodes),...layers.flatMap(layer=>arr(layer.nodes))];
  const keyValues = map => {
    const result=[];
    if(!map || !map.head)return result;
    let cursor=map.head.next_0;
    while(cursor!==map.head){
      if(!cursor || result.length>100000)throw Error('Observed LinkedHashMap chain mismatch');
      result.push(cursor.value_0);cursor=cursor.next_0;
    }
    return result;
  };
  const setValues = set => {
    if(!set)return [];
    const result=[],iterator=set.map_0.keySet_0().iterator_0();
    while(iterator.hasNext_0())result.push(iterator.next_1());
    return result;
  };
  const edge = e => ({identity:id(e),directionFacts:directionFacts(e),facts:facts(e),id:e.id_0,source:id(e.source),target:id(e.target),
    properties:properties(e),bendPoints:arr(e.bendPoints).map(vec)});
  const port = p => ({identity:id(p),directionFacts:directionFacts(p),explicitlySuppliedPortAnchor:p.explicitlySuppliedPortAnchor,facts:facts(p),id:p.id_0,owner:id(p.owner),side:p.side && p.side.name_0,
    position:vec(p.pos),size:vec(p.size_0),anchor:vec(p.anchor),properties:properties(p),
    incoming:arr(p.incomingEdges).map(edge),outgoing:arr(p.outgoingEdges).map(edge)});
  const loopHolder = n => {
    const holder=global.__E06Holder(n);
    if(!holder)return null;
    const wrapperPort = p => ({identity:id(p),isHidden:p.isHidden,hadOnlySelfLoops:p.hadOnlySelfLoops,
      port:port(p.lPort),incomingSLEdges:arr(p.incomingSLEdges).map(id),outgoingSLEdges:arr(p.outgoingSLEdges).map(id)});
    return {identity:id(holder),node:id(holder.lNode),arePortsHidden:holder.arePortsHidden,
      routingSlotCount:[...holder.routingSlotCount],ports:keyValues(holder.slPorts).map(wrapperPort),
      loops:arr(holder.slHyperLoops).map(l=>({identity:id(l),selfLoopType:l.selfLoopType && l.selfLoopType.name_0,
        leftmostPort:id(l.leftmostPort),rightmostPort:id(l.rightmostPort),routingSlot:[...l.routingSlot],
        portOrder:arr(l.slPorts).map(id),labelsPresent:!!l.slLabels,
        edges:setValues(l.slEdges).map(e=>({identity:id(e),slSource:id(e.slSource),slTarget:id(e.slTarget),edge:edge(e.lEdge)}))}))};
  };
  const node = n => ({identity:id(n),directionFacts:directionFacts(n),facts:facts(n),id:n.id_0,type:n.type_0 && n.type_0.name_0,
    position:vec(n.pos),size:vec(n.size_0),margin:inset(n.margin),padding:inset(n.padding),properties:properties(n),portSideIndices:sideIndices(n.portSideIndices),
    selfLoopHolder:loopHolder(n),ports:arr(n.ports).map(p=>({identity:id(p),directionFacts:directionFacts(p),explicitlySuppliedPortAnchor:p.explicitlySuppliedPortAnchor,id:p.id_0,facts:facts(p),side:p.side && p.side.name_0,position:vec(p.pos),size:vec(p.size_0),anchor:vec(p.anchor),
      properties:properties(p),incoming:arr(p.incomingEdges).map(e=>({identity:id(e),directionFacts:directionFacts(e),facts:facts(e),source:id(e.source),target:id(e.target),properties:properties(e),bendPoints:e.bendPoints ? arr(e.bendPoints).map(vec):[]})),
      outgoing:arr(p.outgoingEdges).map(e=>({identity:id(e),directionFacts:directionFacts(e),facts:facts(e),source:id(e.source),target:id(e.target),properties:properties(e),bendPoints:e.bendPoints ? arr(e.bendPoints).map(vec):[]}))}))});
  return {identity:id(graph),directionFacts:directionFacts(graph),facts:facts(graph),layerless:arr(graph.layerlessNodes).map(id),layers:layers.map(l=>({nodes:arr(l.nodes).map(id),size:vec(l.size_0)})),
    nodes:nodes.map(node),size:vec(graph.size_0),offset:vec(graph.offset),padding:inset(graph.padding),
    random:random ? {seedhi:random.seedhi,seedlo:random.seedlo}:null};
}
async function child(kind,packageRoot,requestPath,outputPath) {
  verify(packageRoot);
  const bytes=fs.readFileSync(requestPath),request=JSON.parse(bytes);
  const graph=clone(request.graph),constructor=clone(request.constructor),args=clone(request.layoutArguments);
  const original=fs.readFileSync(path.join(packageRoot,'lib/elk-worker.js'),'utf8');
  const phases=[],rng=[],supportEvents=[],identities=new Map();
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
        current={index:phases.length,name,strategy:strategy || null,transformMode:processor.mode ? processor.mode.name_0 : null,before,functions:[],after:null};
      };
      global.__E04After=g=>{
        current.functions=coverage();current.after=snapshot(g,currentRandom,identities);phases.push(current);current=null;currentRandom=null;
      };
      global.__E07NS=(event,component,privateGraph,previous,graph)=>supportEvents.push({kind:'ns-component',event,
        component:component.array.map(n=>global.__E05Facts(n).originIdentifier),previousCounts:previous===null?null:[...previous],
        privateNodes:privateGraph ? privateGraph.nodes.array.map(n=>({origin:global.__E05Facts(n.origin_0).originIdentifier,rank:n.layer})):null,
        currentLayers:graph.layers.array.map(l=>l.nodes.array.map(n=>global.__E05Facts(n).originIdentifier))});
      global.__E05Greedy=state=>supportEvents.push({kind:'greedy-before-cleanup',phaseIndex:current && current.index,
        nodes:state.layeredGraph.layerlessNodes.array.map(n=>({id:n.id_0,originIdentifier:global.__E05Facts(n).originIdentifier})),
        indeg:[...state.indeg],outdeg:[...state.outdeg],marks:[...state.mark]});
      global.__E04Rng=(event,bits,r,seedInput)=>rng.push({index:rng.length,event,bits,seedhi:r.seedhi,seedlo:r.seedlo,
        phaseIndex:current && current.index,phaseName:current && current.name,seedInput:seedInput || null,diagnosticCallStack:new Error().stack});
      const filename=path.join(packageRoot,'lib/elk-worker.js');
      const compiled=new Module(filename,module);compiled.filename=filename;compiled.paths=Module._nodeModulePaths(packageRoot);
      compiled._compile(source,filename);Worker=compiled.exports.Worker;
    } else Worker=require(path.join(packageRoot,'lib/elk-worker.js')).Worker;
    const ELK=require(path.join(packageRoot,'lib/elk-api.js')).default;
    elk=new ELK({...constructor,workerFactory:()=>new Worker()});
  }
  const result={schema:'py-elk-e07-direction-phase-observation/v1',kind,requestSha256:sha(bytes),actualLayoutArguments:args,
    constructorInfrastructureOverride:kind==='bundled'?null:'workerFactory uses locked PRETTY Worker (instrumented in memory when selected)',
    workerSha256:sha(Buffer.from(original)),instrumentedSourceSha256:kind==='instrumented'?sha(Buffer.from(source)):null,
    toolSha256:sha(fs.readFileSync(__filename)),patches,phases,rng,supportEvents,pythonAlgorithmsVerified:0};
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
  if(argv.length!==3) throw Error('Usage: node trace_e07_directions.cjs PACKAGE REQUEST NEW_OUTPUT');
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
  const summary={schema:'py-elk-e07-direction-phase-trace/v1',requestSha256:sha(fs.readFileSync(requestPath)),workerSha256:c.workerSha256,toolSha256:sha(fs.readFileSync(__filename)),
    actualLayoutArguments:c.actualLayoutArguments,argumentOverrides:{layoutArguments:null,constructorWorkerFactory:'development PRETTY engine plumbing only'},
    prettyResultExactToBundled:util.isDeepStrictEqual(a.result,b.result),instrumentedResultExactToPretty:util.isDeepStrictEqual(b.result,c.result),
    prettyInputExactToBundled:util.isDeepStrictEqual(a.inputAfter,b.inputAfter),instrumentedInputExactToPretty:util.isDeepStrictEqual(b.inputAfter,c.inputAfter),
    outcomes:Object.fromEntries(Object.entries(observations).map(([k,v])=>[k,v.outcome])),
    calls:c.phases.map(p=>({index:p.index,name:p.name,strategy:p.strategy,transformMode:p.transformMode,observedFunctionCount:p.functions.length})),
    rngPrimitiveDraws:c.rng.filter(r=>r.event==='before').length,
    limitation:'Actual fixed generated worker graph behavior with selected origin/reference facts and per-processor V8 coverage, not exact Java build identity or Python layout acceptance. Coverage membership/counts can vary across independent processes; absence alone does not prove non-execution. Snapshots include selected fields only and equality does not prove a processor is a no-op.'};
  summary.passed=Object.values(summary.outcomes).every(v=>v==='returned') && summary.prettyResultExactToBundled && summary.instrumentedResultExactToPretty && summary.prettyInputExactToBundled && summary.instrumentedInputExactToPretty;
  write(path.join(out,'summary.json'),summary);console.log(JSON.stringify({passed:summary.passed,processorCalls:summary.calls.length,rngPrimitiveDraws:summary.rngPrimitiveDraws}));
  if(!summary.passed) process.exitCode=1;
}
main().catch(error=>{console.error(error.stack || error);process.exitCode=2;});
