// Original polygon predicates only; no rasterizer or packing provider.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__discoPolygon=function(s){
 const rectangle=new ElkRectangle_0(...s.rect),path=new LinkedList;s.path.forEach(v=>$add_7(path,new KVector_1(...v)));
 const element=new DCElement(path),component=new DCComponent,elements=new ArrayList;$add_3(elements,element);$addElements(component,elements);
 return {intersects:intersects_1(rectangle,path),contains:contains_51(rectangle,path),componentIntersects:$intersects(component,rectangle),tolerance:$intern_119,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__discoPolygon(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-disco-polygon-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
