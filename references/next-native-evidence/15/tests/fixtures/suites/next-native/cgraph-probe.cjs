const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__cgraphControl=function(request){
 $clinit_Direction_0();
 const dirs={UNDEFINED:UNDEFINED_2,LEFT:LEFT_6,RIGHT:RIGHT_6,UP:UP_1,DOWN:DOWN_1};
 const array=x=>{const a=[],i=x.iterator_0();while(i.hasNext_0())a.push(i.next_1());return a;};
 const number=x=>Number.isFinite(x)?(Object.is(x,-0)?{number:'-0'}:x):{number:String(x)};
 const result=[];
 for(const input of request.cases){
  const graph=new CGraph_0(allOf(Lorg_eclipse_elk_core_options_Direction_2_classLit)),owner=new ComponentsToCGraphTransformer(input.spacing);
  const nodes=input.rectangles.map((v,i)=>{const n=new ComponentsToCGraphTransformer$CRectNode_0(owner,new ElkRectangle_0(...v),input.individualSpacing[i]);$add_3(graph.cNodes,n);return n;});
  for(const indices of input.groups)$add_3(graph.cGroups,new CGroup_0(indices.map(i=>nodes[i])));
  const compactor=new OneDimensionalCompactor_0(graph),calls=[],observations=[];
  if(input.componentSpacing)$setSpacingsHandler_0(compactor,SPACING_HANDLER);
  if(input.locking.length)$setLockingStrategy(compactor,{apply_0:pair=>{calls.push([nodes.indexOf(pair.first),pair.second.name_0]);return input.locking[(calls.length-1)%input.locking.length];}});
  const snap=label=>({label,direction:compactor.direction.name_0,finished:compactor.finished,
   nodes:nodes.map(n=>({id:n.id_0,box:[n.hitbox.x_0,n.hitbox.y_0,n.hitbox.width_0,n.hitbox.height].map(number),offset:[n.cGroupOffset.x_0,n.cGroupOffset.y_0].map(number),constraints:n.constraints.array.map(v=>nodes.indexOf(v)),reposition:n.reposition,start:number(n.startPos),group:graph.cGroups.array.indexOf(n.cGroup)})),
   groups:graph.cGroups.array.map(g=>({nodes:array(g.cNodes.map_0.keySet_0()).map(n=>nodes.indexOf(n)),reference:g.reference==null?null:nodes.indexOf(g.reference),incoming:array(g.incomingConstraints.map_0.keySet_0()).map(n=>nodes.indexOf(n)),outDegree:g.outDegree,delta:number(g.delta),normalized:number(g.deltaNormalized),start:number(g.startPos),reposition:g.reposition,repositionType:typeof g.reposition}))});
  observations.push(snap('constructed'));
  for(const direction of input.directions){
   $changeDirection_0(compactor,dirs[direction]);observations.push(snap('changed-'+direction));
   $applyLockingStrategy(compactor);observations.push(snap('locked-'+direction));
   $compact_3(compactor);observations.push(snap('compacted-'+direction));
  }
  $finish(compactor);observations.push(snap('finished'));
  result.push({name:input.name,calls,observations,usesSharedCalculator:compactor.constraintAlgorithm===SCANLINE_CONSTRAINTS_0});
 }
 return result;
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(fs.readFileSync(requestPath)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__cgraphControl(request),actualCGraphEngine:true,controlledLockingCallback:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
