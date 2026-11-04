// Actual ComponentsProcessor split/combine over prepared LGraphs; no phase math.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__componentsGeneral=function(request){
 registerLayoutAlgorithms(['layered']);$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_LNode$NodeType();
 const list=c=>{const a=[],it=c.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const point=v=>[v.x_0,v.y_0];
 return request.cases.map(c=>{
  const g=new LGraph,cfg=optsToCfg(new JSONObject_0(c.options));$applyProperties(cfg,g,$configure(cfg,Lorg_eclipse_elk_graph_ElkNode_2_classLit));
  const random=new Random_0(7),processors=new ArrayList;$setProperty_0(g,RANDOM_0,random);$setProperty_0(g,PROCESSORS,processors);
  g.padding.top_0=1;g.padding.right=2;g.padding.bottom=3;g.padding.left=4;
  const nodes=c.nodes.map((row,i)=>{const n=new LNode(g);n.id_0=i;n.pos.x_0=i;n.pos.y_0=-i;n.size_0.x_0=10+i;n.size_0.y_0=20+i;
   if(row.priority!==undefined)$setProperty_0(n,PRIORITY_0,valueOf_3(row.priority));
   if(row.order!==undefined)$setProperty_0(n,MODEL_ORDER_2,valueOf_3(row.order));
   $add_3(g.layerlessNodes,n);return n;});
  const ports=c.nodes.map((row,i)=>Array.from({length:row.ports||1},()=>{const p=new LPort;$setNode(p,nodes[i]);return p;}));
  const edges=c.edges.map((r,i)=>{const e=new LEdge;e.id_0=i;$setSource_0(e,ports[r[0]][r[1]]);$setTarget_0(e,ports[r[2]][r[3]]);$addLast_0(e.bendPoints,new KVector_1(i+1,i+2));const label=new LLabel;label.pos.x_0=i+3;label.pos.y_0=i+4;$add_3(e.labels,label);return e;});
  if(c.external){const all=$getEnumConstants(Lorg_eclipse_elk_alg_layered_options_GraphProperties_2_classLit),props=new EnumSet$EnumSetImpl(all,createFrom(all,all.length),0);props.add_2(EXTERNAL_PORTS);$setProperty_0(g,GRAPH_PROPERTIES,props);}
  const seed=$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.randomSeed'),seedBox=$getProperty(g,seed),originalMinimum=$hasProperty(g,NODE_SIZE_MINIMUM_0)?$getProperty(g,NODE_SIZE_MINIMUM_0):null,processor=new ComponentsProcessor_0,components=$split_2(processor,g);
  const split=list(components).map(h=>({nodeOrder:list(h.layerlessNodes).map(n=>nodes.indexOf(n)),sameGraph:h===g,paddingSame:h.padding===g.padding,
   minimumPresent:$hasProperty(h,NODE_SIZE_MINIMUM_0),integerBoxShared:$getProperty(h,seed)===seedBox,randomShared:$getProperty(h,RANDOM_0)===random,processorsShared:$getProperty(h,PROCESSORS)===processors,
   nodeOwners:list(h.layerlessNodes).every(n=>n.graph_0===h),externalConnections:$hasProperty(h,EXT_PORT_CONNECTIONS)?list($getProperty(h,EXT_PORT_CONNECTIONS)).map(v=>v.name_0):null}));
  list(components).forEach((h,i)=>{h.size_0.x_0=20+15*i;h.size_0.y_0=10+5*i;h.offset.x_0=i-1;h.offset.y_0=2-i;});
  $combine(processor,components,g);
  return {name:c.name,split,componentOrderAfterCombine:list(components).map(h=>split[list(components).indexOf(h)]&&list(h.layerlessNodes).map(n=>nodes.indexOf(n))),
   targetNodes:list(g.layerlessNodes).map(n=>({index:nodes.indexOf(n),pos:point(n.pos),targetOwner:n.graph_0===g})),
   edgeBends:edges.map(e=>list(e.bendPoints).map(point)),edgeLabels:edges.map(e=>list(e.labels).map(l=>point(l.pos))),
   junctionPresence:edges.map(e=>$hasProperty(e,JUNCTION_POINTS)),
   size:point(g.size_0),minimumRetained:originalMinimum!==null?$getProperty(g,NODE_SIZE_MINIMUM_0)===originalMinimum:null,
   randomShared:$getProperty(g,RANDOM_0)===random,processorsShared:$getProperty(g,PROCESSORS)===processors};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation:global.__componentsGeneral(JSON.parse(requestRaw)),fullLayoutExecuted:false,actualSplitAndCombineExecuted:true,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
