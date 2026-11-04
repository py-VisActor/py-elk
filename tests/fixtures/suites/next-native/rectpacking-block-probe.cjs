// Real Block/Stack math on original imported ElkNodes, no provider scheduler.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__rectBlock=function(s){
 const n=v=>Number.isNaN(v)?'NaN':v===Infinity?'Infinity':v===-Infinity?'-Infinity':Object.is(v,-0)?'-0':v;
 const importer=new JsonImporter,root=$transformNode_0(importer,new JSONObject_0({id:'block-root',children:s.rects}),null),nodes=[];
 for(let i=$getChildren(root).iterator_0();i.hasNext_0();)nodes.push(i.next_1());
 const parent=new RectRow(s.y,s.spacing),blocks=[],initialLists=[],names=new Map(nodes.map((p,i)=>[p,s.rects[i].id]));
 const make=(x,y)=>{const b=new Block(x,y,parent,s.spacing);blocks.push(b);initialLists.push([b.children,b.rows_0]);$addBlock_0(parent,b);return b;};
 const block=make(s.x,s.y);
 const rect=v=>[n(v.x_0),n(v.y_0),n(v.width_0),n(v.height)];
 const view=b=>({dimensions:[b.x_0,b.y_0,b.width_0,b.height].map(n),limits:[b.minWidth,b.minHeight,b.maxHeight,b.smallestRectWidth,b.smallestRectHeight,b.averageHeight].map(n),
  children:b.children.array.map(p=>names.get(p)),rows:b.rows_0.array.map(r=>({dimensions:rect(r),rects:r.rects.array.map(p=>names.get(p))})),sameChildren:b.children===initialLists[blocks.indexOf(b)][0],sameRows:b.rows_0===initialLists[blocks.indexOf(b)][1]});
 const snap=()=>({blocks:blocks.map(view),nodes:nodes.map(rect),parent:[n(parent.width_0),n(parent.height)]});
 const steps=[snap()],returned=[];
 if(s.operation==='stack'){
  nodes.slice(0,2).forEach(p=>$addChild(block,p));const other=make(s.x,s.y+11);nodes.slice(2).forEach(p=>$addChild(other,p));
  const stack=new BlockStack(s.x,s.y,s.spacing),list=stack.blocks;$addBlock(stack,block);$addBlock(stack,other);
  const ss=()=>({geometry:[stack.x_0,stack.y_0,stack.width_0,stack.height].map(n),sameList:stack.blocks===list,owned:blocks.map(b=>b.stack_0===stack),state:snap()});
  const stackSteps=[ss()];returned.push(n($getWidthForFixedHeight(stack,s.targetHeight)));stackSteps.push(ss());
  $placeRectsIn_2(stack,s.targetWidth);stackSteps.push(ss());$setLocation_0(stack,...s.move);stackSteps.push(ss());$expand_1(stack,...s.expand);stackSteps.push(ss());
  return {id:s.id,stackSteps,returned,layoutExecuted:false};
 }
 nodes.forEach(p=>{$addChild(block,p);steps.push(snap());});
 if(s.operation==='place'){
  const b=$placeRectsIn_1(block,s.targetWidth,false);returned.push(rect(b));steps.push(snap());returned.push(n($getWidthForTargetHeight(block,s.targetHeight)));steps.push(snap());
  const actual=$placeRectsIn_1(block,s.targetWidth,true);returned.push(rect(actual));steps.push(snap());
 }else{$removeChild(block,nodes[s.operation==='remove-middle'?1:0]);steps.push(snap());}
 return {id:s.id,steps,returned,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const spec=JSON.parse(requestRaw),results=spec.cases.map(s=>global.__rectBlock(s));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-rectpacking-block-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
