// Actual SortByInputModel working-graph phase, independent source-first input.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__inputModelSort=function(s){
 getInstance();$clinit_PortSide();$clinit_PortConstraints();$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_OrderingStrategy();
 const g=new LGraph,nodes={},ports={},nodeIds=new Map,portIds=new Map;
 const constraints={UNDEFINED:UNDEFINED_4,FREE:FREE,FIXED_SIDE:FIXED_SIDE,FIXED_ORDER:FIXED_ORDER,FIXED_RATIO:FIXED_RATIO,FIXED_POS:FIXED_POS};
 for(const item of s.nodes){const n=new LNode(g);nodes[item.id]=n;nodeIds.set(n,item.id);$setProperty_0(n,MODEL_ORDER_2,valueOf_3(item.order));$setProperty_0(n,PORT_CONSTRAINTS_0,constraints[item.constraint]);$add_3(n.labels,new LLabel_0(item.id));
  for(const [id,order] of item.ports){const p=new LPort;ports[id]=p;portIds.set(p,id);$setNode(p,n);$setSide(p,item.side==='EAST'?EAST_2:WEST_2);$setProperty_0(p,MODEL_ORDER_2,valueOf_3(order));$add_3(p.labels,new LLabel_0(id));}}
 for(const item of s.nodes){if(!instanceOf($getProperty(nodes[item.id],PORT_CONSTRAINTS_0),106))throw Error('PortConstraints enum required');}
 s.layers.forEach((ids,i)=>{const layer=new Layer(g);layer.id_0=20+i;$add_3(g.layers,layer);ids.forEach((id,j)=>$setLayer(nodes[id],j,layer));});
 for(const [a,b,order] of s.edges){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);$setProperty_0(e,MODEL_ORDER_2,valueOf_3(order));}
 $setProperty_0(g,MAX_MODEL_ORDER_NODES,valueOf_3(s.nodes.length));$setProperty_0(g,CONSIDER_MODEL_ORDER_STRATEGY_0,PREFER_NODES);$setProperty_0(g,CONSIDER_MODEL_ORDER_PORT_MODEL_ORDER_0,true);
 const events=[],saved=insertionSort_0;
 insertionSort_0=function(row,cmp){const big=cmp.biggerThan,small=cmp.smallerThan,before=row.array.map(n=>nodeIds.get(n)),previous=cmp.previousLayer.map(n=>nodeIds.get(n));saved(row,cmp);events.push({kind:'insertion',beforePorts:cmp.beforePorts,before,previous,after:row.array.map(n=>nodeIds.get(n)),newCaches:cmp.biggerThan!==big&&cmp.smallerThan!==small,cacheSizes:[cmp.biggerThan.size_1(),cmp.smallerThan.size_1()]});};
 const monitor={begin:(name,total)=>events.push({kind:'begin',name,total}),log_0:text=>events.push({kind:'log',text}),done_1:()=>events.push({kind:'done'})};
 try{$process_52(g,monitor);}finally{insertionSort_0=saved;}
 return {events,layers:g.layers.array.map(l=>({id:l.id_0,nodes:l.nodes.array.map(n=>nodeIds.get(n))})),ports:s.nodes.map(item=>({id:item.id,ports:nodes[item.id].ports.array.map(p=>portIds.get(p))})),layoutExecuted:false,workingGraphPhaseExecuted:true,suppliedInternalModelOrder:true};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__inputModelSort(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-input-model-sort-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
