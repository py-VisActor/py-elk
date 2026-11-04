const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const raw=fs.readFileSync(worker),req=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__rectHull=function(request){
 const num=v=>Number.isNaN(v)?'NaN':!Number.isFinite(v)?String(v):Object.is(v,-0)?'-0':v;
 const coord=p=>[num(p.x_0),num(p.y_0)],errors=[];
 const value=request.cases.map(c=>{
  const points=new ArrayList;for(const v of c.points)$add_3(points,new Point(v[0],v[1]));
  const originals=points.array.slice(),before=originals.map(coord);let hull,phase='of';
  try{
   hull=of_5(points);phase='split';const beforeHull=hull.hull.array.slice(),rects=$splitIntoRectangles(hull);
   return {name:c.name,failedPhase:null,extrema:[hull.xMax1,hull.xMin1,hull.xMin2,hull.yMax1,hull.yMin1].map(p=>originals.indexOf(p)),
    hull:hull.hull.array.map(p=>({point:coord(p),quadrant:p.quadrant.name_0,convex:p.convex,inputReference:originals.includes(p)})),
    rectangles:rects.array.map(r=>[r.x_0,r.y_0,r.width_0,r.height].map(num)),
    inputUnchanged:JSON.stringify(before)===JSON.stringify(points.array.map(coord))&&originals.every((p,i)=>points.array[i]===p),
    hullReferencesUnchanged:beforeHull.every((p,i)=>hull.hull.array[i]===p)};
  }catch(e){errors.push({name:c.name,phase,error:String(e),stack:e&&e.stack});return {name:c.name,failedPhase:phase};}
 });return {value,rawErrors:errors};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(req),pid:process.pid,parentPid:process.ppid,node:process.version,...global.__rectHull(JSON.parse(req)),actualRectHull:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
