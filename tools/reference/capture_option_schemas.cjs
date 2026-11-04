// Development-only original metadata observation. No layout or Python runtime.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,idsPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),idsRaw=fs.readFileSync(idsPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__schemaObservation=function(ids){
 registerLayoutAlgorithms(['layered','force','stress','mrtree','radial','disco','sporeOverlap','sporeCompaction','rectpacking']);
 const list=x=>{const a=[],it=x.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const className=c=>c?$getName(c):null;
 function value(v){
  if(v==null)return null;
  if(typeof v==='number')return Number.isFinite(v)?v:{nonfinite:String(v)};
  if(typeof v==='boolean'||typeof v==='string')return v;
  if(typeof v.name_0==='string')return {enum:v.name_0};
  if(typeof v.value_0==='number'||typeof v.value_0==='boolean'||typeof v.value_0==='string')return value(v.value_0);
  if('x_0'in v && 'y_0'in v)return {vector:[value(v.x_0),value(v.y_0)]};
  if('top_0'in v)return {insets:[value(v.top_0),value(v.right),value(v.bottom),value(v.left)]};
  if(typeof v.iterator_0==='function')return {sequence:list(v).map(value)};
  return {unmappedDefault:true,text:typeof v.toString_0==='function'?v.toString_0():String(v)};
 }
 return ids.map(id=>{
  const o=$getOptionDataBySuffix(SERVICE,id);if(!o)throw Error('Missing original option '+id);
  const constants=o.clazz&&$getEnumConstants(o.clazz),row={id:o.id_0,type:o.type_0.name_0,targets:list(o.targets).map(t=>t.name_0),
   declaredDefault:value(o.defaultValue),clazz:className(o.clazz),enumValues:constants?constants.map(v=>v.name_0):[]};
  if(o.type_0.name_0==='OBJECT'){
   try { const instance=$createDataInstance(o);row.factory={outcome:'returned',value:value(instance)}; }
   catch(e) { row.factory={outcome:'threw',text:String(e)}; }
  }
  return row;
 });
};`;
const moduleObject=new Module(workerPath,module);moduleObject.filename=workerPath;moduleObject.paths=Module._nodeModulePaths(pkg);
moduleObject._compile(raw.toString()+bridge,workerPath);
const ids=JSON.parse(idsRaw).map(x=>typeof x==='string'?x:x.id);
const options=global.__schemaObservation(ids);
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-original-option-schema-observation/v1',workerSha256:sha(raw),
 probeSha256:sha(fs.readFileSync(__filename)),idsSourceSha256:sha(idsRaw),pid:process.pid,parentPid:process.ppid,node:process.version,
 options,optionCount:options.length,layoutExecuted:false,candidateExecuted:false,fullValidation:false,
 scope:'Fixed original metadata defaults, enum constants, targets and object-factory observations; not migrated native option support'},null,2)+'\n',{flag:'wx'});
