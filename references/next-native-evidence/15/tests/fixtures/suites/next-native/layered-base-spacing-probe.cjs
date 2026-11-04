const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const[pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),wp=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(wp),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__baseSpacing=function(s){
 getInstance();$clinit_LayeredSpacings$LayeredSpacingsBuilder();
 const g=new LGraph,b=new LayeredSpacings$LayeredSpacingsBuilder(s.base),keys=[BASE_SPACING_OPTION,...DEPENDENT_SPACING_OPTIONS.array],writes=[];
 if(s.existingEdgeEdge!==undefined)$setProperty_0(g,SPACING_EDGE_EDGE,s.existingEdgeEdge);
 const snapshot=()=>keys.map(p=>({id:p.getId(),present:$hasProperty(g,p),value:$hasProperty(g,p)?$doubleValue(castToDouble($getProperty(g,p))):null}));
 const factors=keys.map(p=>({id:p.getId(),factor:$doubleValue(castToDouble($get_10(b.factorMap,p))),default:p.getDefault()==null?null:$doubleValue(castToDouble(p.getDefault()))}));
 const acceptsProperty=b.filters.array[0].accept_4(g,BASE_SPACING_OPTION),before=snapshot(),filtersBefore=b.filters.array.length;
 const original=$lambda$6;$lambda$6=function(builder,holder,property){writes.push(property.getId());return original(builder,holder,property);};
 let first,second,filtersAfterFirst,filtersAfterSecond;
 try{$apply_16(b,g);first=snapshot();filtersAfterFirst=b.filters.array.length;$apply_16(b,g);second=snapshot();filtersAfterSecond=b.filters.array.length;}finally{$lambda$6=original;}
 return{id:s.id,factors,acceptsProperty,before,first,second,writes,filtersBefore,filtersAfterFirst,filtersAfterSecond,layoutExecuted:false};
};`;
const m=new Module(wp,module);m.filename=wp;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,wp);
const observation={cases:JSON.parse(requestRaw).cases.map(s=>global.__baseSpacing(s)),layoutExecuted:false};
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-base-spacing/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
