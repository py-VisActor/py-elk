const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const raw=fs.readFileSync(worker),req=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__orthogonalAxes=function(request){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_PortSide();
 const array=c=>{const a=[],i=c.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;};
 const num=v=>Object.is(v,-0)?'-0':Number.isNaN(v)?'NaN':v,point=p=>[num(p.x_0),num(p.y_0)];
 return request.cases.map(c=>{
  const graph=new LGraph,nodes=[],ports=[],edges=[];
  for(let i=0;i<c.positions.length;i++){
   const n=new LNode(graph);n.pos.x_0=i===0?-0:c.positions[i];n.pos.y_0=i*3;nodes.push(n);$add_3(graph.layerlessNodes,n);
   const p=new LPort;$setNode(p,n);$setSide(p,i<3?(c.direction===1?SOUTH_2:NORTH_3):(c.direction===1?NORTH_3:SOUTH_2));
   p.pos.x_0=-0;p.anchor.x_0=-0;ports.push(p);
  }
  for(const [a,b]of c.links){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);edges.push(e);}
  const existing=new KVectorChain;$add_7(existing,new KVector_1(-7,13));$setProperty_0(edges[0],JUNCTION_POINTS,existing);
  const empty=new KVectorChain;$setProperty_0(edges[1],JUNCTION_POINTS,empty);
  $setProperty_0(graph,RANDOM_0,new Random_0(c.seed));
  const generator=new OrthogonalRoutingGenerator(c.direction,c.spacing),source=new ArrayList,target=new ArrayList;
  for(let i=0;i<3;i++)$add_3(source,nodes[i]);for(let i=3;i<6;i++)$add_3(target,nodes[i]);
  const splits=[],draws=[],saved=[$splitSegments,$nextInt];
  $splitSegments=function(...args){const before=args[2].array.length,result=saved[0](...args);splits.push({before,after:args[2].array.length,dependencies:args[1].array.length,threshold:args[3]});return result;};
  $nextInt=function(...args){draws.push(args[1]);return saved[1](...args);};
  let slots;try{slots=$routeEdges_0(generator,graph,source,target,c.start);}finally{[$splitSegments,$nextInt]=saved;}
  return {name:c.name,slots,threshold:generator.criticalConflictThreshold,splits,draws,
   portCoordinates:ports.map(p=>num(generator.routingStrategy.getPortPositionOnHyperNode(p))),
   sourceSide:generator.routingStrategy.getSourcePortSide().name_0,targetSide:generator.routingStrategy.getTargetPortSide().name_0,
   nodes:nodes.map(n=>point(n.pos)),edges:edges.map(e=>({bends:array(e.bendPoints).map(point),hasJunction:$hasProperty(e,JUNCTION_POINTS),junctions:$hasProperty(e,JUNCTION_POINTS)?array($getProperty(e,JUNCTION_POINTS)).map(point):null})),
   priorNonemptySame:$getProperty(edges[0],JUNCTION_POINTS)===existing,priorEmptySame:$getProperty(edges[1],JUNCTION_POINTS)===empty,
   createdCleared:generator.routingStrategy.createdJunctionPoints.map_0.size_1()===0};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(req),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__orthogonalAxes(JSON.parse(req)),actualAxesGenerators:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
