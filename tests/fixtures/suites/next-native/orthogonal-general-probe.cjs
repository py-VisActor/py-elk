// New real Orthogonal phase: external boundaries, nonzero anchors, critical ring.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__orthogonalGeneral=function(s){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_PortSide();
 const g=new LGraph,nodes={},ports={},edges={},nodeIds=new Map;
 const enumValue=(klass,name)=>castTo($getEnumConstants(klass),10).find(v=>v.name_0===name);
 for(const item of s.nodes){const n=new LNode(g);nodes[item.id]=n;nodeIds.set(n,item.id);n.type_0=enumValue(Lorg_eclipse_elk_alg_layered_graph_LNode$NodeType_2_classLit,item.type);n.pos.y_0=item.y;n.size_0.x_0=item.width;n.size_0.y_0=4;
  $setProperty_0(n,ALIGNMENT,enumValue(Lorg_eclipse_elk_core_options_Alignment_2_classLit,item.alignment));if(item.externalSide)$setProperty_0(n,EXT_PORT_SIDE,item.externalSide==='WEST'?WEST_2:EAST_2);}
 s.layers.forEach((item,i)=>{const l=new Layer(g);l.id_0=i;l.size_0.x_0=item.width;$add_3(g.layers,l);item.nodes.forEach((id,j)=>$setLayer(nodes[id],j,l));});
 for(const [id,owner,side,y,anchor] of s.ports){const p=new LPort;ports[id]=p;$setNode(p,nodes[owner]);$setSide(p,side==='WEST'?WEST_2:EAST_2);p.pos.y_0=y;p.anchor.y_0=anchor;}
 for(const [id,a,b] of s.edges){const e=new LEdge;edges[id]=e;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);}
 const existing=new KVectorChain;$addNode_0(existing,new KVector_1(s.preexistingJunction.x,s.preexistingJunction.y),existing.tail.prev,existing.tail);$setProperty_0(edges[s.preexistingJunction.edge],JUNCTION_POINTS,existing);
 $setProperty_0(g,SPACING_NODE_NODE_BETWEEN_LAYERS_0,s.spacing.nodeNode);$setProperty_0(g,SPACING_EDGE_EDGE_BETWEEN_LAYERS_0,s.spacing.edgeEdge);$setProperty_0(g,SPACING_EDGE_NODE_BETWEEN_LAYERS_0,s.spacing.edgeNode);$setProperty_0(g,RANDOM_0,new Random_0(s.seed));
 const calls=[],draws=[],saved=[$routeEdges_0,$splitSegments,$nextInt];
 $routeEdges_0=function(...args){const result=saved[0](...args);calls.push({kind:'gap',left:args[2]?args[2].array.map(n=>nodeIds.get(n)):null,right:args[3]?args[3].array.map(n=>nodeIds.get(n)):null,start:args[4],slots:result});return result;};
 $splitSegments=function(...args){const before=args[2].array.length,result=saved[1](...args);calls.push({kind:'split',dependencies:args[1].array.length,before,after:args[2].array.length,threshold:args[3]});return result;};
 $nextInt=function(...args){draws.push(args[1]);return saved[2](...args);};
 const monitor=new BasicProgressMonitor;try{$process_84(g,monitor);}finally{[$routeEdges_0,$splitSegments,$nextInt]=saved;}
 const array=list=>{const out=[],it=list.iterator_0();while(it.hasNext_0())out.push(it.next_1());return out;};
 return {width:g.size_0.x_0,nodes:s.nodes.map(item=>({id:item.id,x:nodes[item.id].pos.x_0,y:nodes[item.id].pos.y_0})),edges:s.edges.map(([id])=>{const edge=edges[id],has=$hasProperty(edge,JUNCTION_POINTS);return {id,bends:array(edge.bendPoints).map(p=>[p.x_0,p.y_0]),hasJunction:has,junctions:has?array($getProperty(edge,JUNCTION_POINTS)).map(p=>[p.x_0,p.y_0]):null};}),existingChainPreserved:$getProperty(edges[s.preexistingJunction.edge],JUNCTION_POINTS)===existing,calls,draws,monitor:{name:monitor.taskName,closed:monitor.closed_0},layoutExecuted:false,workingGraphPhaseExecuted:true};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__orthogonalGeneral(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-orthogonal-general-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
