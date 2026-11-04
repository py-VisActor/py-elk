// Original geometric value protocol and TD04/05 helpers, not a layout provider.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__triangulationProbe=function(s){
 const points=s.points.map(p=>new KVector_1(...p)),xy=v=>[v.x_0,v.y_0];
 const number=v=>Number.isNaN(v)?'NaN':v===Infinity?'Infinity':v===-Infinity?'-Infinity':Object.is(v,-0)?'-0':v;
 const encoded=v=>xy(v).map(number),list=xs=>{const a=[];for(let i=xs.map_0.keySet_0().iterator_0();i.hasNext_0();)a.push(i.next_1());return a;};
 const edges=xs=>list(xs).map(e=>[points.indexOf(e.u),points.indexOf(e.v)]);
 const setOf=xs=>{const set=new HashSet;xs.forEach(x=>$add_6(set,x));return set;};
 if(s.operation==='hashes')return {hashes:points.map(hashCode_55),coordinates:points.map(encoded),fullLayoutValidated:false};
 if(s.operation==='buckets'){
   const set=new HashSet,steps=[],snapshot=()=>list(set).map(v=>points.indexOf(v));
   points.forEach(v=>$add_6(set,v));steps.push(snapshot());
   const removedFirst=$remove_18(set,points[0]);steps.push(snapshot());
   const removedLastCollision=$remove_18(set,points[2]);steps.push(snapshot());
   const readded=$add_6(set,points[0]);steps.push(snapshot());
   const duplicate=$add_6(set,new KVector_1(points[0].x_0,points[0].y_0));steps.push(snapshot());
   return {steps,removedFirst,removedLastCollision,readded,duplicate,size:set.map_0.size_1(),fullLayoutValidated:false};
 }
 if(s.operation==='triangle'){
   const broad=new TTriangle(...points),repeated=new TTriangle(points[0],points[0],points[0]);
   const first=setOf([broad,repeated]),second=setOf([repeated,broad]);
   return {broadEqualsRepeated:broad.equals_0(repeated),repeatedEqualsBroad:repeated.equals_0(broad),hashes:[hashCode_55(broad),hashCode_55(repeated)],circumcenters:[encoded(broad.circumcenter),encoded(repeated.circumcenter)],insertBroadThenRepeated:list(first).map(t=>t===broad?'broad':'repeated'),insertRepeatedThenBroad:list(second).map(t=>t===broad?'broad':'repeated'),fullLayoutValidated:false};
 }
 if(s.operation==='triangulate'){
   const input=new ArrayList;points.forEach(v=>$add_3(input,v));
   return {edges:edges(triangulate(input)),fullLayoutValidated:false};
 }
 const es=s.edges.map(e=>new TEdge(points[e[0]],points[e[1]])),set=setOf(es),costCalls=[];
 const result=createSpanningTree(set,points[s.root],{cost:e=>{const i=es.indexOf(e);costCalls.push(i);return s.costs[i];}});
 const tree=t=>({node:points.indexOf(t.node),children:t.children.array.map(tree)});
 return {inputEdgeOrder:edges(set),costCalls,tree:tree(result),fullLayoutValidated:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__triangulationProbe(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-triangulation-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
