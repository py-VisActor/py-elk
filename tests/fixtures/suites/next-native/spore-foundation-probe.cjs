// Original SPOrE data/geometry only; no importer, jitter or provider.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__sporeFoundation=function(s){
 const rect=r=>new ElkRectangle_0(...r),vector=v=>new KVector_1(...v),xy=v=>[v.x_0,v.y_0],bounds=r=>[r.x_0,r.y_0,r.width_0,r.height];
 const original=vector(s.vertex),r=rect(s.rectangle),other=new Node_0(vector(s.otherVertex),rect(s.other)),node=new Node_0(original,r);
 const cost={},tree={},comp={},g=new Graph(cost,tree,comp),g2=new Graph(cost,tree,comp);
 const before={vertex:xy(node.vertex),rectangle:bounds(node.rect),underlap:$underlap(node,other),overlap:overlap_0(node.rect,other.rect)};
 $translate(node,vector(s.translate));const translated={vertex:xy(node.vertex),rectangle:bounds(node.rect)};
 $setCenterPosition(node,vector(s.center));
 return {before,translated,after:{vertex:xy(node.vertex),rectangle:bounds(node.rect)},originalVertex:xy(original),originalRectangle:bounds(r),originalVertexReference:node.originalVertex===original,workingVertexIndependent:node.vertex!==original,workingRectangleIndependent:node.rect!==r,graph:{vertices:g.vertices.array,costIdentity:g.costFunction===cost,treeIdentity:g.treeConstructionStrategy===tree,compactionIdentity:g.compactionStrategy===comp,independentVertices:g.vertices!==g2.vertices,orthogonalCompaction:g.orthogonalCompaction},fullLayoutValidated:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__sporeFoundation(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-spore-foundation-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
