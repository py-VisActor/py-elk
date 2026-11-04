// Observe actual ElkNode identity hashing and radial fresh-set callers. The
// explicit forcedHash case is instrumented runtime support, not a layout run.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__radialHash=function(s){
 const nodes=Array.from({length:s.count},()=>new ElkNodeImpl),names=new Map(nodes.map((n,i)=>[n,i]));
 for(const i of s.prehash||[])hashCode__I__devirtual$(nodes[i]);
 if(s.forcedHash)for(const[i,value]of s.forcedHash)nodes[i].$H=value;
 const list=c=>{const a=[],it=c.iterator_0();while(it.hasNext_0())a.push(names.get(it.next_1()));return a;};
 let set;
 if(s.parents){
  for(const[a,b]of s.edges){const e=new ElkEdgeImpl;$getSources(e).add_2(nodes[a]);$getTargets(e).add_2(nodes[b]);}
  const parents=new ArrayList;for(const i of s.parents)$add_3(parents,nodes[i]);
  set=getNextLevelNodeSet(parents);
 }else{set=new HashSet;for(const i of s.insert)$add_6(set,nodes[i]);}
 return {order:list(set),hashes:nodes.map(n=>n.$H===undefined?null:n.$H),bucketKeys:Array.from(set.map_0.hashCodeMap.backingMap.keys()),instrumentedHashOverride:!!s.forcedHash};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__radialHash(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-radial-hashset-observation/v1',mode:'original-ElkNode-and-radial-set-object-adapter',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
