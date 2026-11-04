// Actual SweepCopy restore and NS side/anchor leaf with supplied intermediate order.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__sweepTransfer=function(s){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_PortSide();$clinit_PortConstraints();$clinit_LNode$NodeType();
 const g=new LGraph,layer=new Layer(g);$add_3(g.layers,layer);
 const owner=new LNode(g),dummy=new LNode(g);dummy.type_0=NORTH_SOUTH_PORT;$setLayer(owner,0,layer);$setLayer(dummy,1,layer);
 const active=new LPort,other=new LPort,dp=new LPort;$setNode(active,owner);$setNode(other,owner);$setNode(dp,dummy);
 [active.size_0.x_0,active.size_0.y_0]=s.size;active.explicitlySuppliedPortAnchor=true;[active.anchor.x_0,active.anchor.y_0]=s.anchor;
 $setSide(active,s.side==='NORTH'?NORTH_3:SOUTH_2);$setSide(other,EAST_2);$setSide(dp,EAST_2);
 $setProperty_0(owner,PORT_CONSTRAINTS_0,s.constraint==='FIXED_RATIO'?FIXED_RATIO:FREE);$setProperty_0(dummy,IN_LAYER_LAYOUT_UNIT,owner);$setProperty_0(dp,ORIGIN_0,active);
 const row=stampJavaTypeInfo(getClassLiteralForArray(Lorg_eclipse_elk_alg_layered_graph_LNode_2_classLit,1),$intern_108,9,0,s.ownerFirst?[owner,dummy]:[dummy,owner]),captured=new SweepCopy_0([row]);
 const layerList=layer.nodes,ownerPorts=owner.ports,dummyPorts=dummy.ports;owner.ports.array.reverse();
 $transferNodeAndPortOrdersToGraph_0(captured,g);
 const names=new Map([[owner,'owner'],[dummy,'dummy'],[active,'active'],[other,'other'],[dp,'dummyPort']]);
 const node=n=>{const ranges={};if(n.portSideIndices)for(const side of [NORTH_3,EAST_2,SOUTH_2,WEST_2]){const pair=$get_14(n.portSideIndices,side);if(pair)ranges[side.name_0]=[pair.first.value_0,pair.second.value_0];}return{name:names.get(n),id:n.id_0,constraint:$getProperty(n,PORT_CONSTRAINTS_0).name_0,ports:n.ports.array.map(p=>({name:names.get(p),side:p.side.name_0,anchor:[p.anchor.x_0,p.anchor.y_0]})),cached:!!n.portSidesCached,ranges,graphRetained:n.graph_0===g,layerRetained:n.layer===layer};};
 return {order:layer.nodes.array.map(n=>names.get(n)),owner:node(owner),dummy:node(dummy),layerListIdentity:layer.nodes===layerList,ownerPortListIdentity:owner.ports===ownerPorts,dummyPortListIdentity:dummy.ports===dummyPorts,orderSupplied:true,counterExecuted:false,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__sweepTransfer(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-sweep-transfer-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
