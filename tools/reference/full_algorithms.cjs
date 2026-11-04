// Unified public API oracle: one actual Node process, immutable npm artifact.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const clone=v=>JSON.parse(JSON.stringify(v));
async function main(){
 const [pkg,suitePath,out]=process.argv.slice(2); if(!out)throw Error('PACKAGE SUITE NEW_OUT');
 fs.mkdirSync(out,{recursive:false});
 const root=path.resolve(__dirname,'../..'),lock=JSON.parse(fs.readFileSync(path.join(root,'UPSTREAM.json')));
 for(const [name,digest]of Object.entries(lock.distribution.sha256Files))if(sha(fs.readFileSync(path.join(pkg,name)))!==digest)throw Error('npm identity '+name);
 const ELK=require(path.resolve(pkg,'lib/elk.bundled.js')),suiteBytes=fs.readFileSync(suitePath),suite=JSON.parse(suiteBytes),rows=[];
 for(const c of suite.cases){
  const raw=fs.readFileSync(path.resolve(path.dirname(suitePath),c.request));if(sha(raw)!==c.requestSha256)throw Error('request SHA '+c.id);
  const req=JSON.parse(raw),constructor=clone(req.constructor),graph=clone(req.graph),args=clone(req.layoutArguments);
  let elk;const started=process.hrtime.bigint();let value={id:c.id,requestSha256:sha(raw),inputBefore:clone(graph)};
  try{elk=new ELK(constructor);value.result=await elk.layout(graph,args);value.outcome='returned';}
  catch(e){value.outcome='threw';value.error={name:String(e.name),message:String(e.message)};value.stack=String(e.stack);}
  value.elapsedSeconds=Number(process.hrtime.bigint()-started)/1e9;
  value.inputAfter=graph;value.constructorAfter=constructor;value.argumentsAfter=args;
  if(elk)try{value.termination={outcome:'returned',returnKind:typeof elk.terminateWorker()};}catch(e){value.termination={outcome:'threw',name:String(e.name),message:String(e.message)};}
  const bytes=Buffer.from(JSON.stringify(value,null,2)+'\n');fs.writeFileSync(path.join(out,c.id+'.json'),bytes,{flag:'wx'});rows.push({id:c.id,sha256:sha(bytes),outcome:value.outcome});
  process.stdout.write(JSON.stringify({id:c.id,outcome:value.outcome})+'\n');
 }
 fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({schema:'py-elk-full-algorithms-reference/v1',pid:process.pid,node:process.version,executable:process.execPath,nodeSha256:sha(fs.readFileSync(process.execPath)),suiteSha256:sha(suiteBytes),collectorSha256:sha(fs.readFileSync(__filename)),distribution:lock.distribution.sha256Files,rows},null,2)+'\n',{flag:'wx'});
}
main().catch(e=>{process.stderr.write(String(e.stack)+'\n');process.exitCode=2});
