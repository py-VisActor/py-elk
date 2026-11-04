// Object adapter only: all cell arithmetic executes the unchanged fixed worker.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg);
const workerPath=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__cellsProbe=function(spec){
 $clinit_ContainerArea();$clinit_HorizontalLabelAlignment();$clinit_VerticalLabelAlignment();
 const areas=[BEGIN,CENTER,END],ha=[LEFT,CENTER_0,RIGHT],va=[TOP,CENTER_1,BOTTOM];
 function build(s){
  let c;if(s.kind==='atomic')c=new AtomicCell;else if(s.kind==='grid')c=new GridContainerCell(!!s.tabular,!!s.symmetrical,s.gap||0);else if(s.kind==='strip')c=new StripContainerCell(s.mode||0,!!s.symmetrical,s.gap||0);else c=new LabelCell_1(s.gap||0,s.horizontalMode!==false);
  const p=s.padding||[0,0,0,0];[c.padding.top_0,c.padding.right,c.padding.bottom,c.padding.left]=p;
  c.contributesToMinimumWidth=s.contributes!==false;c.contributesToMinimumHeight=s.contributes!==false;
  if(s.minimum)[c.minimumContentAreaSize.x_0,c.minimumContentAreaSize.y_0]=s.minimum;
  if(s.rect)[c.cellRectangle.x_0,c.cellRectangle.y_0,c.cellRectangle.width_0,c.cellRectangle.height]=s.rect;
  if(s.kind==='grid'){
   c.onlyCenterCellContributesToMinimumSize=!!s.onlyCenter;
   if(s.centerMinimum){const v=new KVector;[v.x_0,v.y_0]=s.centerMinimum;$setCenterCellMinimumSize(c,v);}
   for(const entry of s.children||[])$setCell(c,areas[entry.row],areas[entry.col],build(entry.cell));
  }else if(s.kind==='strip'){for(const entry of s.children||[])$setCell_0(c,areas[entry.area],build(entry.cell));}
  else if(s.kind==='label'){
   if(s.horizontalAlignment!==undefined)$setHorizontalAlignment(c,ha[s.horizontalAlignment]);
   if(s.verticalAlignment!==undefined)$setVerticalAlignment(c,va[s.verticalAlignment]);
   for(const size of s.labels||[]){const label=new LLabel;[label.size_0.x_0,label.size_0.y_0]=size;$addLabel(c,new LGraphAdapters$LLabelAdapter(label));}
  }
  return c;
 }
 const rect=r=>[r.x_0,r.y_0,r.width_0,r.height];
 function snapshot(c,s){
  const o={minimum:[c.getMinimumWidth(),c.getMinimumHeight()],helperMinimum:[minWidthOfCell(c,false),minHeightOfCell(c,false)],respectedMinimum:[minWidthOfCell(c,true),minHeightOfCell(c,true)],rect:rect(c.cellRectangle)};
  if(s.kind==='grid'){o.centerRect=rect(c.centerCellRect);o.children=(s.children||[]).map(e=>snapshot($getCell(c,areas[e.row],areas[e.col]),e.cell));}
  if(s.kind==='strip')o.children=(s.children||[]).map(e=>snapshot(c.cells_0[e.area],e.cell));
  if(s.kind==='label')o.labels=c.labels.array.map(a=>{const l=a.element;return [l.pos.x_0,l.pos.y_0,l.size_0.x_0,l.size_0.y_0];});
  return o;
 }
 const c=build(spec);if(spec.kind==='grid'||spec.kind==='strip'){c.layoutChildrenHorizontally();c.layoutChildrenVertically();}else if(spec.kind==='label')$applyLabelLayout(c);
 return snapshot(c,spec);
};
`;
const compiled=new Module(workerPath,module);compiled.filename=workerPath;compiled.paths=Module._nodeModulePaths(pkg);compiled._compile(raw.toString()+bridge,workerPath);
const request=JSON.parse(requestRaw),results=request.cases.map(c=>({id:c.id,value:global.__cellsProbe(c.cell)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-cell-observation/v1',mode:'unchanged-worker-object-adapter',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false},null,2)+'\n',{flag:'wx'});
