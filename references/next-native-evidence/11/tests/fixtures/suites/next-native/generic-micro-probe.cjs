// Actual JSON importer -> generic ElkGraphAdapter -> NodeMicroLayout, with no
// provider layout. Given label dimensions are source input, not text estimates.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__genericMicro=function(s){
 getInstance();$clinit_CoreOptions();
 const importer=new JsonImporter,json=new JSONObject_0(JSON.parse(JSON.stringify(s.graph))),root=$transformNode_0(importer,json,null);$transformEdges_2(importer,json);
 const ga=new ElkGraphAdapters$ElkGraphAdapter(root),nodes=$getNodes_0(ga).array;
 const list=l=>{const a=[],it=l.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const shape=x=>({id:x.identifier,pos:[x.x_0,x.y_0],size:[x.width_0,x.height],labels:list(x.getLabels_0()).map(l=>({pos:[l.x_0,l.y_0],size:[l.width_0,l.height]}))});
 const snapshot=before=>nodes.map(n=>({shape:shape(n.element),ports:(before?list($getPorts_3(n.element)).map(p=>new ElkGraphAdapters$ElkPortAdapter(p)):n.getPorts().array).map(p=>({shape:shape(p.element),compoundConnections:p.hasCompoundConnections()}))}));
 // Do not populate the shared adapter's port cache before source sortPortLists.
 const before=snapshot(true);$execute(new NodeMicroLayout(ga));
 const after=snapshot(false),margins=nodes.map(n=>{const p=n.getMargin();return[p.top_0,p.right,p.bottom,p.left];});
 return {before,after,margins};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__genericMicro(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-generic-micro-observation/v1',mode:'unchanged-worker-JSON-import-and-generic-micro',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
