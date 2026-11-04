// Observe binary64 JSON numbers through actual original shape import helpers.
// No algorithm, EMF runtime port, input-size guard or layout is implemented.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__numericImport=function(spec){
 const input=JSON.parse('{'+['x','y','width','height'].map(k=>JSON.stringify(k)+':'+spec.literals[k]).join(',')+'}');
 const object=new JSONObject;
 for(const k of ['x','y','width','height'])$put_5(object,k,new JSONNumber(input[k]));
 $clinit_ElkGraphFactory();const node=new ElkNodeImpl;
 $transformShapeLayout(object,node);
 const imported={x:node.x_0,y:node.y_0,width:node.width_0,height:node.height};
 return {imported,negativeZero:Object.fromEntries(Object.entries(imported).map(([k,v])=>[k,Object.is(v,-0)])),
         widthPlusOne:node.width_0+1,xPlusOne:node.x_0+1};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const cases=JSON.parse(requestRaw).cases.map(s=>({id:s.id,result:global.__numericImport(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-numeric-import-observation/v1',workerSha256:sha(raw),
 probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,
 cases,candidateExecuted:false,layoutExecuted:false,scope:'Actual original optDouble/transformShapeLayout/setters, JSON binary64 literals and one subsequent addition'},null,2)+'\n',{flag:'wx'});
