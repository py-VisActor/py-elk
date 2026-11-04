// Original parser/property/clone objects only. No layout or candidate code.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(workerPath),requestBytes=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__objectProperties=function(request){
 registerLayoutAlgorithms(['layered','force','stress','mrtree','radial','disco','sporeOverlap','sporeCompaction','rectpacking']);
 const list=c=>{const values=[],it=c.iterator_0();while(it.hasNext_0())values.push(it.next_1());return values;};
 const point=p=>({x:p.x_0,y:p.y_0,negativeZeroX:Object.is(p.x_0,-0),negativeZeroY:Object.is(p.y_0,-0)});
 const parsed=request.parseCases.map(c=>{
  const option=$getOptionDataBySuffix(SERVICE,c.option),value=$parseValue(option,c.value);
  return {id:c.id,cloneable:instanceOf(value,4),points:('x_0'in value)?[point(value)]:list(value).map(point)};
 });
 const importer=new JsonImporter,json=new JSONObject_0(JSON.parse(JSON.stringify(request.graph))),root=$transformNode_0(importer,json,null);
 $transformEdges_2(importer,json);applyVisitors(root,[optsToCfg(new JSONObject_0(request.globalOptions))]);
 const a=$getChildren(root).get_0(0),b=$getChildren(root).get_0(1),e1=a.getOutgoingEdges_0().get_0(0),e2=b.getOutgoingEdges_0().get_0(0);
 const prop=$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.bendPoints');
 const one=$getProperty_0(e1,prop),two=$getProperty_0(e2,prop),first=list(one)[0],second=list(two)[0];
 const globalPresence=[$hasProperty_0(e1,prop),$hasProperty_0(e2,prop)];
 first.x_0=99;
 const j1=$getProperty_0(e1,JUNCTION_POINTS_0),j2=$getProperty_0(e2,JUNCTION_POINTS_0);
 return {parsed,clone:{globalChainsDistinct:one!==two,globalPointsShared:first===second,mutationVisible:second.x_0===99,
  globalPresence,junctionDefaultsDistinct:j1!==j2,junctionReadCached:$getProperty_0(e1,JUNCTION_POINTS_0)===j1,
  junctionPresenceAfterRead:[$hasProperty_0(e1,JUNCTION_POINTS_0),$hasProperty_0(e2,JUNCTION_POINTS_0)],junctionEmpty:list(j1).length===0&&list(j2).length===0}};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__objectProperties(JSON.parse(requestBytes));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-object-properties-original/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),
 requestSha256:sha(requestBytes),pid:process.pid,parentPid:process.ppid,node:process.version,observation,
 layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
