// Actual registered algorithm feature declarations; no provider/layout execution.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__algorithmFeatures=function(){
 const names=['fixed','box','random','layered','force','stress','mrtree','radial','disco','sporeOverlap','sporeCompaction','rectpacking'];
 registerLayoutAlgorithms(names);
 return names.map(name=>{const data=$getAlgorithmDataBySuffix(SERVICE,name),features=[],it=data.supportedFeatures.iterator_0();while(it.hasNext_0())features.push(it.next_1().name_0);return {id:data.id_0,features};});
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const observation=global.__algorithmFeatures();fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),
 pid:process.pid,parentPid:process.ppid,observation,layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
