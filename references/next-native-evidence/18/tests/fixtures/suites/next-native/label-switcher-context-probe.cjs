const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,out]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath)),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');global.__switcherRequest=request;
const bridge=String.raw`
global.__newSwitcherContexts=function(){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_Direction_0();$clinit_EdgeLabelPlacement();$clinit_CenterEdgeLabelPlacementStrategy();$clinit_LabelDummyInserter();
 const r=global.__switcherRequest,strategies={MEDIAN_LAYER,TAIL_LAYER,HEAD_LAYER,SPACE_EFFICIENT_LAYER,WIDEST_LAYER,CENTER_LAYER},sw=new LabelDummySwitcher,quiet={begin:()=>{},done_1:()=>{}},arr=c=>{const out=[],it=c.iterator_0();while(it.hasNext_0())out.push(it.next_1());return out;};
 return r.cases.map(c=>{
  const g=new LGraph,a=new LNode(g),b=new LNode(g),p=new LPort,q=new LPort,e=new LEdge,labels=[],events=[];
  a.size_0.x_0=10;b.size_0.x_0=10;$add_3(g.layerlessNodes,a);$add_3(g.layerlessNodes,b);$setNode(p,a);$setNode(q,b);$setSide(p,EAST_2);$setSide(q,WEST_2);$setSource_0(e,p);$setTarget_0(e,q);
  $setProperty_0(g,DIRECTION,c.direction==='UP'?UP_1:RIGHT_6);$setProperty_0(g,SPACING_EDGE_LABEL_0,2);$setProperty_0(g,SPACING_LABEL_LABEL,1);$setProperty_0(g,SPACING_EDGE_NODE_BETWEEN_LAYERS_0,4.25);$setProperty_0(g,SPACING_NODE_NODE_BETWEEN_LAYERS_0,7.75);$setProperty_0(g,EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY_0,strategies[c.strategy]);$setProperty_0(e,EDGE_THICKNESS_0,3);$setProperty_0(e,REVERSED,!!c.reversed);
  for(const width of[12,7]){const l=new LLabel;l.size_0.x_0=width;l.size_0.y_0=2;$setProperty_0(l,EDGE_LABELS_PLACEMENT,CENTER_5);$add_3(e.labels,l);labels.push(l);}
  if(c.nullOverride){$put_6(labels[0].propertyMap,EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY_0,null);$setProperty_0(labels[1],EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY_0,TAIL_LAYER);}
  $process_26(g,quiet);const labelDummy=g.layerlessNodes.array.find(n=>n!==a&&n!==b),layers=Array.from({length:5},()=>new Layer(g));for(const layer of layers)$add_3(g.layers,layer);g.layerlessNodes.array.length=0;$setLayer_0(a,layers[0]);$setLayer_0(labelDummy,layers[1]);$setLayer_0(b,layers[4]);
  const extra=new LNode(g);extra.size_0.x_0=c.zeroWidths?0:20;$setLayer_0(extra,layers[3]);new LongEdgeSplitter().process(g,quiet);
  const longs=[2,3].map(i=>layers[i].nodes.array.find(n=>n.type_0===LONG_EDGE)),nodes=[a,labelDummy,...longs,extra,b],names=['source','label','long2','long3','extra','target'],name=n=>names[nodes.indexOf(n)];
  layers.forEach((layer,i)=>{layer.id_0=i;layer.size_0.x_0=c.zeroWidths?0:(i===3?20:i===0||i===4?10:0);});
  const info=new LabelDummySwitcher$LabelDummyInfo(labelDummy,strategies[c.strategy]),beforeInfo={strategy:info.placementStrategy.name_0,left:arr(info.leftLongEdgeDummies).map(name),right:arr(info.rightLongEdgeDummies).map(name),range:[info.leftmostLayerId,info.rightmostLayerId]};
  sw.process(g,{begin:(task,work)=>events.push(['begin',task,work]),done_1:()=>events.push(['done'])});
  const allEdges=[];for(const n of nodes)for(const port of n.ports.array)for(const edge of port.outgoingEdges.array)if(!allEdges.includes(edge))allEdges.push(edge);
  return {name:c.name,events,beforeInfo,layers:layers.map(l=>l.nodes.array.map(name)),labelLayer:labelDummy.layer.id_0,alignment:$getProperty(labelDummy,ALIGNMENT).name_0,
   markers:longs.map(n=>({node:name(n),has:$hasProperty(n,LONG_EDGE_BEFORE_LABEL_DUMMY),value:$booleanValue(castToBoolean($getProperty(n,LONG_EDGE_BEFORE_LABEL_DUMMY)))})),
   includes:labels.map(l=>$booleanValue(castToBoolean($getProperty(l,INCLUDE_LABEL)))),edges:allEdges.map(edge=>[name(edge.source.owner),name(edge.target.owner)]),fieldReset:sw.layerWidths==null,firstOverrideHas:$hasProperty(labels[0],EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY_0)};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(out,JSON.stringify({workerSha256:sha(raw),requestSha256:sha(fs.readFileSync(requestPath)),probeSha256:sha(fs.readFileSync(__filename)),value:global.__newSwitcherContexts(),layoutExecuted:false,explicitLayerGeometry:true,pid:process.pid},null,2)+'\n',{flag:'wx'});
