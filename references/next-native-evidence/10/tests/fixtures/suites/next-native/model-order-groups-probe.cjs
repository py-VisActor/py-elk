const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestBytes=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__modelOrderGroups=function(input){
 registerLayoutAlgorithms(['layered']);const ji=new JsonImporter,json=new JSONObject_0(input),root=$transformNode_0(ji,json,null);$transformEdges_2(ji,json);
 const graph=$createLGraph(root);$importFlatGraph(new ElkGraphImporter,root,graph);
 const a=$getChildren(root).get_0(0),b=$getChildren(root).get_0(1),group=$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.layered.considerModelOrder.groupModelOrder.cycleBreakingId');
 return {groups:$getProperty(graph,CB_NUM_MODEL_ORDER_GROUPS).value_0,maximum:$getProperty(graph,MAX_MODEL_ORDER_NODES).value_0,
  equalGroupDistinctBoxes:$getProperty_0(a,group)!==$getProperty_0(b,group),importedNodes:graph.layerlessNodes.array.length};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const observation=global.__modelOrderGroups(JSON.parse(requestBytes));fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestBytes),
 pid:process.pid,parentPid:process.ppid,observation,layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
