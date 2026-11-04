// Original copyProperties of actual stored values; no layout or candidate.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(workerPath),requestBytes=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__propertySnapshot=function(request){
 registerLayoutAlgorithms(['layered']);const ji=new JsonImporter,json=new JSONObject_0(JSON.parse(JSON.stringify(request.graph))),root=$transformNode_0(ji,json,null);$transformEdges_2(ji,json);
 applyVisitors(root,[optsToCfg(new JSONObject_0(request.globalOptions))]);
 const a=$getChildren(root).get_0(0),b=$getChildren(root).get_0(1),get=(n,key)=>$getProperty_0(n,$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.'+key));
 const has=(n,key)=>$hasProperty_0(n,$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.'+key));
 const minimum=get(a,'nodeSize.minimum'),padding=get(a,'nodeLabels.padding'),constraints=get(a,'nodeSize.constraints');
 get(a,'direction');const scalarAbsentBefore=!has(a,'direction');
 const privateKey=new Property('private.scalar');$setProperty_1(a,privateKey,42);
 const algorithm=$getAlgorithmDataBySuffix(SERVICE,'box');$setProperty_1(a,RESOLVED_ALGORITHM,algorithm);
 $copyProperties_0(b,a);
 const value={minimumShared:get(b,'nodeSize.minimum')===minimum,paddingShared:get(b,'nodeLabels.padding')===padding,
  constraintsShared:get(b,'nodeSize.constraints')===constraints,algorithmShared:$getProperty_0(b,RESOLVED_ALGORITHM)===algorithm,
  scalarAbsentBefore,scalarAbsentAfter:!has(b,'direction'),privateValue:$getProperty_0(b,privateKey),
  individualShared:get(b,'spacing.individual')===get(a,'spacing.individual')};
 minimum.x_0=99;value.mutationVisible=get(b,'nodeSize.minimum').x_0===99;
 $setProperty_1(a,$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.priority'),valueOf_3(8));
 value.copiedKeyIndependent=get(b,'priority').value_0===7&&get(a,'priority').value_0===8;
 $setProperty_1(a,NODE_SIZE_MINIMUM_0,new KVector_1(1,2));
 value.replacementIndependent=get(b,'nodeSize.minimum')===minimum&&get(a,'nodeSize.minimum')!==minimum;
 return value;
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__propertySnapshot(JSON.parse(requestBytes));
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestBytes),
 pid:process.pid,parentPid:process.ppid,node:process.version,observation,layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
