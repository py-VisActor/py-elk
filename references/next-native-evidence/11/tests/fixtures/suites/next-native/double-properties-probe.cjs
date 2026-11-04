// New original numeric-property import observations; no layout is performed.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__doubleProperties=function(spec){
 registerLayoutAlgorithms(['layered','force']);
 const option=$getOptionDataBySuffix(SERVICE,spec.option);
 const graph={id:'root',layoutOptions:{[spec.option]:JSON.parse(spec.literal)}};
 const node=$transformNode_0(new JsonImporter,new JSONObject_0(graph),null);
 const value=$getProperty_0(node,option);
 return {present:$hasProperty_0(node,option),value,negativeZero:Object.is(value,-0),plusOne:value+1};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,result:global.__doubleProperties(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-original-double-properties-observation/v1',workerSha256:sha(raw),
 probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,
 results,layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
