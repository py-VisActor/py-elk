const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__slMargin=function(){
 $clinit_CoreOptions();$clinit_InternalProperties_1();$clinit_LGraphAdapters();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_EdgeLabelPlacement();
 const arr=list=>{const a=[],i=list.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;},edges=l=>arr(l).map(x=>x.element.id_0),ins=v=>[v.top_0,v.right,v.bottom,v.left];
 const g=new LGraph,layer=new Layer(g);$add_3(g.layers,layer);const n=new LNode(g);$setLayer(n,0,layer);n.pos.x_0=11;n.pos.y_0=12;n.size_0.x_0=30;n.size_0.y_0=20;const p=new LPort;$setNode(p,n);p.side=WEST_2;p.pos.x_0=-3;p.pos.y_0=8;p.size_0.x_0=3;p.size_0.y_0=4;
 const e=new LEdge;e.id_0=7;$setSource_0(e,p);$setTarget_0(e,p);const slh=new SelfLoopHolder(n),slp=new SelfLoopPort(p);$put_11(slh.slPorts,p,slp);new SelfLoopEdge(e,slp,slp);$setProperty_0(n,SELF_LOOP_HOLDER,slh);
 const dummy=new LNode(g),dp=new LPort;$setNode(dp,dummy);const de=new LEdge;de.id_0=9;$add_3(dp.incomingEdges,de);$add_3(dp.outgoingEdges,de);$setProperty_0(p,PORT_DUMMY,dummy);
 const v=new LGraphAdapters$LPortAdapter(p,true),incoming=v.getIncomingEdges(),outgoing=v.getOutgoingEdges(),rawView=new LGraphAdapters$LPortAdapter(p,false);const initial={incoming:edges(incoming),outgoing:edges(outgoing),nontransparent:edges(rawView.getIncomingEdges())};
 // A new entry after cached edge retrieval does not mutate the returned list.
 const later=new LEdge;later.id_0=10;new SelfLoopEdge(later,slp,slp);initial.cached=edges(v.getIncomingEdges());initial.same=incoming===v.getIncomingEdges();
 const missing=new LPort;$setNode(missing,n);const missingView=new LGraphAdapters$LPortAdapter(missing,true);initial.missingPort=edges(missingView.getIncomingEdges());
 const l=new LLabel;l.pos.x_0=-9;l.pos.y_0=-5;l.size_0.x_0=8;l.size_0.y_0=4;$add_3(n.labels,l);const pl=new LLabel;pl.pos.x_0=-6;pl.pos.y_0=0;pl.size_0.x_0=5;pl.size_0.y_0=7;$add_3(p.labels,pl);const edgeLabel=new LLabel;edgeLabel.size_0.x_0=80;edgeLabel.size_0.y_0=40;$setProperty_0(edgeLabel,EDGE_LABELS_PLACEMENT_0,HEAD);$add_3(e.labels,edgeLabel);
 const monitor=new BasicProgressMonitor;$process_22(g,monitor);return {sl:initial,innermost:{margin:ins(n.margin),position:[n.pos.x_0,n.pos.y_0],size:[n.size_0.x_0,n.size_0.y_0],label:[l.pos.x_0,l.pos.y_0],portLabel:[pl.pos.x_0,pl.pos.y_0],monitorRunning:monitor.isRunning(),physicalEdgeLabelSize:[edgeLabel.size_0.x_0,edgeLabel.size_0.y_0]}};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__slMargin(),preparedViews:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
