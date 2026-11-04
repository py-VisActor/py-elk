// Original EnumSet cloneability/default/global assignment scalar observations.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__enumSetIdentity=function(s){
 registerLayoutAlgorithms([]);
 const ji=new JsonImporter,json=new JSONObject_0({id:'r',children:[{id:'a'},{id:'b'}]}),root=$transformNode_0(ji,json,null);$transformEdges_2(ji,json);
 const children=$getChildren(root),a=children.get_0(0),b=children.get_0(1);
 const properties=[['org.eclipse.elk.nodeSize.options',NODE_SIZE_OPTIONS_6],['org.eclipse.elk.nodeLabels.placement',NODE_LABELS_PLACEMENT_5]];
 const before=properties.map(([id,p])=>({id,aHas:$hasProperty_0(a,p),bHas:$hasProperty_0(b,p)}));
 if(s.operation==='global'){
  const lc=optsToCfg(new JSONObject_0(s.global));
  applyVisitors(root,stampJavaTypeInfo(getClassLiteralForArray(Lorg_eclipse_elk_core_util_IGraphElementVisitor_2_classLit,1),$intern_2,544,0,[lc]));
 }
 const members=set=>{const result=[],it=set.iterator_0();while(it.hasNext_0())result.push(it.next_1().name_0);return result;};
 return {before,properties:properties.map(([id,p])=>{const x=$getProperty_0(a,p),y=$getProperty_0(b,p);return{id,type4:instanceOf(x,4),sharedBetweenNodes:x===y,sameAsCoreDefault:x===p.getDefault(),aHasAfter:$hasProperty_0(a,p),bHasAfter:$hasProperty_0(b,p),aMembers:members(x),bMembers:members(y)};}),layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__enumSetIdentity(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-enumset-identity-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
