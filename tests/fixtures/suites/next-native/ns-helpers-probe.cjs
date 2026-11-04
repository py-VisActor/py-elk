// Actual NS pre/post over real layered graph objects. Dummy positions between
// stages are explicit DTO inputs; they are not calculated layout coordinates.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__nsHelpers=function(s){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_PortSide();$clinit_PortConstraints();$clinit_OrderingStrategy();$clinit_EdgeRouting();
 const g=new LGraph,layer=new Layer(g);$add_3(g.layers,layer);
 const nodes=[],ports=[],edges=[],names=new Map,byPort={},initialJunctions=new Map;
 const list=l=>{const a=[],it=l.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 $setProperty_0(g,CONSIDER_MODEL_ORDER_STRATEGY_0,{NONE:NONE_11,NODES_AND_EDGES,PREFER_EDGES,PREFER_NODES}[s.strategy]);
 $setProperty_0(g,EDGE_ROUTING,{ORTHOGONAL,SPLINES}[s.routing]);
 for(const spec of s.nodes){
  const n=new LNode(g);names.set(n,spec.id);nodes.push(n);[n.pos.x_0,n.pos.y_0]=spec.pos||[0,0];[n.size_0.x_0,n.size_0.y_0]=spec.size||[40,30];
  $setProperty_0(n,PORT_CONSTRAINTS_0,FIXED_SIDE);$setLayer(n,layer.nodes.array.length,layer);
  for(const item of spec.ports){const p=new LPort;$setNode(p,n);$setSide(p,{NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2}[item.side]);[p.pos.x_0,p.pos.y_0]=item.pos||[2,3];[p.anchor.x_0,p.anchor.y_0]=item.anchor||[1,2];p.id_0=ports.length;names.set(p,item.id);byPort[item.id]=p;ports.push(p);if(item.allowSwitch!==undefined)$setProperty_0(p,ALLOW_NON_FLOW_PORTS_TO_SWITCH_SIDES_0,item.allowSwitch);}
 }
 for(const item of s.edges){const e=new LEdge;names.set(e,item.id);edges.push(e);$setSource_0(e,byPort[item.source]);$setTarget_0(e,byPort[item.target]);for(const p of item.bends||[])$addLast_0(e.bendPoints,new KVector_1(p[0],p[1]));if(item.emptyJunction){const chain=new KVectorChain;$setProperty_0(e,JUNCTION_POINTS,chain);initialJunctions.set(e,chain);}}
 const name=v=>v==null?null:names.get(v),prop=(o,k)=>$hasProperty(o,k)?$getProperty(o,k):null;
 function snapshot(){
  return {layer:layer.nodes.array.map(name),nodes:nodes.map(n=>({id:name(n),type:n.type_0.name_0,origin:name(prop(n,ORIGIN_0)),hint:prop(n,CROSSING_HINT)?.value_0??null,layoutUnit:name(prop(n,IN_LAYER_LAYOUT_UNIT)),successors:prop(n,IN_LAYER_SUCCESSOR_CONSTRAINTS)?list(prop(n,IN_LAYER_SUCCESSOR_CONSTRAINTS)).map(name):[],associates:prop(n,BARYCENTER_ASSOCIATES)?list(prop(n,BARYCENTER_ASSOCIATES)).map(name):[],inLayer:!!n.layer,graphRetained:n.graph_0===g,ports:n.ports.array.map(p=>({id:name(p),side:p.side.name_0,origin:name(prop(p,ORIGIN_0)),dummy:name(prop(p,PORT_DUMMY)),incoming:p.incomingEdges.array.map(name),outgoing:p.outgoingEdges.array.map(name),splineY:prop(p,SPLINE_NS_PORT_Y_COORD)}))})),edges:edges.map(e=>({id:name(e),source:name(e.source),target:name(e.target),bends:list(e.bendPoints).map(v=>[v.x_0,v.y_0]),junctionPresent:$hasProperty(e,JUNCTION_POINTS),junctions:prop(e,JUNCTION_POINTS)?list(prop(e,JUNCTION_POINTS)).map(v=>[v.x_0,v.y_0]):[],initialJunctionIdentityPreserved:initialJunctions.has(e)?initialJunctions.get(e)===prop(e,JUNCTION_POINTS):null}))};
 }
 $process_39(g,new BasicProgressMonitor);
 let index=0;
 for(const n of layer.nodes.array)if(!names.has(n)){const key='d'+index++;names.set(n,key);nodes.push(n);n.ports.array.forEach((p,i)=>names.set(p,key+'.p'+i));}
 const pre=snapshot();
 index=0;for(const n of nodes)if(n.type_0===NORTH_SOUTH_PORT){n.pos.x_0=s.dummyPlacement.start[0]+index*s.dummyPlacement.step[0];n.pos.y_0=s.dummyPlacement.start[1]+index*s.dummyPlacement.step[1];index++;}
 $process_38(g,new BasicProgressMonitor);return {pre,post:snapshot(),dummyCoordinatesSupplied:true};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__nsHelpers(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-NS-helpers-observation/v1',mode:'original-layered-NS-pre-post-with-supplied-dummy-positions',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
