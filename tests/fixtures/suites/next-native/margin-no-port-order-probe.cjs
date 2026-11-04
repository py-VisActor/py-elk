// Actual source computeLabelBox numeric leaf; adapters supply geometry only.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__marginNoPortOrder=function(){
 const node={getPosition(){return new KVector_1(1e16,3);},getSize(){return new KVector_1(1,4);}},label={getSize(){return new KVector_1(1,2);}};
 return [true,false].map(incoming=>{const box=new ElkRectangle;$computeLabelBox(box,label,incoming,node,null,null,1);return {incoming,box:[box.x_0,box.y_0,box.width_0,box.height]};});
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__marginNoPortOrder(),layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
