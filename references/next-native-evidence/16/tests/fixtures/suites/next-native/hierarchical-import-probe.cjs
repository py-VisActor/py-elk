const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const[pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),wp=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(wp),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__hierImport=function(s){
 registerLayoutAlgorithms(['layered']);const ji=new JsonImporter,json=new JSONObject_0(JSON.parse(JSON.stringify(s.graph))),root=$transformNode_0(ji,json,null);$transformEdges_2(ji,json);
 const rawNodes=[],rawEdges=[];function visit(n){rawNodes.push(n);if(n.containedEdges){const it=n.containedEdges.iterator_0();while(it.hasNext_0())rawEdges.push(it.next_1());}if(n.children){const it=n.children.iterator_0();while(it.hasNext_0())visit(it.next_1());}}visit(root);
 const events=[],nativeEdges=[],create=$createLGraph,node=$transformNode,edge=$transformEdge,check=$checkEdgeValidity;
 $createLGraph=function(n){events.push('graph:'+n.identifier);return create(n);};
 $transformNode=function(i,n,g){events.push('node:'+n.identifier);return node(i,n,g);};
 $checkEdgeValidity=function(e){events.push('check:'+e.identifier);return check(e);};
 $transformEdge=function(i,e,p,g){events.push('edge:'+e.identifier);const value=edge(i,e,p,g);nativeEdges.push([e,value,g]);return value;};
 const importer=new ElkGraphImporter;let graph;try{graph=$importGraph_1(importer,root);}finally{$createLGraph=create;$transformNode=node;$transformEdge=edge;$checkEdgeValidity=check;}
 const graphId=g=>g?$getProperty(g,ORIGIN_0).identifier:null;
 const integer=v=>v===null?null:v.value_0;
 const order=n=>$hasProperty_0(n,MODEL_ORDER_2)?integer($getProperty_0(n,MODEL_ORDER_2)):null;
 return{id:s.id,events,rawOrders:rawNodes.concat(rawEdges).map(n=>({id:n.identifier,order:order(n)})),maxOrder:integer($getProperty(graph,MAX_MODEL_ORDER_NODES)),groups:integer($getProperty(graph,CB_NUM_MODEL_ORDER_GROUPS)),nodes:rawNodes.slice(1).map(n=>{const v=$get_10(importer.nodeAndPortMap,n);return{id:n.identifier,imported:!!v,graph:v?graphId($getGraph(v)):null,nested:v?graphId(v.nestedGraph):null,nestedDirection:v&&v.nestedGraph?$getProperty(v.nestedGraph,DIRECTION).name_0:null,parentIdentity:!!(v&&v.nestedGraph&&v.nestedGraph.parentNode===v)};}),edges:nativeEdges.map(([e,v,g])=>({id:e.identifier,graph:graphId(g),coordinateOrigin:graphId($getProperty(v,COORDINATE_SYSTEM_ORIGIN)),coordinatePresent:$hasProperty(v,COORDINATE_SYSTEM_ORIGIN)})),layoutExecuted:false};
};`;
const m=new Module(wp,module);m.filename=wp;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,wp);
const observation={cases:JSON.parse(requestRaw).cases.map(s=>global.__hierImport(s)),layoutExecuted:false};
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-hierarchical-import/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
