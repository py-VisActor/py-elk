const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__longestPath=function(input){
 $clinit_LNode$NodeType();$clinit_PortSide();const arr=list=>{const result=[],it=list.iterator_0();while(it.hasNext_0())result.push(it.next_1());return result;},result=[];
 for(const variant of input.variants){
  const g=new LGraph,nodes=new Map,ports=new Map,names=new Map;
  for(const name of input.nodeOrder){const n=new LNode(g);n.type_0=NORMAL;$add_3(g.layerlessNodes,n);nodes.set(name,n);names.set(n,name);for(const side of ['in','out']){const p=new LPort;$setNode(p,n);$setSide(p,side==='in'?WEST_2:EAST_2);ports.set(name+':'+side,p);}}
  input.edges.forEach(([a,b],index)=>{const e=new LEdge;e.id_0=index;$setSource_0(e,ports.get(a+':out'));$setTarget_0(e,ports.get(b+':in'));});
  const layerless=g.layerlessNodes,layers=g.layers,owner=variant==='LONGEST_PATH'?new LongestPathLayerer:new LongestPathSourceLayerer,cfg=owner.getLayoutProcessorConfiguration(g),rawConfiguration=cfg.list.array.map(slot=>arr(slot).map(p=>({name:p.name_0,ordinal:p.ordinal}))),monitor=new BasicProgressMonitor;
  owner.process(g,monitor);
  result.push({variant,layers:g.layers.array.map(layer=>layer.nodes.array.map(n=>names.get(n))),ids:[...nodes].map(([name,n])=>({name,id:n.id_0,layer:g.layers.array.indexOf(n.layer)})),sameLayerless:layerless===g.layerlessNodes,sameLayers:layers===g.layers,layerlessCount:g.layerlessNodes.array.length,ownerGraphCleared:owner.layeredGraph===null,ownerHeightsCleared:owner.nodeHeights===null,monitorName:monitor.getTaskName(),monitorRunning:monitor.isRunning(),monitorClosed:monitor.closed_0,rawConfiguration,configurationByOrdinal:rawConfiguration.map(slot=>slot.slice().sort((a,b)=>a.ordinal-b.ordinal).map(p=>p.name))});
 }
 return result;
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(fs.readFileSync(requestPath)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__longestPath(request),actualLayerersExecuted:true,layoutExecuted:false,nativeExecuted:false},null,2)+'\n',{flag:'wx'});
