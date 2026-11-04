const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,out]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath)),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
global.__selectorRequest=request;
const bridge=String.raw`
global.__selectorContexts=function(){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_PortSide();$clinit_Direction_0();$clinit_EdgeLabelPlacement();$clinit_EdgeLabelSideSelection();$clinit_LabelSide();$clinit_LabelDummyInserter();
 const r=global.__selectorRequest,arr=c=>{const a=[],it=c.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;},modes=[ALWAYS_UP,ALWAYS_DOWN,DIRECTION_UP,DIRECTION_DOWN,SMART_UP,SMART_DOWN];
 return modes.map((mode,caseIndex)=>{
  const g=new LGraph,a=new LNode(g),b=new LNode(g),ports=[],labels=[],names=[],edges=[],events=[];
  $add_3(g.layerlessNodes,a);$add_3(g.layerlessNodes,b);$setProperty_0(g,DIRECTION,RIGHT_6);$setProperty_0(g,SPACING_EDGE_LABEL_0,2);$setProperty_0(g,SPACING_LABEL_LABEL,1);$setProperty_0(g,EDGE_LABELS_SIDE_SELECTION_0,mode);
  for(const side of[EAST_2,EAST_2,NORTH_3]){const p=new LPort;$setNode(p,a);$setSide(p,side);ports.push(p);}
  const q=new LPort;$setNode(q,b);$setSide(q,WEST_2);
  const edge=(source,target,rev)=>{const e=new LEdge;$setSource_0(e,source);$setTarget_0(e,target);$setProperty_0(e,EDGE_THICKNESS_0,3);$setProperty_0(e,REVERSED,rev);edges.push(e);return e;};
  const label=(e,name,placement,inline)=>{const l=new LLabel;l.size_0.x_0=4;l.size_0.y_0=2;$setProperty_0(l,EDGE_LABELS_PLACEMENT,placement);$setProperty_0(l,EDGE_LABELS_INLINE_0,inline);$add_3(e.labels,l);labels.push(l);names.push(name);return l;};
  const e0=edge(ports[0],q,true),e1=edge(ports[1],q,false),loop=edge(ports[2],ports[2],false);
  label(e0,'c0',CENTER_5,false);const h0=label(e0,'h0',HEAD,false);label(e1,'c1',CENTER_5,true);const t1=label(e1,'t1',TAIL,false);label(e1,'h1',HEAD,false);const lt=label(loop,'loop-tail',TAIL,false);label(loop,'loop-head',HEAD,false);
  if(!h0.propertyMap)h0.propertyMap=new HashMap;$put_6(h0.propertyMap,END_LABEL_EDGE,null);
  const quiet={begin:()=>{},done_1:()=>{}};$process_26(g,quiet);const dummies=g.layerlessNodes.array.filter(n=>n!==a&&n!==b);
  const layers=[new Layer(g),new Layer(g),new Layer(g)];for(const l of layers)$add_3(g.layers,l);g.layerlessNodes.array.length=0;$setLayer_0(a,layers[0]);for(const n of dummies)$setLayer_0(n,layers[1]);$setLayer_0(b,layers[2]);
  const dummyBefore=dummies.map(n=>({size:[n.size_0.x_0,n.size_0.y_0],portYs:n.ports.array.map(p=>p.pos.y_0)}));
  $process_30(g,{begin:(name,work)=>events.push(['begin',name,work]),done_1:()=>events.push(['done'])});
  const empty=gatherLabels(ports[0]),tails=gatherLabels(ports[1]),loopLabels=gatherLabels(ports[2]);
  return {mode:mode.name_0,events,dummyBefore,dummies:dummies.map(n=>({side:$getProperty(n,LABEL_SIDE).name_0,height:n.size_0.y_0,portYs:n.ports.array.map(p=>p.pos.y_0)})),labelSides:labels.map(l=>({name:names[labels.indexOf(l)],side:$getProperty(l,LABEL_SIDE).name_0})),
   emptyBagNonnull:empty!=null,emptyBagLength:empty==null?null:empty.array.length,tailBag:arr(tails).map(l=>names[labels.indexOf(l)]),loopBag:arr(loopLabels).map(l=>names[labels.indexOf(l)]),sameLoopTailTwice:loopLabels.array[0]===lt&&loopLabels.array[1]===lt,
   h0MarkerPresent:$hasProperty(h0,END_LABEL_EDGE),h0MarkerNullish:$getProperty(h0,END_LABEL_EDGE)==null,t1MarkerOriginal:$getProperty(t1,END_LABEL_EDGE)===e1,portMaximums:ports.map(p=>$getProperty(p,MAX_EDGE_THICKNESS))};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(out,JSON.stringify({workerSha256:sha(raw),requestSha256:sha(fs.readFileSync(requestPath)),probeSha256:sha(fs.readFileSync(__filename)),value:global.__selectorContexts(),layoutExecuted:false,explicitLayerSetup:true,pid:process.pid},null,2)+'\n',{flag:'wx'});
