const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__simplePlacement=function(input){
 $clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_GraphProperties();
 const properties={SPACING_NODE_NODE_0,SPACING_EDGE_NODE,SPACING_LABEL_PORT_VERTICAL},types={NORMAL,LONG_EDGE,LABEL,EXTERNAL_PORT},arr=list=>{const a=[],it=list.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;},owner=new SimpleNodePlacer,result=[];let initialConfiguration;
 for(const item of input.cases){
  const g=new LGraph,nodes=[];g.size_0.x_0=321;g.size_0.y_0=654;
  const all=castTo($getEnumConstants(Lorg_eclipse_elk_alg_layered_options_GraphProperties_2_classLit),10),flags=new EnumSet$EnumSetImpl(all,castTo(createFrom(all,all.length),10),0);for(const flag of item.flags)$add_5(flags,EXTERNAL_PORTS);$setProperty_0(g,GRAPH_PROPERTIES,flags);
  if(item.spacings){for(const [key,value]of Object.entries(item.spacings))$setProperty_0(g,properties[key],value);$setProperty_0(g,SPACINGS,new Spacings(g));}
  for(const l of item.layers){const layer=new Layer(g);$add_3(g.layers,layer);layer.size_0.x_0=l.width;layer.size_0.y_0=789;for(const n of l.nodes){const node=new LNode(g);node.type_0=types[n.type];node.pos.x_0=n.x;node.pos.y_0=-100;node.size_0.x_0=n.width;node.size_0.y_0=n.height;$set_6(node.margin,...n.margin);$setLayer_0(node,layer);if(n.individual){const holder=new MapPropertyHolder;for(const [key,value]of Object.entries(n.individual))$setProperty(holder,properties[key],value);$setProperty_0(node,SPACING_INDIVIDUAL,holder);}nodes.push([n.name,node]);}}
  const cfg=owner.getLayoutProcessorConfiguration(g),rawConfiguration=cfg===null?null:cfg.list.array.map(slot=>arr(slot).map(p=>({name:p.name_0,ordinal:p.ordinal})));if(cfg!==null)initialConfiguration=cfg;
  const monitor=new BasicProgressMonitor;owner.process(g,monitor);
  result.push({name:item.name,graphSize:[g.size_0.x_0,g.size_0.y_0],layerSizes:g.layers.array.map(l=>[l.size_0.x_0,l.size_0.y_0]),nodes:nodes.map(([name,node])=>({name,position:[node.pos.x_0,node.pos.y_0],size:[node.size_0.x_0,node.size_0.y_0]})),spacingHas:$hasProperty(g,SPACINGS),monitor:{name:monitor.getTaskName(),running:monitor.isRunning(),closed:monitor.closed_0},rawConfiguration,configurationByOrdinal:rawConfiguration===null?null:rawConfiguration.map(slot=>slot.slice().sort((a,b)=>a.ordinal-b.ordinal).map(p=>p.name)),sameConfiguration:cfg===null?null:(new SimpleNodePlacer).getLayoutProcessorConfiguration(g)===initialConfiguration});
 }
 return result;
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(fs.readFileSync(requestPath)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__simplePlacement(request),actualSimplePlacementExecuted:true,layoutExecuted:false,nativeExecuted:false},null,2)+'\n',{flag:'wx'});
