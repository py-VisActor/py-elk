// Original PG01/04 storage, bounds/center helpers only; no raster/packer.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__gridFoundation=function(s){
 const g=new PlanarGrid(...s.size),snapshot=()=>({size:[g.xSize,g.ySize],center:[g.xCenter,g.yCenter],wordCounts:g.grid.map(row=>row.length),cells:Array.from({length:g.ySize},(_,y)=>Array.from({length:g.xSize},(_,x)=>toInt_0($retrieve(g,x,y)))),text:g.toString_0()});
 const attempt=f=>{try{return{outcome:'returned',value:f()};}catch(e){return{outcome:'threw',error:{name:String(e.name),message:String(e.message),text:String(e)}};}};
 if(s.operation==='words'){
  s.sets.forEach(a=>$set_4(g,...a));
  const flags=s.sets.map(([x,y])=>({x,y,empty:$isEmpty_0(g,x,y),blocked:$isBlocked(g,x,y),weak:$isWeaklyBlocked(g,x,y)}));
  return {snapshot:snapshot(),flags,reads:s.reads.map(([x,y])=>({x,y,result:attempt(()=>toInt_0($retrieve(g,x,y)))})),badSets:s.badSets.map(a=>({x:a[0],y:a[1],result:attempt(()=>{$set_4(g,...a);return null;})})),layoutExecuted:false};
 }
 $setBlockedCenterBased(g,0,0);$setWeaklyBlockedCenterBased(g,-2,-1);$weaklyBlockArea(g,...s.weakArea);
 const before=snapshot(),weakOnlyAreaIntersects=$weaklyIntersectsArea(g,0,0,1,0),allAreaIntersects=$weaklyIntersectsArea(g,...s.weakArea),centerFlags={blocked:$isBlockedCenterBased(g,0,0),weak:$isWeaklyBlockedCenterBased(g,-2,-1),empty:$isEmptyCenterBased(g,1,0)};
 const grid=g.grid;$reinitialize(g,...s.reinitialize);
 return {before,weakOnlyAreaIntersects,allAreaIntersects,centerFlags,after:snapshot(),storageReplaced:g.grid!==grid,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__gridFoundation(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-polyomino-grid-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
