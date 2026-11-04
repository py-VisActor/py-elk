const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [packageArg,requestPath,out]=process.argv.slice(2),pkg=path.resolve(packageArg),worker=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
global.__directionRequest=request;
const bridge=String.raw`
global.__newDirectionContext=function(){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_PortSide();$clinit_Direction_0();$clinit_DirectionCongruency();$clinit_GraphTransformer$Mode();
 const r=global.__directionRequest,g=new LGraph,n=new LNode(g),ports=[],tokens=[],events=[];
 $add_3(g.layerlessNodes,n);g.size_0.x_0=100;g.size_0.y_0=80;g.offset.x_0=2;g.offset.y_0=3;
 $setProperty_0(g,DIRECTION,DOWN_1);$setProperty_0(g,DIRECTION_CONGRUENCY_0,READING_DIRECTION);
 n.pos.x_0=3;n.pos.y_0=4;n.size_0.x_0=20;n.size_0.y_0=10;
 n.padding.top_0=1;n.padding.right=2;n.padding.bottom=3;n.padding.left=4;
 for(let i=0;i<3;i++){
  const p=new LPort;$setNode(p,n);p.size_0.x_0=2;p.size_0.y_0=3;
  $setSide(p,[EAST_2,SOUTH_2,WEST_2][i]);p.pos.x_0=i+1;p.pos.y_0=i+2;p.anchor.x_0=.25;p.anchor.y_0=.75;
  const t=valueOf_3(r.indices[i]);$setProperty_0(p,PORT_INDEX,t);ports.push(p);tokens.push(t);
 }
 const edge=new LEdge;$setSource_0(edge,ports[0]);$setTarget_0(edge,ports[1]);
 const bend=new KVector_1(...r.bend);$add_7(edge.bendPoints,bend);
 const chain=new KVectorChain,junction=new KVector_1(...r.junction);$add_7(chain,junction);$setProperty_0(edge,JUNCTION_POINTS,chain);
 const before=[$hasProperty(g,NODE_LABELS_PADDING),$hasProperty(n,NODE_SIZE_MINIMUM_0)];
 const transformer=new GraphTransformer(TO_INTERNAL_LTR);
 $process_12(transformer,g,{begin:(name,work)=>events.push(['begin',name,work]),done_1:()=>events.push(['done'])});
 const point=v=>[v.x_0,v.y_0],ins=v=>[v.top_0,v.right,v.bottom,v.left],num=v=>Object.is(v,-0)?'-0':v;
 return {events,graphSize:point(g.size_0),graphOffset:point(g.offset),nodePos:point(n.pos),nodeSize:point(n.size_0),nodePadding:ins(n.padding),
  ports:ports.map(p=>({side:p.side.name_0,pos:point(p.pos),size:point(p.size_0),anchor:point(p.anchor),index:num($getProperty(p,PORT_INDEX).value_0)})),
  zeroCached:$getProperty(ports[0],PORT_INDEX)===valueOf_3(0),uncachedFresh:$getProperty(ports[1],PORT_INDEX)!==valueOf_3(-129),
  typedChainSame:$getProperty(edge,JUNCTION_POINTS)===chain,junctionSame:$get_7(chain,0)===junction,bendSame:$get_7(edge.bendPoints,0)===bend,junction:point(junction),bend:point(bend),
  presenceBefore:before,presenceAfter:[$hasProperty(g,NODE_LABELS_PADDING),$hasProperty(n,NODE_SIZE_MINIMUM_0)],nodeMinimum:point($getProperty(n,NODE_SIZE_MINIMUM_0)),graphLabelPadding:ins($getProperty(g,NODE_LABELS_PADDING)),
  edgeLabelsSide:$getProperty(g,EDGE_LABELS_SIDE_SELECTION_0).name_0,labelsEmpty:n.labels.array.length===0&&ports.every(p=>p.labels.array.length===0)&&edge.labels.array.length===0};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const value=global.__newDirectionContext();
fs.writeFileSync(out,JSON.stringify({workerSha256:sha(raw),requestSha256:sha(fs.readFileSync(requestPath)),probeSha256:sha(fs.readFileSync(__filename)),value,pid:process.pid,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
