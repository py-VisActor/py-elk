// Development-only direct original property parser, not a layout.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outputPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestBytes=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__scalarParserObservation=function(cases){
 registerLayoutAlgorithms(['layered','force','stress','mrtree','radial','disco','sporeOverlap','sporeCompaction','rectpacking']);
 const rows=[];
 for(const c of cases){
  const o=$getOptionDataBySuffix(SERVICE,c.option);if(!o)throw Error('Missing original option '+c.option);
  const parsed=$parseValue(o,c.value),type=o.type_0.name_0;let value;
  if(parsed==null)value=null;
  else if(type==='ENUM')value={enum:parsed.name_0};
  else if(type==='ENUMSET'){
   const members=[],it=parsed.iterator_0();while(it.hasNext_0())members.push(it.next_1().name_0);value={members};
  }else if(typeof parsed==='object'&&'value_0'in parsed)value=parsed.value_0;
  else value=parsed;
  rows.push({id:c.id,option:o.id_0,type,value});
 }
 return rows;
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const request=JSON.parse(requestBytes),cases=global.__scalarParserObservation(request.cases);
fs.writeFileSync(outputPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestBytes),
 pid:process.pid,parentPid:process.ppid,node:process.version,cases,layoutExecuted:false,candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
