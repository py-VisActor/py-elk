// Actual reversal/pre/post helpers; prepared layer/hidden inputs are explicit.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__generalConstraints=function(s){
 getInstance();$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_LayerConstraint();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_PortConstraints();$clinit_LayerConstraintPreprocessor();
 const list=c=>c.array.slice(),constraints={NONE:NONE_7,FIRST,LAST,FIRST_SEPARATE:FIRST_SEPARATE_0,LAST_SEPARATE:LAST_SEPARATE_0};
 return {cases:s.cases.map(item=>{
  const g=new LGraph,nodes={},ports={},edges={},nodeNames=new Map,portNames=new Map,edgeNames=new Map,events=[];
  for(const v of item.nodes){const n=new LNode(g);nodes[v.id]=n;nodeNames.set(n,v.id);n.type_0=v.type==='LABEL'?LABEL:v.type==='EXTERNAL_PORT'?EXTERNAL_PORT:NORMAL;$add_3(g.layerlessNodes,n);
   if(v.constraint!==undefined)$setProperty_0(n,LAYERING_LAYER_CONSTRAINT_0,constraints[v.constraint]);
   if(v.portConstraints)$setProperty_0(n,PORT_CONSTRAINTS_0,FIXED_SIDE);
   const p=new LPort;$setSide(p,EAST_2);$setNode(p,n);ports[v.id]=p;portNames.set(p,v.id+':p');}
  for(const[id,a,b,reversed]of item.edges){const e=new LEdge;edges[id]=e;edgeNames.set(e,id);$setSource_0(e,ports[a]);if(b!==null)$setTarget_0(e,ports[b]);if(reversed)$setProperty_0(e,REVERSED,true);}
  const view=()=>({layerless:list(g.layerlessNodes).map(n=>nodeNames.get(n)),layers:list(g.layers).map(l=>list(l.nodes).map(n=>nodeNames.get(n))),
   nodes:item.nodes.map(v=>{const n=nodes[v.id];return {id:v.id,hasConstraint:$hasProperty(n,LAYERING_LAYER_CONSTRAINT_0),constraint:$getProperty(n,LAYERING_LAYER_CONSTRAINT_0).name_0,edgeConstraint:$hasProperty(n,EDGE_CONSTRAINT)?$getProperty(n,EDGE_CONSTRAINT).name_0:null,connection:$hasProperty(n,HIDDEN_NODE_CONNECTIONS)?$getProperty(n,HIDDEN_NODE_CONNECTIONS).name_0:null,incoming:list(ports[v.id].incomingEdges).map(e=>edgeNames.get(e)),outgoing:list(ports[v.id].outgoingEdges).map(e=>edgeNames.get(e))};}),
   edges:item.edges.map(([id])=>{const e=edges[id];return{id,source:e.source?portNames.get(e.source):null,target:e.target?portNames.get(e.target):null,reversed:$hasProperty(e,REVERSED)?$getProperty(e,REVERSED):null,originalOpposite:$hasProperty(e,ORIGINAL_OPPOSITE_PORT)?portNames.get($getProperty(e,ORIGINAL_OPPOSITE_PORT)):null};}),hidden:$hasProperty(g,HIDDEN_NODES)?list($getProperty(g,HIDDEN_NODES)).map(n=>nodeNames.get(n)):null});
  const monitor={begin:(name,total)=>events.push({kind:'begin',name,total}),done_1:()=>events.push({kind:'done'})};let beforePost=null,visits=[];
  if(item.kind==='reverse')$process_7(g,monitor);
  else{
   if(item.kind==='hideRestore'){$process_32(g,monitor);beforePost=view();const layer=new Layer(g);$add_3(g.layers,layer);for(const n of list(g.layerlessNodes))$setLayer_0(n,layer);g.layerlessNodes.array.length=0;}
   else{const hidden=new ArrayList;$add_3(hidden,nodes.F);$setProperty_0(g,HIDDEN_NODES,hidden);$setProperty_0(edges.loop,ORIGINAL_OPPOSITE_PORT,ports.F);g.layerlessNodes.array.length=0;}
   const saved=$next_6;$next_6=function(it){const value=saved(it);if(item.kind==='postSelfLoop'&&(it.this$01===ports.F.incomingEdges||it.this$01===ports.F.outgoingEdges))visits.push(edgeNames.get(value));return value;};
   try{$process_31(g,monitor);}finally{$next_6=saved;}
  }
  return{id:item.id,events,beforePost,after:view(),visits,suppliedPostLayers:item.kind==='hideRestore',preparedHiddenNodes:!!item.preparedHiddenNodes};
 }),layoutExecuted:false,workingGraphHelpersExecuted:true};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__generalConstraints(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-general-constraints/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
