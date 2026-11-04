// Actual cleanup in layout_1 with empty processors, then actual resizeGraph.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__resizeGeneral=function(request){
 registerLayoutAlgorithms(['layered']);$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_LNode$NodeType();
 const list=c=>{const a=[],it=c.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const number=v=>Object.is(v,-0)?'-0':Number.isNaN(v)?'NaN':v;
 const point=v=>[number(v.x_0),number(v.y_0)];
 return request.cases.map(c=>{
  const g=new LGraph;g.size_0.x_0=c.size[0];g.size_0.y_0=c.size[1];g.offset.x_0=c.offset[0];g.offset.y_0=c.offset[1];
  [g.padding.top_0,g.padding.right,g.padding.bottom,g.padding.left]=c.padding;
  const cfg=optsToCfg(new JSONObject_0(c.options));$applyProperties(cfg,g,$configure(cfg,Lorg_eclipse_elk_graph_ElkNode_2_classLit));
  const sides=['UNDEFINED','WEST','EAST','NORTH','SOUTH'],nodes=[],layers=[];
  for(let i=0;i<5;i++){
   const n=new LNode(g);n.id_0=i;n.pos.x_0=i-2;n.pos.y_0=i+1;nodes.push(n);
   if(i){n.type_0=EXTERNAL_PORT;$setProperty_0(n,EXT_PORT_SIDE,PortSide_map(sides[i]));}
   if(i<2)$add_3(g.layerlessNodes,n);else{const layer=new Layer(g);layers.push(layer);$add_3(g.layers,layer);$setLayer(n,0,layer);}
  }
  if(c.external){$clinit_GraphProperties();const all=$getEnumConstants(Lorg_eclipse_elk_alg_layered_options_GraphProperties_2_classLit),props=new EnumSet$EnumSetImpl(all,createFrom(all,all.length),0);props.add_2(EXTERNAL_PORTS);$setProperty_0(g,GRAPH_PROPERTIES,props);}
  const beforeMinimum=$hasProperty(g,NODE_SIZE_MINIMUM_0),sourceSize=g.size_0,sourceOffset=g.offset;
  $setProperty_0(g,PROCESSORS,new ArrayList);$layout_1(g,new BasicProgressMonitor);$resizeGraph(g);
  const minimum=$hasProperty(g,NODE_SIZE_MINIMUM_0)?$getProperty(g,NODE_SIZE_MINIMUM_0):null;
  return {name:c.name,size:point(g.size_0),offset:point(g.offset),sameSize:sourceSize===g.size_0,sameOffset:sourceOffset===g.offset,
    minimumBefore:beforeMinimum,minimumAfter:$hasProperty(g,NODE_SIZE_MINIMUM_0),minimum:minimum?point(minimum):null,
    nodes:list(g.layerlessNodes).map(n=>({id:n.id_0,pos:point(n.pos),layerNull:n.layer===null})),layers:g.layers.array.length,oldLayerNodeCounts:layers.map(l=>l.nodes.array.length)};
 });
 function PortSide_map(name){return name==='WEST'?WEST_2:name==='EAST'?EAST_2:name==='NORTH'?NORTH_3:SOUTH_2;}
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation:global.__resizeGeneral(JSON.parse(requestRaw)),fullLayoutExecuted:false,actualCleanupAndResizeExecuted:true,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
