const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const raw=fs.readFileSync(worker),req=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__componentCompaction=function(request){
 getInstance();$clinit_InternalProperties_1();$clinit_PortSide();$clinit_Direction_0();
 const sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2};
 const array=c=>{const a=[],i=c.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;};
 const num=v=>Number.isNaN(v)?'NaN':!Number.isFinite(v)?String(v):Object.is(v,-0)?'-0':v;
 const point=v=>[num(v.x_0),num(v.y_0)],box=v=>[v.x_0,v.y_0,v.width_0,v.height].map(num);
 const sideSet=names=>{const a=$getEnumConstants(Lorg_eclipse_elk_core_options_PortSide_2_classLit),s=new EnumSet$EnumSetImpl(a,createFrom(a,a.length),0);for(const name of names)s.add_2(sides[name]);return s;};
 const lockTable=[];
 for(let mask=0;mask<16;mask++){
  const names=Object.keys(sides).filter((_,i)=>mask&(1<<i)),node=new ComponentsToCGraphTransformer$CRectNode(new ComponentsToCGraphTransformer(5),new ElkRectangle_0(0,0,1,1)),lock=node.lock;
  $setLock(node,sideSet(names));lockTable.push({sides:names,values:[lock.left_0,lock.right_0,lock.up,lock.down],same:node.lock===lock});
 }
 const pairHashes=request.pairCodes.map(([a,b])=>(new Pair({hashCode_1:()=>a},{hashCode_1:()=>b})).hashCode_1());
 const value=request.cases.map(c=>{
  $clinit_OneDimensionalComponentsCompaction();
  const connected=new ComponentsCompactor$InternalConnectedComponents,components=[],extensions=[];
  for(const input of c.components){
   const g=new LGraph;$setProperty_0(g,EXT_PORT_CONNECTIONS,sideSet(input.sides));
   const component=new ComponentsCompactor$InternalComponent(g);component.rectilinearConvexHull=new ArrayList;
   for(const row of input.rectangles)$add_3(component.rectilinearConvexHull,new ElkRectangle_0(...row));
   for(const item of input.extensions){const e=new ComponentsCompactor$InternalUnionExternalExtension;e.side=sides[item.side];e.extension=new ElkRectangle_0(...item.rectangle);e.placeholder=item.placeholder?new ElkRectangle_0(...item.placeholder):null;$add_3(component.externalExtensions,e);extensions.push(e);}
   $add_3(connected.components,component);components.push(component);
  }
  const controller=new OneDimensionalComponentsCompaction;controller.transformer=new ComponentsToCGraphTransformer(c.spacing);controller.compactionGraph=$transform_0(controller.transformer,connected);
  const graph=controller.compactionGraph,groups=graph.cGroups,nodes=graph.cNodes,originals=components.map(x=>$get_10(controller.transformer.oldPosition,x)),passes=[],calls=[];
  const saved=[$compact_1,$compact_3];
  $compact_1=function(owner){const v=saved[0](owner);passes.push(num(v));return v;};
  $compact_3=function(owner){calls.push({direction:owner.direction.name_0,nodes:owner.cGraph.cNodes.array.length,groups:owner.cGraph.cGroups.array.length});return saved[1](owner);};
  try{$compact_2(controller);}finally{[$compact_1,$compact_3]=saved;}
  const placeholders=array($values(controller.transformer.externalPlaceholder));
  return {name:c.name,passes,calls,topLeft:point(controller.topLeft),bottomRight:point(controller.bottomRight),globalOffset:point(controller.transformer.globalOffset),graphSize:point(controller.transformer.graphSize),
   offsets:components.map(x=>point($getOffset_0(controller,x))),rectangles:components.map(x=>x.rectilinearConvexHull.array.map(box)),
   extensions:extensions.map(e=>({rect:box(e.extension),hitbox:box($get_10(controller.transformer.externalExtensions,e).second.hitbox)})),
   placeholders:placeholders.map(p=>({rect:box(p.second.rect),hitbox:box(p.second.hitbox),spacing:num(p.second.individualSpacing),groupSeparate:p.second.cGroup!==p.first})),
   originalPositionsSame:components.map((x,i)=>$get_10(controller.transformer.oldPosition,x)===originals[i]),
   listsSame:graph.cGroups===groups&&graph.cNodes===nodes,cleared:[groups.array.length,nodes.array.length],finished:controller.compactor.finished,direction:controller.compactor.direction.name_0};
 });return {value,lockTable,pairHashes};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(req),pid:process.pid,parentPid:process.ppid,node:process.version,...global.__componentCompaction(JSON.parse(req)),actualComponentController:true,geometryExplicitlySupplied:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
