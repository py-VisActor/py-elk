// Actual original JSONNumber/JSONObject unwrapping and final JSON.stringify.
// This observes wire conversion only, without running or altering layout math.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__jsonWire=function(spec){
 const number={NaN,Infinity,'-Infinity':-Infinity}[spec.value],o=new JSONObject;
 $put_5(o,'coordinate',new JSONNumber(number));
 return {inputKind:spec.value,internalKind:String(o.jsObject.coordinate),internalStillNumber:typeof o.jsObject.coordinate==='number',internalFinite:Number.isFinite(o.jsObject.coordinate),wireText:JSON.stringify(o.jsObject),wireValue:JSON.parse(JSON.stringify(o.jsObject))};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const collector=path.resolve(__dirname,'../../../../tools/reference/capture_layout.cjs');
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__jsonWire(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-json-wire-observation/v1',mode:'original-JSONNumber-JSONObject-and-final-JSON-stringify',workerSha256:sha(raw),collectorSha256:sha(fs.readFileSync(collector)),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
