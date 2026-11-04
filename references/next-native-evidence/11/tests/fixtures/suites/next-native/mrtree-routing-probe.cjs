// New object-level compaction/router/boxed-level/mean observations. No public
// provider, NodeMicroLayout or old stage oracle is executed by this bridge.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__treeRouting=function(s){
 $clinit_MrTreeOptions();$clinit_InternalProperties_2();$clinit_Direction_0();$clinit_EdgeRoutingMode();
 const list=l=>{const a=[],it=l.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const g=new TGraph,nodes=[],names=new Map;
 $setProperty_0(g,DIRECTION_0,{RIGHT:RIGHT_6,LEFT:LEFT_6,DOWN:DOWN_1,UP:UP_1}[s.direction]);
 $setProperty_0(g,COMPACTION_0,s.compaction===true);
 $setProperty_0(g,EDGE_ROUTING_MODE_0,{AVOID_OVERLAP,MIDDLE_TO_MIDDLE,NONE:NONE_12}[s.mode]);
 $setProperty_0(g,SPACING_NODE_NODE_1,s.spacing||20);
 for(const [i,spec]of s.nodes.entries()){
  const n=new TNode(i,g,'n'+i);[n.pos.x_0,n.pos.y_0]=spec.pos;[n.size_0.x_0,n.size_0.y_0]=spec.size;
  $setProperty_0(n,TREE_LEVEL_0,valueOf_3(spec.level));if(i===0)$setProperty_0(n,ROOT_0,true);
  nodes.push(n);names.set(n,'n'+i);$add_7(g.nodes,n);
 }
 for(const spec of s.edges){const e=new TEdge_0(nodes[spec[0]],nodes[spec[1]]);$add_7(g.edges,e);$add_7(e.source.outgoingEdges,e);$add_7(e.target.incomingEdges,e);for(const p of spec[2]||[])$addLast_0(e.bendPoints,new KVector_1(p[0],p[1]));}
 const snap=()=>({nodes:list(g.nodes).map(n=>({id:n.id_0,pos:[n.pos.x_0,n.pos.y_0],level:$getProperty(n,TREE_LEVEL_0).value_0,constraints:list($getProperty(n,COMPACT_CONSTRAINTS)).map(v=>v.id_0)})),edges:list(g.edges).map(e=>({source:e.source.id_0,target:e.target.id_0,bends:list(e.bendPoints).map(v=>[v.x_0,v.y_0])}))});
 const result={before:snap()};$process_87(new CompactionProcessor,g,new BasicProgressMonitor);result.compacted=snap();$process_91(g,new BasicProgressMonitor);$process_101(g,new BasicProgressMonitor);result.routed=snap();return result;
};
global.__treeBoxed=function(level){
 $clinit_MrTreeOptions();const g=new TGraph,a=new TNode(1,g,'a'),b=new TNode(2,g,'b'),e=new TEdge_0(a,b);
 $setProperty_0(a,TREE_LEVEL_0,valueOf_3(level));$setProperty_0(b,TREE_LEVEL_0,valueOf_3(level));$add_7(g.nodes,a);$add_7(g.nodes,b);$add_7(g.edges,e);
 return {sameBox:$getProperty(a,TREE_LEVEL_0)===$getProperty(b,TREE_LEVEL_0),outgoingCount:getAllOutgoingEdges(a,g).array.length,incomingCount:getAllIncomingEdges(b,g).array.length};
};
global.__treeMean=function(values){const stats=new DoubleSummaryStatistics;for(const v of values)$accept(stats,v);const mean=$getSum(stats)/toDouble_0(stats.count);return {mean,secondAbove:values[1]>mean};};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const request=JSON.parse(requestRaw),result={cases:request.cases.map(s=>({id:s.id,value:global.__treeRouting(s)})),boxed:request.boxed.map(level=>({level,value:global.__treeBoxed(level)})),mean:global.__treeMean(request.mean)};
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-tree-routing-observation/v1',mode:'unchanged-worker-prepared-stage-object-adapter',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,...result,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
