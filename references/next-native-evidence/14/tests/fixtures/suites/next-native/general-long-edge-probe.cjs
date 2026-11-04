const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const[pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),wp=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(wp),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__longEdges=function(s){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_EdgeLabelPlacement();
 const list=l=>{const a=[],it=l.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const g=new LGraph,nodes=[],names=new Map,edgeNames=new Map,allEdges=[],dummies=[],events=[];
 for(let i=0;i<4;i++){const layer=new Layer(g);$add_3(g.layers,layer);const n=new LNode(g);$setLayer_0(n,layer);names.set(n,'n'+i);nodes.push(n);const p=new LPort;$setSide(p,i===3?WEST_2:EAST_2);$setNode(p,n);names.set(p,'p'+i);}
 const port=i=>nodes[i].ports.array[0],edge=new LEdge,adjacent=new LEdge;
 $setSource_0(edge,port(0));$setTarget_0(edge,port(3));$setSource_0(adjacent,port(2));$setTarget_0(adjacent,port(3));
 edgeNames.set(edge,'edge');edgeNames.set(adjacent,'adjacent');allEdges.push(edge,adjacent);
 $setProperty_0(edge,EDGE_THICKNESS_0,s.thickness);$setProperty_0(g,UNNECESSARY_BENDPOINTS_0,s.unnecessary);
 const initialJunctions=new KVectorChain;$add_7(initialJunctions,new KVector_1(1,2));$setProperty_0(edge,JUNCTION_POINTS,initialJunctions);
 const labelNames=new Map;for(const[id,placement,marker]of [['tail',TAIL,false],['head',HEAD,false],['keptHead',HEAD,true],['center',CENTER,false]]){const l=new LLabel_0(id);labelNames.set(l,id);$setProperty_0(l,EDGE_LABELS_PLACEMENT,placement);if(marker)$setProperty_0(l,END_LABEL_EDGE,adjacent);$add_3(edge.labels,l);}
 const monitor={begin:(name,total)=>events.push({kind:'begin',name,total}),done_1:()=>events.push({kind:'done'})};
 $process_35(g,monitor);
 for(let i=0;i<g.layers.array.length;i++)for(const n of g.layers.array[i].nodes.array)if(n.type_0===LONG_EDGE){const index=dummies.length;dummies.push(n);names.set(n,'d'+index);n.ports.array.forEach((p,j)=>names.set(p,'d'+index+'.p'+j));const e=n.ports.array[1].outgoingEdges.array[0];edgeNames.set(e,'generated'+index);allEdges.push(e);}
 const prop=(o,k)=>$hasProperty(o,k)?$getProperty(o,k):null,name=o=>o==null?null:names.get(o),points=c=>c?list(c).map(p=>[p.x_0,p.y_0]):[];
 const view=()=>({layers:g.layers.array.map(l=>l.nodes.array.map(name)),edges:allEdges.map(e=>({id:edgeNames.get(e),source:name(e.source),target:name(e.target),labels:e.labels.array.map(l=>labelNames.get(l)),junctionPresent:$hasProperty(e,JUNCTION_POINTS),junctions:points(prop(e,JUNCTION_POINTS)),bends:points(e.bendPoints)})),dummies:dummies.map(n=>({id:name(n),height:n.size_0.y_0,ports:n.ports.array.map(p=>({id:name(p),side:p.side.name_0,y:p.pos.y_0})),source:name(prop(n,LONG_EDGE_SOURCE)),target:name(prop(n,LONG_EDGE_TARGET)),origin:edgeNames.get(prop(n,ORIGIN_0)),labelDummies:!!$getProperty(n,LONG_EDGE_HAS_LABEL_DUMMIES)})),headMarkers:edge.labels.array.concat(...dummies.map(n=>n.ports.array[1].outgoingEdges.array.flatMap(e=>e.labels.array))).filter(l=>labelNames.get(l)==='head'||labelNames.get(l)==='keptHead').map(l=>({label:labelNames.get(l),edge:edgeNames.get(prop(l,END_LABEL_EDGE))})),targetIncoming:port(3).incomingEdges.array.map(e=>edgeNames.get(e)),originalJunctionIdentity:$getProperty(edge,JUNCTION_POINTS)===initialJunctions});
 const split=view();const suppliedPoints=[];
 dummies.forEach((n,i)=>{n.pos.x_0=10+20*i;n.pos.y_0=20+20*i;const e=n.ports.array[1].outgoingEdges.array[0],p=new KVector_1(11+20*i,22+20*i);$add_7(e.bendPoints,p);suppliedPoints.push(p);if(i===dummies.length-1){const c=new KVectorChain,p=new KVector_1(9,8);$add_7(c,p);$setProperty_0(e,JUNCTION_POINTS,c);suppliedPoints.push(p);}});
 $process_34(g,monitor);
 const joined=view();return{id:s.id,events,split,joined,removedDummiesRetainLayer:dummies.every(n=>n.layer!==null),droppedEdgesDetached:allEdges.slice(2).every(e=>e.source===null&&e.target===null),copiedPointsFresh:list(edge.bendPoints).concat(list($getProperty(edge,JUNCTION_POINTS))).every(p=>!suppliedPoints.includes(p)),dummyCoordinatesSupplied:true,segmentGeometrySupplied:true,layoutExecuted:false};
};`;
const m=new Module(wp,module);m.filename=wp;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,wp);
const observation={cases:JSON.parse(requestRaw).cases.map(s=>global.__longEdges(s)),layoutExecuted:false};
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-general-long-edges/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
