// Original layered InvertedPortProcessor / HyperedgeDummyMerger only.
// DTOs supply actual intermediate graph objects; no full layout is claimed.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__portDummyKernels=function(s){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_PortSide();$clinit_PortConstraints();$clinit_LNode$NodeType();$clinit_EdgeLabelPlacement();
 const g=new LGraph,layers=[],nodes=[],ports={},edges=[],labels=[],names=new Map,byNode={},byEdge={},initialJunctions=new Map;
 for(let i=0;i<s.layerCount;i++){const layer=new Layer(g);layers.push(layer);$add_3(g.layers,layer);}
 const side={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2};
 for(const spec of s.nodes){
  const n=new LNode(g);names.set(n,spec.id);nodes.push(n);byNode[spec.id]=n;$setType(n,{NORMAL,LONG_EDGE}[spec.type||'NORMAL']);
  [n.pos.x_0,n.pos.y_0]=spec.pos||[0,0];[n.size_0.x_0,n.size_0.y_0]=spec.size||[20,12];
  $setProperty_0(n,PORT_CONSTRAINTS_0,FIXED_SIDE);$setLayer(n,layers[spec.layer].nodes.array.length,layers[spec.layer]);
  if(spec.hasLabels!==undefined)$setProperty_0(n,LONG_EDGE_HAS_LABEL_DUMMIES,spec.hasLabels);
  if(spec.beforeLabel!==undefined)$setProperty_0(n,LONG_EDGE_BEFORE_LABEL_DUMMY,spec.beforeLabel);
  for(const item of spec.ports){const p=new LPort;$setNode(p,n);$setSide(p,side[item.side]);p.id_0=item.scratchId??0;names.set(p,item.id);ports[item.id]=p;}
 }
 for(const spec of s.nodes){const n=byNode[spec.id];if(spec.sourceMarker)$setProperty_0(n,LONG_EDGE_SOURCE,ports[spec.sourceMarker]);if(spec.targetMarker)$setProperty_0(n,LONG_EDGE_TARGET,ports[spec.targetMarker]);}
 for(const item of s.edges){const e=new LEdge;names.set(e,item.id);edges.push(e);byEdge[item.id]=e;$setSource_0(e,ports[item.source]);$setTarget_0(e,ports[item.target]);$setProperty_0(e,ORIGIN_0,{rawId:item.id});if(item.emptyJunction){const chain=new KVectorChain;$setProperty_0(e,JUNCTION_POINTS,chain);initialJunctions.set(e,chain);}}
 for(const item of s.edges)for(const spec of item.labels||[]){const label=new LLabel;names.set(label,spec.id);labels.push(label);$setProperty_0(label,EDGE_LABELS_PLACEMENT,{HEAD,CENTER,TAIL}[spec.placement]);if(spec.marker)$setProperty_0(label,END_LABEL_EDGE,byEdge[spec.marker]);$add_3(byEdge[item.id].labels,label);}
 const name=v=>v==null?null:names.get(v),prop=(o,k)=>$hasProperty(o,k)?$getProperty(o,k):null;
 if(s.operation==='inverted')$process_24(g,new BasicProgressMonitor);else $process_19(new HyperedgeDummyMerger,g,new BasicProgressMonitor);
 let di=0;for(const layer of layers)for(const n of layer.nodes.array)if(!names.has(n)){const key='d'+di++;names.set(n,key);nodes.push(n);n.ports.array.forEach((p,i)=>names.set(p,key+'.p'+i));}
 let ei=0;for(const n of nodes)for(const p of n.ports.array)for(const e of [...p.incomingEdges.array,...p.outgoingEdges.array])if(!names.has(e)){names.set(e,'x'+ei++);edges.push(e);}
 return {layers:layers.map(l=>l.nodes.array.map(name)),nodes:nodes.map(n=>({id:name(n),type:n.type_0.name_0,pos:[n.pos.x_0,n.pos.y_0],size:[n.size_0.x_0,n.size_0.y_0],layerPointer:n.layer?layers.indexOf(n.layer):null,physicallyInLayer:!!n.layer&&n.layer.nodes.array.includes(n),origin:name(prop(n,ORIGIN_0)),sourceMarker:name(prop(n,LONG_EDGE_SOURCE)),targetMarker:name(prop(n,LONG_EDGE_TARGET)),sourceMarkerPresent:$hasProperty(n,LONG_EDGE_SOURCE),targetMarkerPresent:$hasProperty(n,LONG_EDGE_TARGET),ports:n.ports.array.map(p=>({id:name(p),scratchId:p.id_0,side:p.side.name_0,size:[p.size_0.x_0,p.size_0.y_0],incoming:p.incomingEdges.array.map(name),outgoing:p.outgoingEdges.array.map(name)}))})),edges:edges.map(e=>({id:name(e),source:name(e.source),target:name(e.target),originRawId:prop(e,ORIGIN_0)?.rawId??null,junctionPresent:$hasProperty(e,JUNCTION_POINTS),originalJunctionIdentity:initialJunctions.has(e)?initialJunctions.get(e)===prop(e,JUNCTION_POINTS):null,labels:e.labels.array.map(name)})),labels:labels.map(l=>({id:name(l),endLabelEdge:name(prop(l,END_LABEL_EDGE))})),fullLayoutValidated:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__portDummyKernels(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-port-dummy-kernels-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
