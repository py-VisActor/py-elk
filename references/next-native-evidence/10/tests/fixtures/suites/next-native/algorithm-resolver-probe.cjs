const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestBytes=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__algorithmResolver=function(request){
 registerLayoutAlgorithms(['layered','force','stress','mrtree','radial','disco','sporeOverlap','sporeCompaction','rectpacking']);
 const lookup=id=>$getAlgorithmDataBySuffix(SERVICE,id),lookups=request.lookups.map(id=>{const data=lookup(id);return {id,resolved:data?data.id_0:null,cachedIdentity:!data||data===lookup(id)};});
 const cases=request.cases.map(c=>{
  const ji=new JsonImporter,json=new JSONObject_0(JSON.parse(JSON.stringify(c.graph))),root=$transformNode_0(ji,json,null);$transformEdges_2(ji,json);
  let node=root;for(const index of c.select||[])node=$getChildren(node).get_0(index);
  if(c.presetResolved)$setProperty_1(node,RESOLVED_ALGORITHM,lookup(c.presetResolved));
  let outcome='returned',message=null;try{$visit_1(node);}catch(e){outcome='threw';message=e.message;}
  const resolved=$getProperty_0(node,RESOLVED_ALGORITHM);
  return {id:c.id,outcome,message,resolved:resolved?resolved.id_0:null,hasResolved:$hasProperty_0(node,RESOLVED_ALGORITHM),registryIdentity:!resolved||resolved===lookup(resolved.id_0)};
 });return {lookups,cases};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const observation=global.__algorithmResolver(JSON.parse(requestBytes));fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestBytes),
 pid:process.pid,parentPid:process.ppid,observation,layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
