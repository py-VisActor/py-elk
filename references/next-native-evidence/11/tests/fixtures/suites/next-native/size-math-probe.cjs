// Source arithmetic over explicit, real Cell/PortContext objects. This is not
// a replacement for the full node-size process or label-placement pipeline.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__sizeMathProbe=function(s){
 const parse=(id,value)=>$parseValue($getOptionDataBySuffix(getInstance(),id),value);
 $clinit_CoreOptions();$clinit_PortSide();$clinit_PortConstraints();$clinit_ContainerArea();$clinit_PortPlacementCalculator();
 const sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2};
 const g=new LGraph,node=new LNode(g);[node.size_0.x_0,node.size_0.y_0]=s.nodeSize||[100,60];
 $setProperty(node,NODE_SIZE_MINIMUM_5,parse('nodeSize.minimum',s.minimum||'(0,0)'));
 $setProperty(g,NODE_SIZE_FIXED_GRAPH_SIZE_3,s.fixedGraph===true);
 if(s.alignment!==undefined)$setProperty(node,PORT_ALIGNMENT_DEFAULT,parse('portAlignment.default',s.alignment));
 const ctx=new NodeContext(new LGraphAdapters$LNodeAdapter(new LGraphAdapters$LGraphAdapter(g),node,false));
 ctx.portConstraints=parse('portConstraints',s.constraints);
 ctx.sizeConstraints=parse('nodeSize.constraints','['+(s.sizeConstraints||[]).join(',')+']');
 ctx.sizeOptions=parse('nodeSize.options','['+(s.options||[]).join(',')+']');
 ctx.portLabelsPlacement=parse('portLabels.placement','['+(s.labelPlacement||[]).join(',')+']');
 ctx.portLabelsTreatAsGroup=s.treatAsGroup!==false;
 ctx.portPortSpacing=s.spacing===undefined?10:s.spacing;
 const margins=s.surrounding||[0,0,0,0];[ctx.surroundingPortMargins.top_0,ctx.surroundingPortMargins.right,ctx.surroundingPortMargins.bottom,ctx.surroundingPortMargins.left]=margins;
 ctx.nodeContainer.padding.top_0=3;ctx.nodeContainer.padding.right=4;ctx.nodeContainer.padding.bottom=5;ctx.nodeContainer.padding.left=6;
 // These real source cells are explicit predecessor inputs, not inferred
 // label measurements or claimed output of a full cell-creation process.
 ctx.insideNodeLabelContainer=new GridContainerCell(false,false,0);
 $setCell_0(ctx.nodeContainerMiddleRow,CENTER,ctx.insideNodeLabelContainer);
 const ps=[];
 for(const [index,item]of(s.ports||[]).entries()){
  const p=new LPort;p.side=sides[item.side];p.id_0=index;[p.size_0.x_0,p.size_0.y_0]=item.size||[4,4];[p.pos.x_0,p.pos.y_0]=item.pos||[0,0];
  if(item.ratio!==undefined)$setProperty(p,PORT_RATIO_OR_POSITION,item.ratio);
  const pc=new PortContext(ctx,new LGraphAdapters$LPortAdapter(p,false));pc.labelsNextToPort=item.next!==false;
  if(item.labels){pc.portLabelCell=new LabelCell_1(2,true);for(const size of item.labels){const l=new LLabel;[l.size_0.x_0,l.size_0.y_0]=size;$addLabel(pc.portLabelCell,new LGraphAdapters$LLabelAdapter(l));}}
  $put(ctx.portContexts,p.side,pc);ps.push({p,pc,id:item.id});
 }
 for(const[name,side]of Object.entries(sides)){
  const c=new AtomicCell;c.contributesToMinimumWidth=false;c.contributesToMinimumHeight=false;
  const spec=(s.cells||{})[name]||{};[c.minimumContentAreaSize.x_0,c.minimumContentAreaSize.y_0]=spec.minimum||[7,9];
  const pad=spec.padding||[1,2,3,4];[c.padding.top_0,c.padding.right,c.padding.bottom,c.padding.left]=pad;
  $put_7(ctx.insidePortLabelCells,side,c);
  if(name==='NORTH'||name==='SOUTH')$setCell_0(ctx.nodeContainer,name==='NORTH'?BEGIN:END,c);
  else $setCell_0(ctx.nodeContainerMiddleRow,name==='WEST'?BEGIN:END,c);
 }
 calculateHorizontalPortPlacementSize(ctx);calculateVerticalPortPlacementSize(ctx);
 configureCellSystemSizeContributions(ctx);
 const v=getMinimumNodeOrClientAreaSize(ctx);
 setNodeWidth(ctx);updateVerticalInsidePortLabelCellPadding(ctx);setNodeHeight(ctx);
 const snapshot=c=>({minimum:[c.getMinimumWidth(),c.getMinimumHeight()],content:[c.minimumContentAreaSize.x_0,c.minimumContentAreaSize.y_0],padding:[c.padding.top_0,c.padding.right,c.padding.bottom,c.padding.left],contributes:[c.contributesToMinimumWidth,c.contributesToMinimumHeight]});
 return {minimumNode:[v.x_0,v.y_0],nodeSize:[ctx.nodeSize.x_0,ctx.nodeSize.y_0],nodeRectangle:[ctx.nodeContainer.cellRectangle.width_0,ctx.nodeContainer.cellRectangle.height],cells:Object.fromEntries(Object.entries(sides).map(([n,v])=>[n,snapshot($get_14(ctx.insidePortLabelCells,v))])),middleContributes:[ctx.nodeContainerMiddleRow.contributesToMinimumWidth,ctx.nodeContainerMiddleRow.contributesToMinimumHeight],insideOnlyCenter:ctx.insideNodeLabelContainer.onlyCenterCellContributesToMinimumSize,ports:ps.map(({id,pc})=>({id,margin:[pc.portMargin.top_0,pc.portMargin.right,pc.portMargin.bottom,pc.portMargin.left]}))};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__sizeMathProbe(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-size-math-observation/v1',mode:'unchanged-worker-math-with-explicit-predecessor-cells',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
