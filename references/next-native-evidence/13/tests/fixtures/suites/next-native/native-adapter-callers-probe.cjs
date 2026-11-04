const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__nativeAdapterCallers=function(){
 $clinit_CoreOptions();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LGraphAdapters();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_EdgeLabelPlacement();$clinit_PortLabelPlacement();
 const array=list=>{const o=[],i=list.iterator_0();while(i.hasNext_0())o.push(i.next_1());return o;},vec=v=>[v.x_0,v.y_0],ins=v=>[v.top_0,v.right,v.bottom,v.left];
 const label=(x,y,w,h)=>{const l=new LLabel;l.pos.x_0=x;l.pos.y_0=y;l.size_0.x_0=w;l.size_0.y_0=h;return l;};
 const graph=new LGraph,layer=new Layer(graph);$add_3(graph.layers,layer);const node=new LNode(graph);$setLayer(node,0,layer);node.pos.x_0=10;node.pos.y_0=20;node.size_0.x_0=40;node.size_0.y_0=30;
 const port=new LPort;$setNode(port,node);port.side=EAST_2;port.pos.x_0=40;port.pos.y_0=8;port.size_0.x_0=4;port.size_0.y_0=3;
 const own=new LEdge;own.id_0=1;$add_3(port.incomingEdges,own);$add_3(port.outgoingEdges,own);
 const dummy=new LNode(graph),dp=new LPort;$setNode(dp,dummy);const extra=new LEdge;extra.id_0=2;$add_3(dp.incomingEdges,own);$add_3(dp.incomingEdges,extra);$add_3(dp.outgoingEdges,extra);$setProperty_0(port,PORT_DUMMY,dummy);
 const pv=new LGraphAdapters$LPortAdapter(port,true),incoming=pv.getIncomingEdges(),outgoing=pv.getOutgoingEdges();$add_3(port.incomingEdges,extra);
 const ns=new LNode(graph);ns.type_0=NORTH_SOUTH_PORT;const nsp=new LPort;$setNode(nsp,ns);$add_3(nsp.incomingEdges,own);$setProperty_0(nsp,PORT_DUMMY,dummy);const nsv=new LGraphAdapters$LPortAdapter(nsp,true);
 const p2=new LPort;$setNode(p2,node);p2.side=EAST_2;p2.pos.y_0=-2;$setProperty_0(port,PORT_INDEX,valueOf_3(0));$setProperty_0(p2,PORT_INDEX,valueOf_3(2));const indexed=$compare_10(port,p2);$setProperty_0(p2,PORT_INDEX,null);const geometric=$compare_10(port,p2);
 const portResult={incoming:array(incoming).map(e=>e.element.id_0),outgoing:array(outgoing).map(e=>e.element.id_0),sameCache:incoming===pv.getIncomingEdges(),nsEmpty:array(nsv.getIncomingEdges()).length===0,nsSameEmpty:nsv.getIncomingEdges()===nsv.getOutgoingEdges(),indexed,geometric,anchorNull:pv.getProperty(PORT_ANCHOR_0)===null,anchorHas:pv.hasProperty(PORT_ANCHOR_0)};
 // Margin is a separate actual adapter, without north/south transparency.
 $add_3(node.labels,label(-7,-8,20,6));$add_3(port.labels,label(2,-4,13,7));const tail=label(999,999,20,9),head=label(999,999,12,8);$setProperty_0(tail,EDGE_LABELS_PLACEMENT_0,TAIL);$setProperty_0(head,EDGE_LABELS_PLACEMENT_0,HEAD);$add_3(own.labels,tail);$add_3(own.labels,head);
 const ga=new LGraphAdapters$LGraphAdapter(graph,false,false,{test_0(){return true;}}),calc=new NodeMarginCalculator(ga);$process(calc);const full=ins(node.margin);$process($excludeEdgeHeadTailLabels(calc));const withoutEdges=ins(node.margin);
 // A different graph exercises the actual label/size processor wrapper.
 const sg=new LGraph,sl=new Layer(sg);$add_3(sg.layers,sl);const sn=new LNode(sg);$setLayer(sn,0,sl);sn.size_0.x_0=30;sn.size_0.y_0=20;const sp=new LPort;$setNode(sp,sn);sp.side=EAST_2;sp.size_0.x_0=2;sp.size_0.y_0=3;$add_3(sp.labels,label(0,0,12,6));$add_3(sn.labels,label(0,0,18,7));
 $process_25(sg,new BasicProgressMonitor);
 const sized={size:vec(sn.size_0),padding:ins(sn.padding),port:vec(sp.pos),portLabel:vec(sp.labels.array[0].pos),nodeLabel:vec(sn.labels.array[0].pos),portId:sp.id_0};
 const ext=new LNode(sg),ep=new LPort;$setNode(ep,ext);ext.size_0.x_0=20;ext.size_0.y_0=40;ep.pos.x_0=5;ep.pos.y_0=7;ep.connectedToExternalNodes=false;$add_3(ep.labels,label(0,0,8,3));$add_3(ep.labels,label(0,0,6,4));$setProperty_0(ext,EXT_PORT_SIDE,EAST_2);
 const outside=new HashSet;outside.add_2(OUTSIDE_0); // membership-only observation holder
 $placeExternalPortDummyLabels(ext,outside,true,true);const outsidePositions=ep.labels.array.map(l=>vec(l.pos));const inside=new HashSet;inside.add_2(INSIDE_0);$setProperty_0(ext,EXT_PORT_SIDE,NORTH_3);$placeExternalPortDummyLabels(ext,inside,true,false);
 return {ports:portResult,margin:{full,withoutEdges},sized,external:{outside:outsidePositions,inside:ep.labels.array.map(l=>vec(l.pos))}};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__nativeAdapterCallers(),preparedViews:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
