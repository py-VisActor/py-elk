// Real source importer/cost/update/transfer over JSON and explicitly supplied
// intermediate translations. The collision case controls Math.random and is
// labelled instrumented; no complete packing layout is executed.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__sporeImport=function(s){
 registerLayoutAlgorithms(['sporeCompaction']);
 const input=JSON.parse(JSON.stringify(s.graph)),ji=new JsonImporter,root=$transformNode_0(ji,new JSONObject_0(input),null);$transformEdges_2(ji,new JSONObject_0(input));
 const importer=new ElkGraphImporter_0,draws=[],previousRandom=$wnd.Math.random;let graph;
 if(s.draws){let index=0;$wnd.Math.random=()=>{if(index>=s.draws.length)throw Error('Instrumented entropy exhausted');const v=s.draws[index++];draws.push(v);return v;};}
 try{graph=$importGraph_2(importer,root);}finally{$wnd.Math.random=previousRandom;}
 const list=l=>{const a=[],it=l.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;},xy=v=>[v.x_0,v.y_0],bounds=r=>[r.x_0,r.y_0,r.width_0,r.height];
 const scalar=v=>Number.isFinite(v)?{value:v,negativeZero:Object.is(v,-0)}:{nonfinite:Number.isNaN(v)?'NaN':v===Infinity?'+Infinity':'-Infinity'};
 function imported(){return graph.vertices.array.map(n=>({id:$get_10(importer.nodeMap,n.originalVertex).second.identifier,original:xy(n.originalVertex),working:xy(n.vertex),rectangle:bounds(n.rect)}));}
 const originalRefs=graph.vertices.array.map(n=>n.originalVertex),workingRefs=graph.vertices.array.map(n=>n.vertex),before=imported();
 const costs=()=>{const edge=new TEdge(graph.vertices.array[0].originalVertex,graph.vertices.array[1].originalVertex);return[importer.centerDistance,importer.minimumRootDistance,importer.circleUnderlap,importer.rectangleUnderlap,importer.invertedOverlap].map(f=>scalar(f.cost(edge)));};
 const beforeCosts=costs(),direction=scalar($distance(graph.vertices.array[0],graph.vertices.array[1],new KVector_1(...s.direction)));
 const preferredRoot=graph.preferredRoot?$get_10(importer.nodeMap,graph.preferredRoot.originalVertex).second.identifier:null;
 graph.vertices.array.forEach((n,i)=>$translate(n,new KVector_1(...s.translations[i])));
 graph.tree={marker:true};graph.tEdges={marker:true};$updateGraph(importer,graph);
 const updated=imported(),afterCosts=costs(),workingIdentity=graph.vertices.array.map((n,i)=>n.vertex===workingRefs[i]),originalIdentityReplaced=graph.vertices.array.map((n,i)=>n.originalVertex!==originalRefs[i]);
 $applyPositions_0(importer,graph);
 function shape(n){return{id:n.identifier,pos:[n.x_0,n.y_0],size:[n.width_0,n.height],labels:list(n.getLabels_0()).map(l=>({pos:[l.x_0,l.y_0],size:[l.width_0,l.height]}))};}
 const children=list($getChildren(root)).map(n=>({shape:shape(n),ports:list($getPorts_3(n)).map(shape),margin:(()=>{const m=$getProperty_0(n,MARGINS_0);return[m.top_0,m.right,m.bottom,m.left];})()}));
 const edgeGeometry=list($getContainedEdges(root)).map(e=>({id:e.identifier,sections:list(e.sections).map(sec=>({start:[sec.startX,sec.startY],end:[sec.endX,sec.endY],bends:sec.bendPoints?list(sec.bendPoints).map(p=>[p.x_0,p.y_0]):[]}))}));
 return{before,beforeCosts,direction,preferredRoot,updated,afterCosts,workingIdentity,originalIdentityReplaced,treeCleared:graph.tree===null,edgesCleared:graph.tEdges===null,root:shape(root),children,edgeGeometry,draws,instrumentedEntropy:!!s.draws,inputPreserved:JSON.stringify(input)===JSON.stringify(s.graph),intermediateTranslationsSupplied:true,fullLayoutValidated:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__sporeImport(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-spore-import-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
