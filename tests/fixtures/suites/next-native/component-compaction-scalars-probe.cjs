const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),req=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__componentScalars=function(request){
 getInstance();$clinit_InternalProperties_1();$clinit_PortSide();$clinit_Direction_0();
 const sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2},locks=[];
 for(let mask=0;mask<16;mask++){
  const names=Object.keys(sides).filter((_,i)=>mask&(1<<i)),all=$getEnumConstants(Lorg_eclipse_elk_core_options_PortSide_2_classLit),set=new EnumSet$EnumSetImpl(all,createFrom(all,all.length),0);
  for(const name of names)set.add_2(sides[name]);
  const node=new ComponentsToCGraphTransformer$CRectNode(new ComponentsToCGraphTransformer(5),new ElkRectangle_0(0,0,1,1)),lock=node.lock;
  $setLock(node,set);locks.push({sides:names,values:[LEFT_6,RIGHT_6,UP_1,DOWN_1].map(d=>$get_19(lock,d)),same:node.lock===lock});
 }
 const fieldHashCalls=[];
 const pairHashes=request.pairCodes.map(([a,b])=>{
  const first=new CGroup_0([]),second=new CGroup_0([]);
  first.hashCode_1=function(){fieldHashCalls.push(['first',a]);return a;};
  second.hashCode_1=function(){fieldHashCalls.push(['second',b]);return b;};
  return (new Pair(first,second)).hashCode_1();
 });
 if(fieldHashCalls.length!==2*request.pairCodes.length)throw Error('Actual Java virtual hash callbacks not reached');
 return {lockTable:locks,pairHashes,fieldHashCalls};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(req),pid:process.pid,parentPid:process.ppid,...global.__componentScalars(JSON.parse(req)),actualScalarHelpers:true,controlledFieldHashCallbacks:true,controllerExecutions:0,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
