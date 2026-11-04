// Real DCPolyomino constructor and planar-grid overlay only; no layout/packer.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__polyRaster=function(s){
 $clinit_DCDirection();$clinit_Direction();const dirs={NORTH:NORTH_0,EAST:EAST_0,SOUTH:SOUTH_0,WEST:WEST_0};
 const al=xs=>{const l=new ArrayList;xs.forEach(x=>$add_3(l,x));return l;};
 const elements=s.polygons.map(ps=>{const p=new LinkedList;ps.forEach(v=>$add_7(p,new KVector_1(...v)));return new DCElement(p);});
 s.extensions.forEach(e=>new DCExtension(elements[e.element],dirs[e.direction],new KVector_1(...e.middle),e.width));
 const component=new DCComponent;$addElements(component,al(elements));
 const poly=new DCPolyomino(component,...s.cellSize),dest=new PlanarGrid(...s.destination);
 const cells=g=>Array.from({length:g.ySize},(_,y)=>Array.from({length:g.xSize},(_,x)=>Number(toInt_0($retrieve(g,x,y)))));
 const bounds=g=>{const v=$getFilledBounds(g);return [v.first.value_0,v.second.value_0,v.third.value_0,v.fourth.value_0];};
 s.existing.forEach(([x,y,v])=>$set_4(dest,x,y,!!(v&2),!!(v&1)));
 const raster=cells(poly),filledBounds=bounds(poly),extensions=poly.polyominoExtensions.array.map(e=>[e.first.name_0,e.second.value_0,e.third.value_0]);
 const collisionBefore=$intersectsWithCenterBased_0(dest,poly,...s.offset);
 $addFilledCellsFrom_0(dest,poly,...s.offset);
 return {dimensions:[poly.pWidth,poly.pHeight],raster,filledBounds,extensions,position:[poly.x_0,poly.y_0],destination:cells(dest),destinationBounds:bounds(dest),collisionBefore,collisionAfter:$intersectsWithCenterBased_0(dest,poly,...s.offset),representeeSame:poly.representee===component,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__polyRaster(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-polyomino-raster-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
