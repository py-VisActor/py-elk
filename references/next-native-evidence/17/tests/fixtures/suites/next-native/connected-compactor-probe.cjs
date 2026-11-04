const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),req=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__connectedCompactor=function(request){
 getInstance();$clinit_InternalProperties_1();$clinit_LayeredOptions();$clinit_PortSide();$clinit_LNode$NodeType();
 const sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2},array=c=>{const a=[],i=c.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;};
 const num=v=>Number.isNaN(v)?'NaN':!Number.isFinite(v)?String(v):Object.is(v,-0)?'-0':v,point=v=>[num(v.x_0),num(v.y_0)],box=r=>[r.x_0,r.y_0,r.width_0,r.height].map(num);
 const setSides=names=>{const a=$getEnumConstants(Lorg_eclipse_elk_core_options_PortSide_2_classLit),s=new EnumSet$EnumSetImpl(a,createFrom(a,a.length),0);for(const n of names)s.add_2(sides[n]);return s;};
 return request.cases.map(c=>{
  const graphs=new ArrayList,originalNodes=[],nodeRefs=[],originalEdges=[];
  for(const input of c.graphs){
   const g=new LGraph,nodes={},ports={};$setProperty_0(g,EXT_PORT_CONNECTIONS,setSides(input.sides));
   for(const item of input.nodes){const n=new LNode(g);n.pos.x_0=item.pos[0];n.pos.y_0=item.pos[1];n.size_0.x_0=item.size[0];n.size_0.y_0=item.size[1];[n.margin.top_0,n.margin.right,n.margin.bottom,n.margin.left]=item.margin;n.type_0=item.type==='NORMAL'?NORMAL:EXTERNAL_PORT;if(item.side)$setProperty_0(n,EXT_PORT_SIDE,sides[item.side]);$add_3(g.layerlessNodes,n);nodes[item.id]=n;originalNodes.push(n);nodeRefs.push([n.pos,n.size_0]);}
   for(const item of input.ports){const p=new LPort;$setNode(p,nodes[item.owner]);p.size_0.x_0=item.size[0];p.size_0.y_0=item.size[1];$setSide(p,sides[item.side]);[p.pos.x_0,p.pos.y_0]=item.pos;[p.anchor.x_0,p.anchor.y_0]=item.anchor;ports[item.id]=p;}
   for(const item of input.edges){const e=new LEdge;$setSource_0(e,ports[item.source]);$setTarget_0(e,ports[item.target]);for(const v of item.bends)$add_7(e.bendPoints,new KVector_1(...v));const l=new LLabel;l.text_0=item.id;[l.pos.x_0,l.pos.y_0]=item.labelPos;$add_3(e.labels,l);$setProperty_0(e,EDGE_THICKNESS_0,item.thickness);originalEdges.push(e);}
   $add_3(graphs,g);
  }
  const compactor=new ComponentsCompactor,prepared=[],saved=$transformLGraph;
  $transformLGraph=function(owner,g){const result=saved(owner,g);prepared.push({regularFlag:result.containsRegularNodes,regularFlagType:typeof result.containsRegularNodes,hull:result.rectilinearConvexHull.array.map(box),extensions:result.externalExtensions.array.map(e=>({side:e.side.name_0,rectangle:box(e.extension),placeholder:box(e.placeholder),edgeCount:e.edges.map_0.size_1()}))});return result;};
  let failure=null;
  try{$compact_5(compactor,graphs,c.spacing);}catch(e){failure={name:e.name,message:e.message};}finally{$transformLGraph=saved;}
  const allNodes=graphs.array.flatMap(g=>g.layerlessNodes.array),edges=[];for(const n of allNodes)for(const p of n.ports.array)for(const e of p.outgoingEdges.array)if(!edges.includes(e))edges.push(e);
  const original=originalEdges[0],fake=new LEdge;$setSource_0(fake,original.source);$setTarget_0(fake,original.target);const label=new LLabel;label.text_0='invalid-control';$add_3(fake.labels,label);let invalidError=null;
  if(original.source.owner.type_0===NORMAL&&original.target.owner.type_0===NORMAL){try{new ComponentsCompactor$InternalExternalExtension(fake);}catch(e){invalidError=e.__java$exception&&e.__java$exception.detailMessage||String(e);}}
  $setSource_0(fake,null);$setTarget_0(fake,null);
  return {name:c.name,failed:failure!==null,error:failure,prepared,graphTopLeft:point(compactor.graphTopLeft),graphBottomRight:point(compactor.graphBottomRight),size:failure?null:point(compactor.compactedGraphSize),offset:failure?null:point(compactor.yetAnotherOffset),sizeReferenceSame:failure?null:compactor.compactedGraphSize===compactor.compactor.transformer.graphSize,
   graphs:graphs.array.map(g=>({size:point(g.size_0),offset:point(g.offset),nodes:g.layerlessNodes.array.map(n=>({type:n.type_0.name_0,pos:point(n.pos),size:point(n.size_0),ports:n.ports.array.map(p=>({pos:point(p.pos),anchor:point(p.anchor),side:p.side.name_0}))}))})),
   edges:edges.map(e=>({sourceNode:allNodes.indexOf(e.source.owner),targetNode:allNodes.indexOf(e.target.owner),bends:array(e.bendPoints).map(point),labels:e.labels.array.map(l=>point(l.pos)),hasJunction:$hasProperty(e,JUNCTION_POINTS),junctions:$hasProperty(e,JUNCTION_POINTS)?array($getProperty(e,JUNCTION_POINTS)).map(point):null})),
   originalNodeReferences:originalNodes.map((n,i)=>n.pos===nodeRefs[i][0]&&n.size_0===nodeRefs[i][1]),invalidError};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(req),pid:process.pid,parentPid:process.ppid,value:global.__connectedCompactor(JSON.parse(req)),actualConnectedCompactor:true,inputGeometryExplicitlySupplied:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
