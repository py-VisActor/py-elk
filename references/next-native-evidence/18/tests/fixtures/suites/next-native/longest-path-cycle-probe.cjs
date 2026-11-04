const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__longestCycle=function(input){
 const graph=new LGraph,nodes=[],ports=[];
 for(let i=0;i<input.nodeCount;i++){const n=new LNode(graph),p=new LPort;$add_3(graph.layerlessNodes,n);$setNode(p,n);nodes.push(n);ports.push(p);}
 for(const [a,b]of input.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}
 const owner=new LongestPathLayerer,monitor=new BasicProgressMonitor;let error=null;
 try{owner.process(graph,monitor);}catch(e){error={name:e.name,message:e.message};}
 return {value:{failed:error!==null,layerlessCount:graph.layerlessNodes.array.length,layerCount:graph.layers.array.length,ownerGraphRetained:owner.layeredGraph===graph,heights:owner.nodeHeights,monitorRunning:monitor.isRunning(),monitorClosed:monitor.closed_0},rawError:error};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);const result=global.__longestCycle(request);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(fs.readFileSync(requestPath)),pid:process.pid,parentPid:process.ppid,node:process.version,...result,scope:'Raw cyclic phase host failure only, no preceding cycle breaker. Error text/class/timing not equated across hosts.'},null,2)+'\n',{flag:'wx'});
