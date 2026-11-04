const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__lockingOrderControl=function(){
 $clinit_Direction_0();
 const graph=new CGraph_0(allOf(Lorg_eclipse_elk_core_options_Direction_2_classLit)),owner=new ComponentsToCGraphTransformer(1),node=new ComponentsToCGraphTransformer$CRectNode(owner,new ElkRectangle_0(0,0,1,1));
 $add_3(graph.cNodes,node);const compactor=new OneDimensionalCompactor_0(graph);let calls=0;
 $setLockingStrategy(compactor,{apply_0:pair=>{calls++;if(calls===2)pair.first.cGroup.reposition=false;return true;}});
 $applyLockingStrategy(compactor);
 return {calls,nodeReposition:node.reposition,groupReposition:node.cGroup.reposition,groupValueType:typeof node.cGroup.reposition};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,node:process.version,value:global.__lockingOrderControl(),controlledCallbackSideEffect:true,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
