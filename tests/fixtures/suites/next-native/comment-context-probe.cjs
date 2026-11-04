const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,out]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath)),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
global.__commentRequest=request;
const bridge=String.raw`
global.__commentContexts=function(){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_PortSide();$clinit_PortConstraints();$clinit_EdgeLabelPlacement();
 const r=global.__commentRequest,vec=v=>[v.x_0,v.y_0],margin=n=>[n.margin.top_0,n.margin.right,n.margin.bottom,n.margin.left],side={NORTH:NORTH_3,SOUTH:SOUTH_2,WEST:WEST_2,EAST:EAST_2};
 const monitor=events=>({begin:(n,w)=>events.push(['begin',n,w]),done_1:()=>events.push(['done']),isLoggingEnabled:()=>true,log_0:s=>events.push(['log',s])});
 const marginCases=r.marginCases.map((name,index)=>{
  const g=new LGraph,n=new LNode(g),layer=new Layer(g),events=[],reads=[];$add_3(g.layers,layer);$setLayer_0(n,layer);n.size_0.x_0=index==1?1:5;n.margin.top_0=1;n.margin.right=1;n.margin.bottom=4;n.margin.left=2;
  $setProperty_0(g,SPACING_COMMENT_COMMENT,10);$setProperty_0(g,SPACING_COMMENT_NODE,10);
  const oldMargin=n.margin,top=new ArrayList,bottom=new ArrayList;
  if(index==0){if(!n.propertyMap)n.propertyMap=new HashMap;$put_6(n.propertyMap,SPACING_INDIVIDUAL,null);}
  if(index==1){const individual=new MapPropertyHolder;$setProperty_0(individual,SPACING_COMMENT_COMMENT,-4);$setProperty_0(individual,SPACING_COMMENT_NODE,3);$setProperty_0(n,SPACING_INDIVIDUAL,individual);$setProperty_0(n,TOP_COMMENTS,top);}
  if(index==2){for(const [w,h]of[[4,2],[7,5]]){const box=new LNode(g);box.size_0.x_0=w;box.size_0.y_0=h;$add_3(top,box);}$setProperty_0(n,TOP_COMMENTS,top);$setProperty_0(n,BOTTOM_COMMENTS,bottom);$setProperty_0(n,SPACING_INDIVIDUAL,new MapPropertyHolder);}
  const old=getIndividualOrDefault;getIndividualOrDefault=function(node,p){reads.push(p===SPACING_COMMENT_COMMENT?'commentComment':'commentNode');return old(node,p);};
  const values=[];try{for(let i=0;i<r.repeatMargin;i++){$process_2(g,monitor(events));values.push(margin(n));}}finally{getIndividualOrDefault=old;}
  return {name,events,reads,values,sameMargin:n.margin===oldMargin,sameTop:index===0?$getProperty(n,TOP_COMMENTS)==null:$getProperty(n,TOP_COMMENTS)===top,sameBottom:index===2?$getProperty(n,BOTTOM_COMMENTS)===bottom:$getProperty(n,BOTTOM_COMMENTS)==null,size:vec(n.size_0),topPresence:$hasProperty(n,TOP_COMMENTS),bottomPresence:$hasProperty(n,BOTTOM_COMMENTS)};
 });
 const preCases=r.preCases.map(c=>{
  const g=new LGraph,nodes=[],ports=[],edges=[],names=new Map,events=[],dummyLayers=[],notes=[],connections=[],bends=[],initialTop=new ArrayList,initialBottom=new ArrayList;
  const node=name=>{const n=new LNode(g);names.set(n,name);nodes.push(n);$add_3(g.layerlessNodes,n);return n;};
  const port=(n,name,s)=>{const p=new LPort;$setNode(p,n);$setSide(p,side[s]);p.anchor.x_0=.75;p.anchor.y_0=.5;names.set(p,name);ports.push(p);return p;};
  const edge=(s,t,name)=>{const e=new LEdge;$setSource_0(e,s);$setTarget_0(e,t);names.set(e,name);edges.push(e);$add_7(e.bendPoints,new KVector_1(1,2));$add_7(e.bendPoints,new KVector_1(3,4));bends.push(e.bendPoints);return e;};
  const real=node('real'),neighbor=node('neighbor');real.size_0.x_0=20;real.size_0.y_0=10;real.pos.x_0=30;real.pos.y_0=50;real.margin.top_0=1;real.margin.right=2;real.margin.bottom=3;real.margin.left=4;
  $setProperty_0(g,SPACING_COMMENT_COMMENT,4);$setProperty_0(g,SPACING_COMMENT_NODE,6);$setProperty_0(real,PORT_CONSTRAINTS_0,c.fixed?FIXED_SIDE:FREE);$setProperty_0(real,TOP_COMMENTS,initialTop);$setProperty_0(real,BOTTOM_COMMENTS,initialBottom);
  const label=new LLabel;label.pos.y_0=0;label.size_0.y_0=2;$add_3(real.labels,label);
  for(const s of c.sideOrder)edge(port(real,'real-'+s,s),port(neighbor,'neighbor-'+s,'WEST'),'neighbor-'+s);
  for(let i=0;i<c.noteCount;i++){
   const note=node('note'+i);notes.push(note);$setProperty_0(note,COMMENT_BOX,true);note.size_0.x_0=[7,9,5][i];note.size_0.y_0=[3,5,2][i];
   const bp=port(note,'box'+i,'EAST'),np=port(real,'connection'+i,'WEST');connections.push(np);edge(c.noteOutgoing?bp:np,c.noteOutgoing?np:bp,'comment'+i);
   const dummy=new LNode(g),layer=new Layer(g);names.set(dummy,'dummy'+i);nodes.push(dummy);$add_3(g.layers,layer);$setLayer_0(dummy,layer);dummyLayers.push(layer);$setProperty_0(np,PORT_DUMMY,dummy);
  }
  const retained=node('retained-loop');$setProperty_0(retained,COMMENT_BOX,true);const rp=port(retained,'loop-port','NORTH'),loop=edge(rp,rp,'loop');const ll=new LLabel;$setProperty_0(ll,EDGE_LABELS_PLACEMENT,HEAD);$add_3(loop.labels,ll);const loopPoints=loop.bendPoints.toArray();
  const named=v=>v==null?null:names.get(v),bag=p=>{const a=$getProperty(real,p);return a==null?null:a.array.map(named);};
  const view=()=>({layerless:g.layerlessNodes.array.map(named),layers:g.layers.array.map(l=>l.nodes.array.map(named)),realPorts:real.ports.array.map(named),top:bag(TOP_COMMENTS),bottom:bag(BOTTOM_COMMENTS),margin:margin(real),notes:notes.map((n,i)=>({name:named(n),pos:vec(n.pos),boxPort:vec(n.ports.array[0].pos),connectionOwner:named(connections[i].owner),connectionPos:vec(connections[i].pos),storedConnection:$getProperty(n,COMMENT_CONN_PORT)===connections[i],sameGraph:n.graph_0===g})),edges:edges.map((e,i)=>({name:named(e),source:named(e.source),target:named(e.target),bends:e.bendPoints.toArray().map(vec),sameBendChain:e.bendPoints===bends[i]})),dummyLayerPointers:dummyLayers.map((l,i)=>nodes.find(n=>names.get(n)==='dummy'+i).layer===l),loop:{reversed:$getProperty(loop,REVERSED),present:$hasProperty(loop,REVERSED),label:$getProperty(ll,EDGE_LABELS_PLACEMENT).name_0,samePoints:loop.bendPoints.toArray().map((p,i)=>p===loopPoints[i])},sameTop:$getProperty(real,TOP_COMMENTS)===initialTop,sameBottom:$getProperty(real,BOTTOM_COMMENTS)===initialBottom});
  $process_5(g,monitor(events));const pre=view();
  const mainLayer=new Layer(g);$add_3(g.layers,mainLayer);for(const n of g.layerlessNodes.array)$setLayer_0(n,mainLayer);g.layerlessNodes.array.length=0;
  $process_2(g,monitor(events));const margined=view(),posts=[];for(let i=0;i<r.repeatPost;i++){$process_3(g,monitor(events));posts.push(view());}
  return {name:c.name,events,pre,margined,posts};
 });
 return {marginCases,preCases};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(out,JSON.stringify({workerSha256:sha(raw),requestSha256:sha(fs.readFileSync(requestPath)),probeSha256:sha(fs.readFileSync(__filename)),value:global.__commentContexts(),layoutExecuted:false,explicitGeometrySetup:true,pid:process.pid},null,2)+'\n',{flag:'wx'});
