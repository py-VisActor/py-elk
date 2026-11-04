const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__splineFoundation=function(request){
 $clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_SplineEdgeRouter$SideToProcess();
 const sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2},types={NORMAL,BREAKING_POINT,LONG_EDGE,EXTERNAL_PORT},ss={LEFT:LEFT_4,RIGHT:RIGHT_4},arr=list=>{const a=[],i=list.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;},g=new LGraph,segments=[],records=[];
 for(const input of request.segments){
  const ports=input.ports.map((p,i)=>{const n=new LNode(g);n.type_0=types[p.type];n.pos.y_0=p.nodeY;const port=new LPort;$setNode(port,n);$setSide(port,sides[p.side]);port.id_0=i;port.pos.y_0=p.portY;port.anchor.y_0=p.anchorY;if(Object.hasOwn(p,'nsY'))$setProperty_0(port,SPLINE_NS_PORT_Y_COORD,p.nsY);return port;});
  const edges=input.edges.map((p,i)=>{const e=new LEdge;e.id_0=i;$setSource_0(e,ports[p[0]]);$setTarget_0(e,ports[p[1]]);return e;});let segment,pairOrder=null;
  if(Object.hasOwn(input,'single')){const pairs=new HashSet;edges.forEach((e,i)=>$add_6(pairs,new Pair(ss[input.pairSides[i]],e)));pairOrder=arr(pairs).map(p=>p.second.id_0);segment=new SplineSegment_0(ports[input.single],pairs,ss[input.singleSide]);}
  else segment=new SplineSegment(edges[0],ss[input.sides[0]],ss[input.sides[1]]);
  segments.push(segment);records.push({name:input.name,pairOrder,left:arr(segment.leftPorts).map(p=>p.id_0),right:arr(segment.rightPorts).map(p=>p.id_0),edges:arr(segment.edges).map(e=>e.id_0),bounding:[segment.boundingBox.x_0,segment.boundingBox.y_0,segment.boundingBox.width_0,segment.boundingBox.height],center:segment.centerControlPointY,top:segment.hyperEdgeTopYPos,bottom:segment.hyperEdgeBottomYPos,straight:segment.isStraight,info:edges.map(e=>{const x=$get_10(segment.edgeInformation,e);return{start:x.startY,end:x.endY,sourceNormal:x.normalSourceNode,targetNormal:x.normalTargetNode,leftInverted:x.invertedLeft,rightInverted:x.invertedRight};}),initial:{mark:segment.mark,rank:segment.rank,handled:segment.handled,initialSegment:segment.initialSegment,lastSegment:segment.lastSegment}});
 }
 const deps=request.dependencies.map(p=>new SplineEdgeRouter$Dependency(segments[p[0]],segments[p[1]],p[2]));
 return{segments:records,dependencies:deps.map(d=>({source:segments.indexOf(d.source),target:segments.indexOf(d.target),weight:d.weight})),adjacency:segments.map(s=>({out:s.outgoing.array.map(d=>deps.indexOf(d)),in:s.incoming.array.map(d=>deps.indexOf(d))})),between:request.between.map(p=>isBetween(...p))};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(fs.readFileSync(requestPath)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__splineFoundation(request),actualSegmentAndDependencyConstructors:true,preparedNativeModels:true,layoutExecuted:false,nativeExecuted:false},null,2)+'\n',{flag:'wx'});
