// Source SweepCopy constructor alias depth only; no transfer/counter/sweep.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__sweepCopy=function(s){
 const graph=new LGraph,nodes={},nodeNames=new Map,portNames=new Map;
 const order=s.layers.map((ids,i)=>{const layer=new Layer(graph);layer.id_0=i;return stampJavaTypeInfo(getClassLiteralForArray(Lorg_eclipse_elk_alg_layered_graph_LNode_2_classLit,1),$intern_108,9,0,ids.map((name,j)=>{const n=new LNode(graph);$setLayer(n,j,layer);nodes[name]=n;nodeNames.set(n,name);for(const id of s.ports[name]){const p=new LPort;$setNode(p,n);portNames.set(p,id);}return n;}));});
 const first=new SweepCopy_0(order),second=new SweepCopy(first);
 const nodeOrder=c=>c.nodeOrder.map(layer=>layer.map(n=>nodeNames.get(n)));
 const portOrders=c=>c.portOrders.array.map(layer=>layer.array.map(ps=>ps.array.map(p=>portNames.get(p))));
 const before={nodeOrder:nodeOrder(first),portOrders:portOrders(first),inputOuterIndependent:first.nodeOrder!==order,inputLayerIndependent:first.nodeOrder[0]!==order[0],sameNode:first.nodeOrder[0][0]===nodes.a,copyNodeOuterIndependent:second.nodeOrder!==first.nodeOrder,copyNodeLayerIndependent:second.nodeOrder[0]!==first.nodeOrder[0],copyPortOuterIndependent:second.portOrders!==first.portOrders,copyPortLayerShared:second.portOrders.array[0]===first.portOrders.array[0],copyPortListShared:second.portOrders.array[0].array[0]===first.portOrders.array[0].array[0]};
 order[0].reverse();nodes.a.ports.array.reverse();const afterOriginalEdits={firstNodes:nodeOrder(first),firstPorts:portOrders(first),inputNodes:order.map(l=>l.map(n=>nodeNames.get(n))),originalAPorts:nodes.a.ports.array.map(p=>portNames.get(p))};
 const extra=new LPort;portNames.set(extra,'capturedOnly');$add_3(first.portOrders.array[0].array[0],extra);$add_3(first.portOrders,new ArrayList);first.nodeOrder[0].reverse();
 return {before,afterOriginalEdits,afterCopyEdits:{firstNodes:nodeOrder(first),secondNodes:nodeOrder(second),firstPorts:portOrders(first),secondPorts:portOrders(second),originalAPorts:nodes.a.ports.array.map(p=>portNames.get(p))},transferExecuted:false,counterExecuted:false,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__sweepCopy(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-sweep-copy-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
