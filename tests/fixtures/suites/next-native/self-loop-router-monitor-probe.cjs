const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__monitorObservation=function(){
 $clinit_LayeredOptions();$clinit_EdgeRouting();const graph=new LGraph;$setProperty_0(graph,EDGE_ROUTING,ORTHOGONAL);const monitor=new BasicProgressMonitor;
 const before=monitor.isRunning();$process_50(new SelfLoopRouter,graph,monitor);
 return {beforeRunning:before,afterRunning:monitor.isRunning(),closed:monitor.closed_0,task:monitor.taskName,emptyLayerCount:graph.layers.array.length,actualProcess50Executed:true};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__monitorObservation(),layoutExecuted:false,nativeExecuted:false},null,2)+'\n',{flag:'wx'});
