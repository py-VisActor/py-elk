// Instrumented collection primitive only: explicit enum hash collisions.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__enumKeyMap=function(){
 $clinit_PortSide();const sides={UNDEFINED:UNDEFINED_5,NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2};
 const saved=Object.values(sides).map(e=>({e,own:Object.prototype.hasOwnProperty.call(e,'$H'),value:e.$H}));
 const list=c=>{const a=[],it=c.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const set=names=>{const all=$getEnumConstants(Lorg_eclipse_elk_core_options_PortSide_2_classLit),s=new EnumSet$EnumSetImpl(all,createFrom(all,all.length),0);names.forEach(n=>s.add_2(sides[n]));return s;};
 const snapshot=(map,setKeys)=>list(map.entrySet_0()).map(e=>({key:e.getKey()===null?null:setKeys?list(e.getKey()).map(v=>v.name_0):e.getKey().name_0,value:e.getValue()}));
 try{
  Object.entries({UNDEFINED:7,NORTH:11,EAST:11,SOUTH:22,WEST:13}).forEach(([k,v])=>sides[k].$H=v);
  const map=new HashMap,a=set(['NORTH','EAST']),b=set(['SOUTH']),c=set(['WEST']),events=[];
  function event(name,value){events.push({name,value,items:snapshot(map,true)});}
  event('missing',$get_10(map,a));event('put-a',$put_6(map,a,'a'));event('put-b',$put_6(map,b,'b'));event('put-c',$put_6(map,c,'c'));
  event('replace-equal-key',$put_6(map,set(['NORTH','EAST']),'A'));
  const storedKeySame=list(map.entrySet_0())[0].getKey()===a;
  event('put-null-key',$put_6(map,null,'null-key'));
  a.add_2(WEST_2);event('get-mutated-key',$get_10(map,a));event('get-old-membership',$get_10(map,set(['NORTH','EAST'])));
  event('remove-b',$remove_6(map,b));event('reinsert-b',$put_6(map,b,'B'));event('remove-c',$remove_6(map,c));event('reinsert-c',$put_6(map,c,'C'));
  const scalar=new HashMap;$put_6(scalar,NORTH_3,1);$put_6(scalar,WEST_2,2);$put_6(scalar,EAST_2,3);
  const scalarItems=snapshot(scalar,false);
  sides.NORTH.$H=2147483647;sides.EAST.$H=3;sides.SOUTH.$H=-2147483646;
  const overflow=new HashMap;$put_6(overflow,set(['NORTH','EAST']),'sum');$put_6(overflow,set(['WEST']),'middle');$put_6(overflow,set(['SOUTH']),'collision');
  return {events,storedKeySame,scalarItems,overflowItems:snapshot(overflow,true)};
 }finally{saved.forEach(s=>{if(s.own)s.e.$H=s.value;else delete s.e.$H;});}
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,parentPid:process.ppid,node:process.version,value:global.__enumKeyMap(),instrumentedEnumHashControl:true,ordinaryLayoutOracle:false,layoutExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
