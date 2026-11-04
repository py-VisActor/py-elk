const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,out]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(worker),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__directionDefaults=function(){
 getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_Direction_0();$clinit_DirectionCongruency();$clinit_GraphTransformer$Mode();
 return [false,true].map(physicalNull=>{
  const g=new LGraph,n=new LNode(g),p=new LPort,events=[];$add_3(g.layerlessNodes,n);$setNode(p,n);n.type_0=EXTERNAL_PORT;
  $setProperty_0(g,DIRECTION,DOWN_1);$setProperty_0(g,DIRECTION_CONGRUENCY_0,READING_DIRECTION);
  if(physicalNull){n.propertyMap=new HashMap;$put_6(n.propertyMap,EXT_PORT_SIDE,null);}
  p.propertyMap=new HashMap;$put_6(p.propertyMap,PORT_INDEX,null);
  const before=[$hasProperty(n,EXT_PORT_SIDE),$hasProperty(p,PORT_INDEX)];
  $process_12(new GraphTransformer(TO_INTERNAL_LTR),g,{begin:(name,work)=>events.push(['begin',name,work]),done_1:()=>events.push(['done'])});
  return {physicalNull,before,after:[$hasProperty(n,EXT_PORT_SIDE),$hasProperty(p,PORT_INDEX)],side:$getProperty(n,EXT_PORT_SIDE).name_0,indexNullish:$getProperty(p,PORT_INDEX)==null,events};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(out,JSON.stringify({workerSha256:sha(raw),requestSha256:sha(fs.readFileSync(requestPath)),probeSha256:sha(fs.readFileSync(__filename)),value:global.__directionDefaults(),layoutExecuted:false,pid:process.pid},null,2)+'\n',{flag:'wx'});
