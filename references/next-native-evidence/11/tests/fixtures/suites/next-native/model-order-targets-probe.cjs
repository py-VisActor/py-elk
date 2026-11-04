// Exact original target/memo producer, including branch order and boxed minima.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__modelTargets=function(s){
 getInstance();$clinit_PortSide();$clinit_InternalProperties_1();$clinit_LNode$NodeType();
 const g=new LGraph,nodes={},ports={},names=new Map;
 for(const [id,type] of s.nodes){const n=nodes[id]=new LNode(g);names.set(n,id);$setType(n,type==='NORMAL'?NORMAL:LONG_EDGE);}
 for(const [id,owner] of s.ports){const p=ports[id]=new LPort;$setNode(p,nodes[owner]);$setSide(p,EAST_2);}
 function edge(a,b,order,reversed){const e=new LEdge;$setSource_0(e,ports[a]);$setTarget_0(e,ports[b]);if(order!==null)$setProperty_0(e,MODEL_ORDER_2,valueOf_3(order));if(reversed)$setProperty_0(e,REVERSED,true);return e;}
 s.edges.forEach(args=>edge(...args));$setProperty_0(nodes[s.explicitTarget[0]],LONG_EDGE_TARGET,ports[s.explicitTarget[1]]);
 s.oldPortTargets.forEach(([p,n])=>$setProperty_0(ports[p],LONG_EDGE_TARGET_NODE,nodes[n]));
 const map=longEdgeTargetNodePreprocessing(nodes[s.source]), boxes=s.targets.map(id=>$get_10(map,nodes[id]));
 const targetValues=boxes.map(b=>b.value_0),targetBoxesSame=boxes[0]===boxes[1],memoSame=map===longEdgeTargetNodePreprocessing(nodes[s.source]);
 const portTargets=s.queryPorts.map(id=>[id,$hasProperty(ports[id],LONG_EDGE_TARGET_NODE),$hasProperty(ports[id],LONG_EDGE_TARGET_NODE)?names.get($getProperty(ports[id],LONG_EDGE_TARGET_NODE)):null]);
 const empty=longEdgeTargetNodePreprocessing(nodes.cached);edge(...s.lateEdge,false);const again=longEdgeTargetNodePreprocessing(nodes.cached);
 return {targetValues,targetBoxesSame,memoSame,portTargets,lateMemoSame:empty===again,lateTargetAbsent:!$hasProperty(ports.cachep,LONG_EDGE_TARGET_NODE),lateMapEmpty:s.targets.every(id=>!$containsKey_3(again,nodes[id])),layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__modelTargets(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-model-targets-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
