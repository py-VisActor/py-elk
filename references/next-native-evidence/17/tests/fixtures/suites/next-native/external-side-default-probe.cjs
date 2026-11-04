const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__externalSide=function(){
 getInstance();$clinit_InternalProperties_1();$clinit_LNode$NodeType();
 const arr=c=>{const a=[],i=c.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;},num=v=>Object.is(v,-0)?'-0':v,point=v=>[num(v.x_0),num(v.y_0)];
 return [false,true].map(physicalNull=>{
  const graph=new LGraph,node=new LNode(graph);node.type_0=EXTERNAL_PORT;node.pos.x_0=5;node.pos.y_0=7;$add_3(graph.layerlessNodes,node);
  const port=new LPort;$setNode(port,node);if(physicalNull){node.propertyMap=new HashMap;$put_6(node.propertyMap,EXT_PORT_SIDE,null);}
  const before=$hasProperty(node,EXT_PORT_SIDE),originalPos=node.pos,graphs=new ArrayList;$add_3(graphs,graph);const owner=new ComponentsCompactor;
  $compact_5(owner,graphs,3);
  const edge=port.outgoingEdges.array[0],extension=new ComponentsCompactor$InternalExternalExtension(edge);
  return {physicalNull,before,after:$hasProperty(node,EXT_PORT_SIDE),side:$getProperty(node,EXT_PORT_SIDE).name_0,extensionSide:extension.externalPortSide.name_0,extensionDirection:extension.getDirection().name_0,representorNullish:extension.getRepresentor()==null,
   size:point(owner.compactedGraphSize),offset:point(owner.yetAnotherOffset),nodes:graph.layerlessNodes.array.map(n=>({type:n.type_0.name_0,pos:point(n.pos),size:point(n.size_0)})),bends:arr(edge.bendPoints).map(point),originalPosSame:node.pos===originalPos,graphConnectionsAbsent:!$hasProperty(graph,EXT_PORT_CONNECTIONS)};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),value:global.__externalSide(),pid:process.pid,parentPid:process.ppid,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
