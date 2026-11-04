const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__nativeAdapterCallers=function(){ $clinit_CoreOptions();$clinit_LGraphAdapters();const p=new LPort,v=new LGraphAdapters$LPortAdapter(p,false),before=v.hasProperty(PORT_ANCHOR_0),value=v.getProperty(PORT_ANCHOR_0);return {anchorNullish:value==null,anchorStrictNull:value===null,anchorType:typeof value,hasBefore:before,hasAfter:v.hasProperty(PORT_ANCHOR_0)};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__nativeAdapterCallers(),preparedViews:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
