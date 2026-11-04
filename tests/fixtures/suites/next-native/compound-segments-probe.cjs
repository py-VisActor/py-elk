const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const[pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),wp=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(wp),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__compoundSegments=function(spec,geometry){
 $clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_PortType();$clinit_CompoundGraphPostprocessor();
 const list=l=>{const values=[],it=l.iterator_0();while(it.hasNext_0())values.push(it.next_1());return values;};
 const names=new Map,graphs={},original=[],originalNames=new Map,labelNames=new Map;
 function graph(name){const g=new LGraph;graphs[name]=g;names.set(g,name);$setProperty_0(g,DIRECTION,RIGHT_6);$setProperty_0(g,GRAPH_PROPERTIES,new EnumSet$EnumSetImpl($getEnumConstants(Lorg_eclipse_elk_alg_layered_options_GraphProperties_2_classLit),createFrom($getEnumConstants(Lorg_eclipse_elk_alg_layered_options_GraphProperties_2_classLit),$getEnumConstants(Lorg_eclipse_elk_alg_layered_options_GraphProperties_2_classLit).length),0));return g;}
 const r=graph('r'),a=graph('A'),b=graph('B');r.offset.x_0=geometry.rootOffset[0];r.offset.y_0=geometry.rootOffset[1];
 function node(g,name,x,y){const n=new LNode(g);n.type_0=NORMAL;n.pos.x_0=x;n.pos.y_0=y;n.size_0.x_0=60;n.size_0.y_0=40;$add_3(g.layerlessNodes,n);names.set(n,name);return n;}
 const pa=node(r,'parentA',...geometry.A.nodePos),pb=node(r,'parentB',...geometry.B.nodePos);pa.nestedGraph=a;a.parentNode=pa;pb.nestedGraph=b;b.parentNode=pb;
 for(const key of ['A','B']){const g=graphs[key],v=geometry[key];g.offset.x_0=v.offset[0];g.offset.y_0=v.offset[1];[g.padding.top_0,g.padding.right,g.padding.bottom,g.padding.left]=v.padding;}
 const x=node(a,'x',7,9),y=node(b,'y',10,11),z=node(b,'z',23,17);
 function port(n,name,side){const p=new LPort;$setNode(p,n);$setSide(p,side);p.pos.x_0=2;p.pos.y_0=3;p.size_0.x_0=4;p.size_0.y_0=6;p.anchor.x_0=2;p.anchor.y_0=3;names.set(p,name);return p;}
 const xp=port(x,'xp',EAST_2),yp=port(y,'yp',WEST_2),zp=port(z,'zp',WEST_2),back=port(z,'back',EAST_2),xin=port(x,'xin',WEST_2);
 function edge(id,source,target,placement){const e=new LEdge;$setSource_0(e,source);$setTarget_0(e,target);$setProperty_0(e,EDGE_THICKNESS_0,id==='e1'?5:2);original.push(e);originalNames.set(e,id);if(placement){const l=new LLabel;l.text_0=id;l.size_0.x_0=10;l.size_0.y_0=4;$setProperty_0(l,EDGE_LABELS_PLACEMENT,placement);$add_3(e.labels,l);labelNames.set(l,id+'-label');}return e;}
 edge('e0',xp,yp,CENTER_5);edge('e1',xp,zp,TAIL);edge('e2',back,xin,HEAD);
 const prep=new CompoundGraphPreprocessor,preMonitor=new BasicProgressMonitor;$process_1(prep,r,preMonitor);
 const map=$getProperty(r,CROSS_HIERARCHY_MAP),edgeTokens=new Map;let nextToken=0;
 const portName=p=>!p?null:names.has(p)?names.get(p):names.get(p.owner)+':port'+p.owner.ports.array.indexOf(p);
 const graphFlags=g=>list($getProperty(g,GRAPH_PROPERTIES)).map(v=>v.name_0).sort();
 function records(){return original.map(e=>({id:originalNames.get(e),detached:!e.source&&!e.target,labels:e.labels.array.map(l=>labelNames.get(l)),segments:list(map.get_1(e)).map(ch=>{if(!edgeTokens.has(ch.newEdge))edgeTokens.set(ch.newEdge,nextToken++);return{graph:names.get(ch.graph_0),type:ch.type_0.name_0,edgeToken:edgeTokens.get(ch.newEdge),actualSource:portName($getActualSource(ch)),actualTarget:portName($getActualTarget(ch)),labels:ch.newEdge.labels.array.map(l=>labelNames.get(l)),thickness:$getProperty(ch.newEdge,EDGE_THICKNESS_0)};})}));}
 const before=records();
 for(const[name,g]of Object.entries(graphs)){if(name!=='r')for(const n of g.layerlessNodes.array)if(n.type_0===EXTERNAL_PORT){n.pos.x_0=geometry[name].dummyPos[0];n.pos.y_0=geometry[name].dummyPos[1];}for(const n of g.layerlessNodes.array)for(const p of n.ports.array)for(const e of p.outgoingEdges.array){if(!edgeTokens.has(e))continue;const v=geometry[name];$reset_0(e.bendPoints);for(const q of v.bends)$add_7(e.bendPoints,new KVector_1(...q));const jp=new KVectorChain;if(spec.junctions)for(const q of v.junctions)$add_7(jp,new KVector_1(...q));$setProperty_0(e,JUNCTION_POINTS,jp);for(const l of e.labels.array){l.pos.x_0=11;l.pos.y_0=13;}}}
 const postMonitor=new BasicProgressMonitor;$process_0(r,postMonitor);
 const points=chain=>chain?list(chain).map(v=>[v.x_0,v.y_0]):null;
 return{id:spec.id,before,after:original.map(e=>({id:originalNames.get(e),source:portName(e.source),target:portName(e.target),bends:points(e.bendPoints),junctionPresent:$hasProperty(e,JUNCTION_POINTS),junctions:$hasProperty(e,JUNCTION_POINTS)?points($getProperty(e,JUNCTION_POINTS)):null,targetOffset:[$getProperty(e,TARGET_OFFSET).x_0,$getProperty(e,TARGET_OFFSET).y_0],labels:e.labels.array.map(l=>({id:labelNames.get(l),position:[l.pos.x_0,l.pos.y_0],originalEdge:$getProperty(l,ORIGINAL_LABEL_EDGE)===e}))})),flags:Object.fromEntries(Object.entries(graphs).map(([k,g])=>[k,graphFlags(g)])),allDummyEdgesDetached:[...edgeTokens.keys()].every(e=>!e.source&&!e.target),persistentMapCleared:prep.dummyNodeMap.size_1()===0,preMapFieldCleared:prep.crossHierarchyMap===null,geometrySupplied:true,routingExecuted:false,layoutExecuted:false};
};`;
const m=new Module(wp,module);m.filename=wp;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,wp);const request=JSON.parse(requestRaw);
const observation={cases:request.cases.map(s=>global.__compoundSegments(s,request.geometry)),geometrySupplied:true,routingExecuted:false,layoutExecuted:false};
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-compound-segments/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,nativeExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
