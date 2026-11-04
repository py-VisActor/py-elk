// Actual JSON import and optsToCfg/NO_OVERWRITE property presence. No layout.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
$registerLayoutMetaDataProviders(getInstance(),[new ForceMetaDataProvider,new StressMetaDataProvider]);$clinit_ElkJs();
global.__presence=function(s){
 const importer=new JsonImporter,json=new JSONObject_0(JSON.parse(JSON.stringify(s.graph))),root=$transformNode_0(importer,json,null);$transformEdges_2(importer,json);
 if(s.globalOptions){const lc=optsToCfg(new JSONObject_0(s.globalOptions));applyVisitors(root,[lc]);}
 const edge=$getChildren(root).get_0(0).getOutgoingEdges_0().get_0(0),child=$getChildren(root).get_0(0),port=$getPorts_3(child).get_0(0),label=child.getLabels_0().get_0(0);
 const has=(o,k)=>$hasProperty_0(o,k),get=(o,k)=>$getProperty_0(o,k);
 const before=has(edge,DESIRED_EDGE_LENGTH),value=get(edge,DESIRED_EDGE_LENGTH),after=has(edge,DESIRED_EDGE_LENGTH);
 return {rootDesiredHas:has(root,DESIRED_EDGE_LENGTH),rootDesired:get(root,DESIRED_EDGE_LENGTH),edgeDesiredHasBefore:before,edgeDesired:value,edgeDesiredHasAfter:after,
  rootFixedHas:has(root,FIXED),rootFixed:get(root,FIXED),childFixedHas:has(child,FIXED),childFixed:get(child,FIXED),edgeFixedHas:has(edge,FIXED),portFixedHas:has(port,FIXED),labelFixedHas:has(label,FIXED),
  rootRepulsiveHas:has(root,REPULSIVE_POWER),edgeRepulsiveHas:has(edge,REPULSIVE_POWER),edgeRepulsive:get(edge,REPULSIVE_POWER)};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__presence(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-property-presence-observation/v1',mode:'original-import-and-selected-global-visitor-no-layout',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
