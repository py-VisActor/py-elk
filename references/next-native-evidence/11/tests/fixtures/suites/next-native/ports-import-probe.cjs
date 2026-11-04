// Read-only snapshot at the actual fixed-worker import return. All original
// pipeline/JSON/EMF code executes; no model or import arithmetic is reimplemented.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [packagePath,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(packagePath);
const workerPath=path.join(pkg,'lib/elk-worker.js'),worker=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(worker)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Fixed worker differs');
const original=worker.toString(),start=original.indexOf('function $importGraph_1('),end=original.indexOf('\n}\n',start)+3;
const before=original.slice(start,end),match='  return topLevelGraph;',replacement='  global.__P03Imports.push(global.__P03Snapshot(topLevelGraph));\n'+match;
if(start<0||before.split(match).length!==2)throw Error('Import instrumentation anchor not unique');
const bridge=String.raw`
global.__P03Snapshot=function(g){
 const vec=v=>[v.x_0,v.y_0],origin=o=>$getProperty(o,ORIGIN_0),id=o=>{const v=origin(o);return v?v.identifier:null;};
 const property=o=>{const result={};for(const [name,key] of [['PORT_INDEX',PORT_INDEX],['PORT_BORDER_OFFSET',PORT_BORDER_OFFSET],['PORT_RATIO_OR_POSITION',PORT_RATIO_OR_POSITION_0],['INSIDE_CONNECTIONS',INSIDE_CONNECTIONS]])if($hasProperty(o,key)){let v=$getProperty(o,key);result[name]=v&&v.value_0!==undefined?v.value_0:v;}return result;};
 const flags=[],iter=$getProperty(g,GRAPH_PROPERTIES).iterator_0();while(iter.hasNext_0())flags.push(iter.next_1().name_0);
 return {direction:$getProperty(g,DIRECTION).name_0,flags:flags.sort(),nodes:g.layerlessNodes.array.map(n=>({id:id(n),position:vec(n.pos),size:vec(n.size_0),constraints:$getProperty(n,PORT_CONSTRAINTS_0).name_0,ports:n.ports.array.map(p=>({id:id(p),side:p.side.name_0,position:vec(p.pos),size:vec(p.size_0),anchor:vec(p.anchor),explicitlySuppliedPortAnchor:p.explicitlySuppliedPortAnchor,properties:property(p),incoming:p.incomingEdges.array.map(id),outgoing:p.outgoingEdges.array.map(id)}))}))};
};
`;
const changed=original.slice(0,start)+before.replace(match,replacement)+original.slice(end)+bridge;
global.__P03Imports=[];
const compiled=new Module(workerPath,module);compiled.filename=workerPath;compiled.paths=Module._nodeModulePaths(pkg);compiled._compile(changed,workerPath);
const ELK=require(path.join(pkg,'lib/elk-api.js')).default,Worker=compiled.exports.Worker,request=JSON.parse(requestRaw);
const elk=new ELK({...request.constructor,workerFactory:()=>new Worker()});
(async()=>{let result,error,termination;try{result=await elk.layout(request.graph,request.layoutArguments);}catch(e){error={name:e.name,message:e.message};}finally{try{elk.terminateWorker();termination={outcome:'returned'};}catch(e){termination={outcome:'threw',name:e.name,message:e.message};}}
 fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-port-import-observation/v1',mode:'read-only-original-import-hook',requestSha256:sha(requestRaw),workerSha256:sha(worker),instrumentedSourceSha256:sha(Buffer.from(changed)),probeSha256:sha(fs.readFileSync(__filename)),patch:{start,end,match,replacement},memoryOnlyBridge:bridge,node:process.version,pid:process.pid,parentPid:process.ppid,imports:global.__P03Imports,apiOutcome:error?'threw':'returned',apiResult:result,apiError:error,termination,candidateExecuted:false,wholePortsPipelineAccepted:false},null,2)+'\n',{flag:'wx'});
})().catch(e=>{console.error(e);process.exitCode=1;});
