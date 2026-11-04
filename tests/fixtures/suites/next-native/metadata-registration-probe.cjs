// Actual metadata registrations and suffix caches; no provider/layout execution.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__metadataRegistration=function(request){
 const savedService=SERVICE,savedInstance=instance_2;
 const values=map=>{const out=[],it=(new AbstractMap$2(map)).iterator_0();while(it.hasNext_0())out.push(it.next_1());return out;};
 const lookup=q=>{const d=$getOptionDataBySuffix(SERVICE,q);return d?d.id_0:null;};
 const fresh=()=>{instance_2=null;SERVICE=getInstance();};
 const snapshot=()=>({algorithms:values(SERVICE.layoutAlgorithmMap).map(d=>d.id_0),
   options:values(SERVICE.layoutOptionMap).map(d=>({id:d.id_0,legacyIds:d.legacyIds?Array.from(d.legacyIds):[]})),
   categories:values(SERVICE.layoutCategoryMap).map(d=>d.id_0),
   lookups:request.queries.map(query=>({query,id:lookup(query)}))});
 try{
  const groups=request.groups.map(group=>{fresh();registerLayoutAlgorithms(group.algorithms);return {name:group.name,registered:group.algorithms,...snapshot()};});
  fresh();const warm=request.warmSequence.map(algorithms=>{registerLayoutAlgorithms(algorithms);return {registered:algorithms,...snapshot()};});
  return {groups,warm};
 }finally{SERVICE=savedService;instance_2=savedInstance;}
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const observation=global.__metadataRegistration(JSON.parse(request));
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(request),
 pid:process.pid,parentPid:process.ppid,node:process.version,observation,layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
