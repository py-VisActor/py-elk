// Fixed-worker primitive calls with caller-supplied cell rectangles and margins.
// Node-size/cell preparation and full layout are deliberately not performed.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__placementProbe=function(s){
 $clinit_CoreOptions();$clinit_PortSide();$clinit_PortAlignment();$clinit_PortConstraints();$clinit_PortPlacementCalculator();
 const sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2};
 const aligns={BEGIN:BEGIN_0,CENTER:CENTER_6,END:END_1,DISTRIBUTED,JUSTIFIED};
 const constraints={FIXED_POS,FIXED_RATIO,FIXED_SIDE};
 const node=new LNode(new LGraph);[node.size_0.x_0,node.size_0.y_0]=s.nodeSize||[100,60];
 if(s.alignment!==undefined)$setProperty(node,PORT_ALIGNMENT_DEFAULT,aligns[s.alignment]);
 for(const [name,value]of Object.entries(s.alignments||{}))$setProperty(node,{NORTH:PORT_ALIGNMENT_NORTH_0,EAST:PORT_ALIGNMENT_EAST_0,SOUTH:PORT_ALIGNMENT_SOUTH_0,WEST:PORT_ALIGNMENT_WEST_0}[name],aligns[value]);
 const context=new NodeContext(new LGraphAdapters$LNodeAdapter(null,node,false));context.portConstraints=constraints[s.constraints];context.portPortSpacing=s.spacing===undefined?10:s.spacing;
 context.sizeOptions={contains(v){return(s.options||[]).includes(v.name_0);}};
 const ps=[];
 for(const [index,item]of s.ports.entries()){
  const p=new LPort;p.side=sides[item.side];[p.pos.x_0,p.pos.y_0]=item.pos||[0,0];[p.size_0.x_0,p.size_0.y_0]=item.size||[4,4];
  if(item.ratio!==undefined)$setProperty(p,PORT_RATIO_OR_POSITION,item.ratio);
  if(item.offset!==undefined)$setProperty(p,PORT_BORDER_OFFSET_0,item.offset);
  p.id_0=index;const pc=new PortContext(context,new LGraphAdapters$LPortAdapter(p,false));
  const m=item.margin||[0,0,0,0];[pc.portMargin.top_0,pc.portMargin.right,pc.portMargin.bottom,pc.portMargin.left]=m;
  $put(context.portContexts,p.side,pc);ps.push({id:item.id,p,pc});
 }
 for(const [name,spec]of Object.entries(s.cells||{})){
  const c=new AtomicCell;[c.cellRectangle.x_0,c.cellRectangle.y_0,c.cellRectangle.width_0,c.cellRectangle.height]=spec.rect;
  [c.minimumContentAreaSize.x_0,c.minimumContentAreaSize.y_0]=spec.minimum;
  const p=spec.padding||[0,0,0,0];[c.padding.top_0,c.padding.right,c.padding.bottom,c.padding.left]=p;$put_7(context.insidePortLabelCells,sides[name],c);
 }
 const before=ps.map(({p})=>[p.pos.x_0,p.pos.y_0]);
 placeHorizontalPorts(context);offsetSouthernPortsByNodeSize(context);placeVerticalPorts(context);
 const staged=ps.map(({p})=>[p.pos.x_0,p.pos.y_0]);
 ps.forEach(({pc})=>$applyPortPosition(pc));
 return {effectiveAlignments:Object.fromEntries(Object.entries(sides).map(([n,v])=>[n,$getPortAlignment(context,v).name_0])),before,staged,ports:ps.map(({id,p})=>({id,pos:[p.pos.x_0,p.pos.y_0]}))};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(c=>({id:c.id,value:global.__placementProbe(c)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-port-placement-observation/v1',mode:'unchanged-worker-primitive-with-supplied-cells',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
