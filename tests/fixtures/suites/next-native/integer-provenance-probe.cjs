// Actual local/global Integer allocations and shallow property copies; no layout.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestBytes=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__integerProvenance=function(request){
 registerLayoutAlgorithms(['layered']);const ji=new JsonImporter,json=new JSONObject_0(JSON.parse(JSON.stringify(request.graph))),root=$transformNode_0(ji,json,null);$transformEdges_2(ji,json);
 applyVisitors(root,[optsToCfg(new JSONObject_0(request.globalOptions))]);
 const children=$getChildren(root),a=children.get_0(0),b=children.get_0(1),c=children.get_0(2),d=children.get_0(3),e=children.get_0(4);
 const priority=$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.priority'),get=n=>$getProperty_0(n,priority),port=$getPorts_3(a).get_0(0);
 const group=CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CROSSING_MINIMIZATION_ID;
 const result={localLargeDistinct:get(a)!==get(b),localSmallShared:get(c)===get(d),
  globalShared:get(root)===get(e),localOverridesGlobal:get(a)!==get(root),
  portGlobalAbsent:!$hasProperty_0(port,priority),numericPayloads:[get(a).value_0,get(c).value_0,get(e).value_0],
  defaultZeroShared:$getProperty_0(a,group)===valueOf_3(0),defaultAbsent:!$hasProperty_0(a,group)};
 $copyProperties_0(b,a);result.copyTokenShared=get(b)===get(a);
 $setProperty_1(a,priority,new Integer(0));result.directNewDistinct=get(a)!==valueOf_3(0);result.copyIndependent=get(b).value_0===129;
 $setProperty_1(a,priority,null);result.removedAbsent=!$hasProperty_0(a,priority);return result;
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const observation=global.__integerProvenance(JSON.parse(requestBytes));
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestBytes),
 pid:process.pid,parentPid:process.ppid,observation,layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
