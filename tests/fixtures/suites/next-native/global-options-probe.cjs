// Actual optsToCfg, importer and visitor only. No layout or candidate execution.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath,selectedCase]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__globalOptions=function(request){
 const list=c=>{const a=[],it=c.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const normalize=(v,d)=>{
  if(v==null)return null;
  if(d.type_0.name_0==='ENUM')return v.name_0;
  if(d.type_0.name_0==='ENUMSET')return list(v).map(x=>x.name_0).sort();
  if(typeof v==='object'&&'x_0'in v)return {x:v.x_0,y:v.y_0,negativeZeroX:Object.is(v.x_0,-0),negativeZeroY:Object.is(v.y_0,-0)};
  if(typeof v==='object'&&'top_0'in v)return {top:v.top_0,right:v.right,bottom:v.bottom,left:v.left};
  return typeof v==='object'&&'value_0'in v?v.value_0:v;
 };
 return request.cases.map(c=>{
  instance_2=null;SERVICE=getInstance();registerLayoutAlgorithms(c.algorithms);
  const json=new JSONObject_0(JSON.parse(JSON.stringify(c.graph))),importer=new JsonImporter,root=$transformNode_0(importer,json,null);$transformEdges_2(importer,json);
  const elements=[];let it=new ElkGraphUtil$PropertiesSkippingTreeIterator(root);while(it.hasNext_0())elements.push(it.next_1());
  const snapshot=()=>elements.map(e=>({id:e.identifier,properties:request.observe.map(id=>{
   const d=$getOptionDataBySuffix(SERVICE,id),has=!!d&&$hasProperty_0(e,d);return {id,has,value:has?normalize($getProperty_0(e,d),d):null};
  })})).sort((a,b)=>a.id.localeCompare(b.id));
  const before=snapshot(),options=new JSONObject_0(c.options),config=optsToCfg(options);applyVisitors(root,[config]);
  const serialized=Object.keys(c.options).filter(k=>$getOptionDataBySuffix(SERVICE,k)).map(key=>{
   const v=$get_9(options,key);return {key,text:v.isString()?v.isString().value_0:v.isBoolean()?''+v.isBoolean().value_0:v.isNumber()?''+v.isNumber().value_0:v.toString_0()};
  });
  const a=$getChildren(root).get_0(0),b=$getChildren(root).get_0(1),vector=$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.nodeSize.minimum'),set=$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.nodeSize.constraints');
  return {name:c.name,serialized,before,after:snapshot(),configuredVectorCopiesDistinct:$hasProperty_0(a,vector)&&$hasProperty_0(b,vector)?$getProperty_0(a,vector)!==$getProperty_0(b,vector):null,
   configuredEnumSetsShared:$hasProperty_0(a,set)&&$hasProperty_0(b,set)?$getProperty_0(a,set)===$getProperty_0(b,set):null};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const request=JSON.parse(requestRaw);if(selectedCase)request.cases=request.cases.filter(c=>c.name===selectedCase);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,selectedCase:selectedCase||null,observation:global.__globalOptions(request),layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
