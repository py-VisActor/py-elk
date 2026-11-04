const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),request=JSON.parse(fs.readFileSync(requestPath));
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__splineRanking=function(request){
 $clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_PortSide();$clinit_SplineEdgeRouter$SideToProcess();const results=[];
 for(const input of request.cases){
  const graph=new LGraph,segments=new ArrayList;
  for(const [i,left]of input.left.entries()){const a=new LNode(graph),b=new LNode(graph),p=new LPort,q=new LPort;$setNode(p,a);$setNode(q,b);$setSide(p,EAST_2);$setSide(q,WEST_2);p.pos.y_0=i*10;q.pos.y_0=i*10+5;const e=new LEdge;$setSource_0(e,p);$setTarget_0(e,q);$add_3(segments,new SplineSegment(e,left?LEFT_4:RIGHT_4,RIGHT_4));}
  const dependencies=input.dependencies.map(p=>new SplineEdgeRouter$Dependency(segments.array[p[0]],segments.array[p[1]],p[2])),random=new Random_0(input.seed),before=[random.seedhi,random.seedlo],bounds=[],realNext=$nextInt;
  $nextInt=function(r,b){if(r===random)bounds.push(b);return realNext(r,b);};try{breakCycles(segments,random);}finally{$nextInt=realNext;}
  const afterCycle=segments.array.map(s=>({mark:s.mark,inWeight:s.inweight,outWeight:s.outweight}));topologicalNumbering_0(segments);
  results.push({name:input.name,nextIntBounds:bounds,seedBefore:before,seedAfter:[random.seedhi,random.seedlo],afterCycle,segments:segments.array.map(s=>({mark:s.mark,rank:s.rank,inWeight:s.inweight,outWeight:s.outweight,out:s.outgoing.array.map(d=>dependencies.indexOf(d)),in:s.incoming.array.map(d=>dependencies.indexOf(d))})),dependencies:dependencies.map(d=>({source:segments.array.indexOf(d.source),target:segments.array.indexOf(d.target),weight:d.weight,active:d.source.outgoing.array.includes(d)&&d.target.incoming.array.includes(d)}))});
 }
 return results;
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(fs.readFileSync(requestPath)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__splineRanking(request),actualBreakCyclesAndNumbering:true,observerOnlyNextInt:true,layoutExecuted:false,nativeExecuted:false},null,2)+'\n',{flag:'wx'});
