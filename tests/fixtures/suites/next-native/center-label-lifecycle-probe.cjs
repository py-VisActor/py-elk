const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,out]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath)),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
global.__centerLifecycleInput=request;
const bridge=String.raw`
global.__centerLifecycle=function(){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_PortSide();$clinit_Direction_0();$clinit_EdgeLabelPlacement();$clinit_LabelSide();$clinit_EdgeRouting();$clinit_LabelDummyInserter();
 const r=global.__centerLifecycleInput,arr=c=>{const a=[],it=c.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;},point=v=>[v.x_0,v.y_0];
 return r.directions.map(direction=>{
  const g=new LGraph,a=new LNode(g),b=new LNode(g),p=new LPort,q=new LPort,e=new LEdge,events=[];
  $add_3(g.layerlessNodes,a);$add_3(g.layerlessNodes,b);$setNode(p,a);$setNode(q,b);$setSide(p,EAST_2);$setSide(q,WEST_2);$setSource_0(e,p);$setTarget_0(e,q);
  $setProperty_0(g,DIRECTION,direction==='UP'?UP_1:RIGHT_6);$setProperty_0(g,SPACING_EDGE_LABEL_0,r.edgeLabelSpacing);$setProperty_0(g,SPACING_LABEL_LABEL,r.labelSpacing);$setProperty_0(g,EDGE_ROUTING,ORTHOGONAL);
  $setProperty_0(e,EDGE_THICKNESS_0,r.thickness);
  const labels=r.labels.map(item=>{const l=new LLabel;l.size_0.x_0=item.size[0];l.size_0.y_0=item.size[1];l.pos.x_0=1;l.pos.y_0=2;
   if(item.placement)$setProperty_0(l,EDGE_LABELS_PLACEMENT,item.placement==='TAIL'?TAIL:item.placement==='HEAD'?HEAD:CENTER_5);
   $setProperty_0(l,EDGE_LABELS_INLINE_0,item.inline);$add_3(e.labels,l);return l;});
  const names=ls=>arr(ls).map(l=>r.labels[labels.indexOf(l)].name),monitor={begin:(name,work)=>events.push(['begin',name,work]),done_1:()=>events.push(['done'])};
  $process_26(g,monitor);const dummy=g.layerlessNodes.array.find(n=>n!==a&&n!==b),represented=$getProperty(dummy,REPRESENTED_LABELS),representedRef=represented,originalLabels=e.labels;
  const segment=dummy.ports.array.find(port=>port.side===EAST_2).outgoingEdges.array[0];
  const inserted={dummySize:point(dummy.size_0),portYs:dummy.ports.array.map(port=>port.pos.y_0),represented:names(represented),surviving:names(e.labels),segment:names(segment.labels),thickness:$getProperty(e,EDGE_THICKNESS_0)};
  const layers=[new Layer(g),new Layer(g),new Layer(g)];for(const layer of layers)$add_3(g.layers,layer);
  g.layerlessNodes.array.length=0;$setLayer_0(a,layers[0]);$setLayer_0(dummy,layers[1]);$setLayer_0(b,layers[2]);dummy.pos.x_0=r.dummyPosition[0];dummy.pos.y_0=r.dummyPosition[1];$setProperty_0(dummy,LABEL_SIDE,BELOW);
  $process_27(g,monitor);
  return {direction,events,inserted,finalLabels:names(e.labels),positions:labels.map(l=>point(l.pos)),sameOriginalLabels:e.labels===originalLabels,sameRepresented:$getProperty(dummy,REPRESENTED_LABELS)===representedRef,
   dummyLayerRetained:dummy.layer===layers[1],middleLayerEmpty:layers[1].nodes.array.length===0,survivorTargetRestored:e.target===q,segmentDetached:segment.source==null&&segment.target==null,
   junctionPresence:[$hasProperty(e,JUNCTION_POINTS),$hasProperty(segment,JUNCTION_POINTS)],junctionsDistinct:$getProperty(e,JUNCTION_POINTS)!==$getProperty(segment,JUNCTION_POINTS)};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(out,JSON.stringify({workerSha256:sha(raw),requestSha256:sha(fs.readFileSync(requestPath)),probeSha256:sha(fs.readFileSync(__filename)),value:global.__centerLifecycle(),layoutExecuted:false,explicitIntermediateGeometry:true,pid:process.pid},null,2)+'\n',{flag:'wx'});
