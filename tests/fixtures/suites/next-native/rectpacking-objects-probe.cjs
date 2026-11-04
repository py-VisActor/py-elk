// Actual DrawingData, BlockRow and RectRow helpers; no packing layout.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__rectObjects=function(s){
 const n=v=>Number.isNaN(v)?'NaN':v===Infinity?'Infinity':v===-Infinity?'-Infinity':Object.is(v,-0)?'-0':v;
 const d=s.drawing;$clinit_DrawingDataDescriptor();const drawing=new DrawingData_0(d.aspectRatio,d.width,d.height,WHOLE_DRAWING,...d.next);
 const draw=()=>({width:drawing.drawingWidth,height:drawing.drawingHeight,scale:n(drawing.scaleMeasure),next:[drawing.nextXcoordinate,drawing.nextYcoordinate],descriptorSame:drawing.placementOption===WHOLE_DRAWING});
 const drawings=[draw()];d.actions.forEach(([key,value])=>{key==='width'?$setDrawingWidth(drawing,value):$setDrawingHeight(drawing,value);drawings.push(draw());});
 const importer=new JsonImporter,root=$transformNode_0(importer,new JSONObject_0({id:'object-root',children:s.nodes}),null),children=$getChildren(root),nodes=[];
 for(let i=children.iterator_0();i.hasNext_0();)nodes.push(i.next_1());
 const point=v=>[n(v.x_0),n(v.y_0)],node=v=>[v.x_0,v.y_0,v.width_0,v.height];
 const dimensions=point(calculateDimensions(children));resetCoordinates(children);const reset=nodes.map(node);
 const row=new BlockRow(s.row.x,s.row.y,s.row.spacing),list=row.rects;
 const snap=()=>({row:[row.x_0,row.y_0,row.width_0,row.height],nodes:nodes.map(node),sameList:row.rects===list,count:row.rects.array.length});
 const rows=[snap()];nodes.forEach(v=>{$addRectangle(row,v);rows.push(snap());});
 $setX_0(row,s.row.move[0]);$setY_0(row,s.row.move[1]);rows.push(snap());$updateRow(row);rows.push(snap());row.rects.clear_0();$updateRow(row);rows.push(snap());
 const aggregate=new RectRow(s.aggregate.y,s.aggregate.spacing),aggregateList=aggregate.children,agg=()=>[aggregate.width_0,n(aggregate.height)];
 const aggregates=[agg()];$notifyAboutNodeChange(aggregate);aggregates.push(agg());const absent=new Block(0,0,aggregate,s.aggregate.spacing);absent.width_0=s.aggregate.absentWidth;absent.height=s.aggregate.absentHeight;$removeBlock(aggregate,absent);aggregates.push(agg());
 return {drawings,scales:d.scaleInputs.map(v=>n(computeScaleMeasure(...v))),dimensions,reset,rows,aggregates,aggregateListSame:aggregate.children===aggregateList,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__rectObjects(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-rectpacking-objects-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
