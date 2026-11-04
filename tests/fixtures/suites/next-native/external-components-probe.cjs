// Actual ComponentsProcessor split and selected external placer, no phase math.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__externalComponents=function(request){
 registerLayoutAlgorithms(['layered']);$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_GraphProperties();
 const list=c=>{const a=[],it=c.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const point=p=>[p.x_0,p.y_0],sideValues={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2};
 return request.cases.map(c=>{
  const g=new LGraph,cfg=optsToCfg(new JSONObject_0(c.options));$applyProperties(cfg,g,$configure(cfg,Lorg_eclipse_elk_graph_ElkNode_2_classLit));
  const all=$getEnumConstants(Lorg_eclipse_elk_alg_layered_options_GraphProperties_2_classLit),props=new EnumSet$EnumSetImpl(all,createFrom(all,all.length),0);props.add_2(EXTERNAL_PORTS);$setProperty_0(g,GRAPH_PROPERTIES,props);
  const nodes=[],names=new Map;let serial=0;
  function make(){const n=new LNode(g);names.set(n,serial++);nodes.push(n);$add_3(g.layerlessNodes,n);n.pos.x_0=serial/4;n.pos.y_0=-serial/2;return n;}
  c.sides.forEach((s,i)=>{
   const n=make(),p=new LPort;$setNode(p,n);$setProperty_0(n,MODEL_ORDER_2,valueOf_3(c.sides.length-i));
   for(const side of s){const ext=make();ext.type_0=EXTERNAL_PORT;$setProperty_0(ext,EXT_PORT_SIDE,sideValues[side]);const ep=new LPort;$setNode(ep,ext);const e=new LEdge;$setSource_0(e,p);$setTarget_0(e,ep);}
  });
  const processor=new ComponentsProcessor_0,components=$split_2(processor,g),parts=list(components);
  parts.forEach((h,i)=>{h.size_0.x_0=11.5+3*i;h.size_0.y_0=7+2.25*i;h.offset.x_0=.25*i-1;h.offset.y_0=-.75*i;});
  const split=parts.map(h=>({nodes:list(h.layerlessNodes).map(n=>names.get(n)),sides:list($getProperty(h,EXT_PORT_CONNECTIONS)).map(s=>s.name_0)}));
  $combine(processor,components,g);
  const placer=processor.graphPlacer,groups=placer.componentGroups?list(placer.componentGroups).map(group=>({
   values:list($values(group.components)).map(h=>parts.indexOf(h)),
   keys:list(group.components.map_0.keySet_0()).map(k=>list(k).map(s=>s.name_0)),
   componentOrder:group.componentOrder?list(group.componentOrder).map(h=>parts.indexOf(h)):null})):null;
  return {name:c.name,split,size:point(g.size_0),nodes:list(g.layerlessNodes).map(n=>({id:names.get(n),pos:point(n.pos),targetOwner:n.graph_0===g})),groups};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation:global.__externalComponents(JSON.parse(requestRaw)),layoutExecuted:false,actualSplitAndExternalPlacerExecuted:true,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
