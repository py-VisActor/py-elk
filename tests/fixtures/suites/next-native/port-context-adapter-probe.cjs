// Focused original LPortAdapter view: NS dummy raw adjacency is intentionally
// hidden by the real transparent adapter. No algorithm or view is emulated.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__contextProbe=function(){
 $clinit_CoreOptions();$clinit_PortSide();$clinit_PortLabelPlacement();$clinit_LNode$NodeType();
 const n=new LNode(new LGraph);n.type_0=NORTH_SOUTH_PORT;
 $setProperty(n,PORT_LABELS_PLACEMENT_5,of_2(OUTSIDE_0,[NEXT_TO_PORT_IF_POSSIBLE_0]));
 const p=new LPort;$setNode(p,n);p.side=NORTH_3;$add_3(p.outgoingEdges,new LEdge);
 const ctx=new NodeContext(new LGraphAdapters$LNodeAdapter(null,n,true));
 const adapted=new LGraphAdapters$LPortAdapter(p,true),pc=new PortContext(ctx,adapted);
 return {nodeType:n.type_0.name_0,rawIncomingCount:p.incomingEdges.array.length,rawOutgoingCount:p.outgoingEdges.array.length,adaptedIncomingCount:adapted.getIncomingEdges().size_1(),adaptedOutgoingCount:adapted.getOutgoingEdges().size_1(),labelsNextToPort:pc.labelsNextToPort};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-node-context-adapter-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,result:global.__contextProbe(),candidateExecuted:false,mode:'original-transparent-adapter-object-primitive'},null,2)+'\n',{flag:'wx'});
