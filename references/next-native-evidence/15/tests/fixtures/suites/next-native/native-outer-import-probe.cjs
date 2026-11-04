const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const[pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),wp=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(wp),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__outerImport=function(s){
 registerLayoutAlgorithms(['layered']);const ji=new JsonImporter,json=new JSONObject_0(JSON.parse(JSON.stringify(s.graph))),root=$transformNode_0(ji,json,null);$transformEdges_2(ji,json);
 const raw=s.selectChild?$getChildren(root).get_0(0):root,events=[];
 const create=$createLGraph,check=$checkExternalPorts,minimum=$calculateMinimumGraphSize,flat=$importFlatGraph;
 $createLGraph=function(n){events.push('create');return create(n);};$checkExternalPorts=function(n,p){events.push('checkExternal');return check(n,p);};$calculateMinimumGraphSize=function(n,g){events.push('minimum');return minimum(n,g);};$importFlatGraph=function(i,n,g){events.push('flat');return flat(i,n,g);};
 let graph;try{graph=$importGraph_1(new ElkGraphImporter,raw);}finally{$createLGraph=create;$checkExternalPorts=check;$calculateMinimumGraphSize=minimum;$importFlatGraph=flat;}
 const setNames=v=>{const result=[],it=v.iterator_0();while(it.hasNext_0())result.push(it.next_1().name_0);return result.sort();};
 const minimumValue=$hasProperty(graph,NODE_SIZE_MINIMUM_0)?$getProperty(graph,NODE_SIZE_MINIMUM_0):null;
 const labelList=[],labelIterator=raw.getLabels_0().iterator_0();while(labelIterator.hasNext_0())labelList.push(labelIterator.next_1());
 const placement=labelList.map(l=>({id:l.identifier,x:l.x_0,y:l.y_0,width:l.width_0,height:l.height}));
 return{id:s.id,events,padding:[graph.padding.top_0,graph.padding.right,graph.padding.bottom,graph.padding.left],direction:$getProperty(graph,DIRECTION).name_0,flags:setNames($getProperty(graph,GRAPH_PROPERTIES)),nativeConstraints:setNames($getProperty(graph,NODE_SIZE_CONSTRAINTS_1)),rawConstraints:setNames($getProperty_0(raw,NODE_SIZE_CONSTRAINTS_1)),minimum:minimumValue?[minimumValue.x_0,minimumValue.y_0]:null,rawPortConstraintsPresent:$hasProperty_0(raw,PORT_CONSTRAINTS_0),rawPortConstraints:$getProperty_0(raw,PORT_CONSTRAINTS_0).name_0,nodes:graph.layerlessNodes.array.map(n=>({id:$getProperty(n,ORIGIN_0).identifier,type:n.type_0.name_0,pos:[n.pos.x_0,n.pos.y_0],size:[n.size_0.x_0,n.size_0.y_0]})),rawLabels:placement,layoutExecuted:false};
};`;
const m=new Module(wp,module);m.filename=wp;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,wp);
const observation={cases:JSON.parse(requestRaw).cases.map(s=>global.__outerImport(s)),layoutExecuted:false};
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-outer-import/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
