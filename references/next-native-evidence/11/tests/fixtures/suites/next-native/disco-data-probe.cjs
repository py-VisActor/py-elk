// Original DisCo data/cached bounds helpers only, no polygon intersection/packing.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__discoData=function(s){
 $clinit_DCDirection();const dirs={NORTH:NORTH_0,EAST:EAST_0,SOUTH:SOUTH_0,WEST:WEST_0};
 const n=v=>Number.isNaN(v)?'NaN':v===Infinity?'Infinity':v===-Infinity?'-Infinity':Object.is(v,-0)?'-0':v;
 const xy=v=>[n(v.x_0),n(v.y_0)],rect=r=>[n(r.x_0),n(r.y_0),n(r.width_0),n(r.height)];
 const al=xs=>{const l=new ArrayList;xs.forEach(x=>$add_3(l,x));return l;};
 const paths=s.polygons.map(ps=>{const l=new LinkedList;ps.forEach(p=>$add_7(l,new KVector_1(...p)));return l;});
 const elements=paths.map(p=>new DCElement(p));
 const extensions=s.extensions.map(e=>new DCExtension(elements[e.element],dirs[e.direction],new KVector_1(...e.middle),e.width));
 const component=new DCComponent;$addElements(component,al(elements));const first=$getDimensionsOfBoundingRectangle(component),corner=$getMinCorner(component),again=$getDimensionsOfBoundingRectangle(component);
 const offset=new KVector_1(...s.offset);$setOffset(component,offset);const moved=$getDimensionsOfBoundingRectangle(component),movedCorner=$getMinCorner(component);
 if(elements.length)$addElements(component,al([elements[0]]));const duplicate=$getDimensionsOfBoundingRectangle(component);
 const before=elements.map(e=>rect(e.bounds));if(paths.length)$getFirst(paths[0]).x_0=s.mutateFirstX;const after=elements.map(e=>rect(e.bounds));
 const groups=al(elements.length?[al([elements[0]]),al(elements.length>1?[elements[1],elements[0]]:[elements[0]])]:[]),graph=new DCGraph_0(groups),components=[];
 for(let i=graph.components.map_0.keySet_0().iterator_0();i.hasNext_0();)components.push(i.next_1());
 const shapeOrder=c=>{const out=[];for(let i=c.shapes.map_0.keySet_0().iterator_0();i.hasNext_0();)out.push(elements.indexOf(i.next_1()));return out;};
 return {before,after,shapeReferences:elements.map((e,i)=>e.shape_0===paths[i]),extensions:extensions.map(e=>({direction:e.direction.name_0,horizontal:e.direction.horizontal,offset:xy(e.offset),width:e.width_0})),first:xy(first),corner:xy(corner),sameCachedDimensions:first===again,moved:xy(moved),movedCorner:xy(movedCorner),offsetReference:component.offset===offset,recomputedAfterOffset:first!==moved,recomputedAfterDuplicate:elements.length?moved!==duplicate:false,shapeOrder:shapeOrder(component),graphComponentShapes:components.map(shapeOrder),reparentedToLast:elements.length?elements[0].cp===components[components.length-1]:null,cellSize:n($computeCellSize(graph)),layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__discoData(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-disco-data-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
