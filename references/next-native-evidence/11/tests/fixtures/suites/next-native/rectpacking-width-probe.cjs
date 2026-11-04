// Original width approximation helpers only; no full packing/provider.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__rectWidth=function(s){
 $clinit_OptimizationGoal();const goals=[ASPECT_RATIO_DRIVEN,MAX_SCALE_DRIVEN,AREA_DRIVEN],importer=new JsonImporter,root=$transformNode_0(importer,new JSONObject_0({id:'width-object-root',children:s.nodes}),null),nodes=$getChildren(root),padding=new ElkPadding;
 padding.left=s.padding.left;padding.right=s.padding.right;padding.top_0=s.padding.top;padding.bottom=s.padding.bottom;
 const approximation=new AreaApproximation(s.aspectRatio,goals[s.goal],s.lastPlaceShift),drawing=$approxBoundingBox(approximation,nodes,s.spacing,padding),positions=[];
 for(let i=nodes.iterator_0();i.hasNext_0();){const n=i.next_1();positions.push([n.x_0,n.y_0,n.width_0,n.height]);}
 return {positions,drawing:{width:drawing.drawingWidth,height:drawing.drawingHeight,scale:drawing.scaleMeasure,next:[drawing.nextXcoordinate,drawing.nextYcoordinate],descriptor:drawing.placementOption.name_0},layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__rectWidth(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-rectpacking-width-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
