// Object adapter only. Execute the actual fixed-worker tree stages and numeric
// dispatch, without provider micro-layout, complete routing or candidate code.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__treeStages=function(s){
 $clinit_MrTreeOptions();$clinit_InternalProperties_2();$clinit_Direction_0();$clinit_OrderWeighting();$clinit_TreeifyingOrder();
 const list=l=>{const a=[],it=l.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const g=new TGraph,nodes=[],names=new Map,edges=new Map,monitor=()=>new BasicProgressMonitor;
 $setProperty_0(g,SEARCH_ORDER_0,s.order==='BFS'?BFS:DFS);
 $setProperty_0(g,DIRECTION_0,{UNDEFINED:UNDEFINED_2,RIGHT:RIGHT_6,LEFT:LEFT_6,DOWN:DOWN_1,UP:UP_1}[s.direction||'DOWN']);
 $setProperty_0(g,SPACING_NODE_NODE_1,s.spacing===undefined?20:s.spacing);
 $setProperty_0(g,WEIGHTING_0,{MODEL_ORDER:MODEL_ORDER_3,FAN:FAN_0,DESCENDANTS:DESCENDANTS_0,CONSTRAINT}[s.weighting||'MODEL_ORDER']);
 for(const [i,spec]of s.nodes.entries()){
  const n=new TNode(99+i,g,'n'+i);[n.pos.x_0,n.pos.y_0]=spec.pos||[0,0];[n.size_0.x_0,n.size_0.y_0]=spec.size||[20,10];
  if(spec.constraint!==undefined)$setProperty_0(n,POSITION_CONSTRAINT_0,spec.constraint);
  nodes.push(n);names.set(n,'n'+i);$add_7(g.nodes,n);
 }
 for(const [i,[a,b]]of s.edges.entries()){const e=new TEdge_0(nodes[a],nodes[b]);edges.set(e,'e'+i);$add_7(g.edges,e);$add_7(e.source.outgoingEdges,e);$add_7(e.target.incomingEdges,e);}
 const snapshot=()=>{
  for(const n of list(g.nodes))if(!names.has(n))names.set(n,n.label_0);
  for(const [i,e]of list(g.edges).entries())if(!edges.has(e))edges.set(e,'dummy'+i);
  const propKeys={ROOT:ROOT_0,DUMMY,FAN,DESCENDANTS,ID,POSITION:POSITION_0,XCOOR,YCOOR,LEVELHEIGHT,PRELIM,MODIFIER,TREE_LEVEL:TREE_LEVEL_0};
  return {nodes:list(g.nodes).map(n=>({key:names.get(n),id:n.id_0,label:n.label_0,pos:[n.pos.x_0,n.pos.y_0],size:[n.size_0.x_0,n.size_0.y_0],incoming:list(n.incomingEdges).map(e=>edges.get(e)),outgoing:list(n.outgoingEdges).map(e=>edges.get(e)),properties:Object.fromEntries(Object.entries(propKeys).map(([name,key])=>[name,$getProperty(n,key)]))})),edges:list(g.edges).map(e=>({key:edges.get(e),source:names.get(e.source),target:names.get(e.target)})),eliminated:list($getProperty(g,REMOVABLE_EDGES)).map(e=>edges.get(e))};
 };
 const result={before:snapshot()};$process_98(new DFSTreeifyer,g,monitor());result.treeified=snapshot();$process_96(new RootProcessor,g,monitor());result.rooted=snapshot();
 if(s.walk){$process_89(new FanProcessor,g,monitor());$process_93(new LevelProcessor,g,monitor());$process_99(new NodeOrderer,g,monitor());$process_92(new LevelHeightProcessor,g,monitor());$process_94(new NeighborsProcessor,g,monitor());$process_100(new NodePlacer,g,monitor());result.placed=snapshot();$process_88(g,monitor());$process_95(new NodePositionProcessor,g,monitor());result.positioned=snapshot();}
 $process_97(g,monitor());result.restored=snapshot();return result;
};
global.__treeRound=v=>toInt_0(fromDouble_0($wnd.Math.round(v)));
`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const request=JSON.parse(requestRaw),special={NaN:NaN,Infinity:Infinity,'-Infinity':-Infinity};
const result={cases:request.cases.map(s=>({id:s.id,value:global.__treeStages(s)})),rounding:request.rounding.map(v=>({input:v,result:global.__treeRound(typeof v==='string'?special[v]:v)}))};
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-tree-stages-observation/v1',mode:'unchanged-worker-stage-object-adapter',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,...result,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
