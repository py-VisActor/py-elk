// Actual source identifier/import, provider body, and generic minimum helpers.
// These are three new boundary witnesses, not a whole macro layout pipeline.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__hostBoundaries=function(s){
 registerLayoutAlgorithms(['sporeCompaction']);
 const input=JSON.parse(JSON.stringify(s.graph)),ji=new JsonImporter,json=new JSONObject_0(input),root=$transformNode_0(ji,json,null);$transformEdges_2(ji,json);
 const list=l=>{const a=[],it=l.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const shape=n=>({id:n.identifier,pos:[n.x_0,n.y_0],size:[n.width_0,n.height],labels:list(n.getLabels_0()).map(l=>({pos:[l.x_0,l.y_0],size:[l.width_0,l.height]}))});
 const snapshot=()=>({root:shape(root),children:list($getChildren(root)).map(n=>({shape:shape(n),ports:list($getPorts_3(n)).map(shape)}))});
 if(s.operation==='numeric-root'){
  const importer=new ElkGraphImporter_0,g=$importGraph_2(importer,root);
  return {selectedIndex:g.vertices.array.indexOf(g.preferredRoot),identifierViews:list($getChildren(root)).map(n=>n.identifier),rawIds:input.children.map(n=>n.id),fullLayoutValidated:false};
 }
 if(s.operation==='invoke-box'){
  const marker=new Property('_v_host_marker');$setProperty_1(root,marker,17);const before=snapshot(),algorithm=$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.algorithm'),algorithmBefore=$getProperty_0(root,algorithm),unknown=$getAlgorithmDataBySuffix(SERVICE,'unknown.native.provider'),known=$getAlgorithmDataBySuffix(SERVICE,'box');
  const monitor=new BasicProgressMonitor,child=monitor.subTask(1);$fetch(known.providerPool).layout(root,child);
  return {before,after:snapshot(),unknownResolved:!!unknown,knownResolved:!!known,marker:$getProperty_0(root,marker),algorithmBefore,algorithmAfter:$getProperty_0(root,algorithm),underlyingProviderExecuted:'box',fullLayoutValidated:false};
 }
 const ga=new ElkGraphAdapters$ElkGraphAdapter(root),node=$getNodes_0(ga).array[0],before=snapshot(),size=process(ga,node,false,true);
 return {before,after:snapshot(),minimum:[size.x_0,size.y_0],applyStuff:false,ignoreInsidePortLabels:true,fullLayoutValidated:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__hostBoundaries(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-host-boundaries-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
