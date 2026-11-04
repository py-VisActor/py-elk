// One pinned reference API request per independent process. No native candidate.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const digest=x=>crypto.createHash('sha256').update(x).digest('hex');
const clone=x=>JSON.parse(JSON.stringify(x));
const error=e=>({name:String(e.name||'Error'),message:String(e.message||e),ownNames:Object.getOwnPropertyNames(e),stack:String(e.stack||e)});
async function main(){
 const [packagePath,requestPath,outPath]=process.argv.slice(2);
 const pkg=path.resolve(packagePath),raw=fs.readFileSync(requestPath),request=JSON.parse(raw);
 if(request.schema!=='py-elk-e08-api-request/v1'||typeof request.id!=='string')throw Error('Invalid API request');
 const lock=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../UPSTREAM.json'),'utf8'));
 for(const [file,sha] of Object.entries(lock.distribution.sha256Files))if(digest(fs.readFileSync(path.join(pkg,file)))!==sha)throw Error('Locked package changed '+file);
 const entry=request.entrypoint||'lib/elk.bundled.js';
 const ELK=require(path.join(pkg,entry));
 const observation={schema:'py-elk-e08-api-observation/v1',id:request.id,requestSha256:digest(raw),engine:{name:'elkjs',version:lock.javascript.version,node:process.version,platform:process.platform,arch:process.arch,entrypoint:entry,entrypointSha256:digest(fs.readFileSync(path.join(pkg,entry)))},events:[]};
 fs.writeFileSync(outPath+'.identity.json',JSON.stringify({schema:observation.schema,id:observation.id,requestSha256:observation.requestSha256,engine:observation.engine})+'\n',{flag:'wx'});
 const eventsPath=outPath+'.events.jsonl';fs.writeFileSync(eventsPath,'',{flag:'wx'});
 const emit=e=>{observation.events.push(e);fs.appendFileSync(eventsPath,JSON.stringify(e)+'\n');process.stdout.write(JSON.stringify({event:e.kind,id:e.id,operation:e.operation,outcome:e.outcome,count:Array.isArray(e.result)?e.result.length:undefined})+'\n');};
 const instances={};
 for(const step of request.steps){
  if(step.operation==='construct'){
   const options=step.hasOwnProperty('constructor')?clone(step.constructor):undefined;
   try{instances[step.id]=step.hasOwnProperty('constructor')?new ELK(options):new ELK();emit({kind:'constructor',id:step.id,outcome:'returned',optionsAfter:options,initialized:instances[step.id].initialized});}
   catch(e){emit({kind:'constructor',id:step.id,outcome:'threw',error:error(e),optionsAfter:options});}
  }else{
   const elk=instances[step.id];
   if(!elk){emit({kind:'call',id:step.id,operation:step.operation,outcome:'instanceNotConstructed'});continue;}
   const graph=step.hasOwnProperty('graph')?clone(step.graph):undefined,args=step.hasOwnProperty('arguments')?clone(step.arguments):undefined;
   let returnKind;
   try{
    let returned;
    if(step.operation==='layout')returned=step.hasOwnProperty('arguments')?elk.layout(graph,args):elk.layout(graph);
    else if(step.operation==='mutate-query'){
      const first=await elk[step.method]();const before=clone(first);
      if(first.length)first[0].id='V_MUTATION';first.push({id:'V_INJECTED'});
      if(step.nested&&first.length>1){for(const name of ['knownOptions','knownLayouters','targets'])if(Array.isArray(first[0][name]))first[0][name].push('V_NESTED_INJECTED');}
      const second=await elk[step.method]();
      emit({kind:'call',id:step.id,operation:step.operation,method:step.method,outcome:'returned',before,result:second,sameArray:first===second,mutatedFirstArray:clone(first)});continue;
    }else returned=elk[step.operation]();
    returnKind=returned instanceof Promise?'Promise':typeof returned;
    const result=await returned;
    emit({kind:'call',id:step.id,operation:step.operation,outcome:'returned',returnKind,result,graphAfter:graph,argumentsAfter:args,initialized:elk.initialized});
   }catch(e){emit({kind:'call',id:step.id,operation:step.operation,outcome:'threw',returnKind:returnKind||'synchronous_throw',error:error(e),graphAfter:graph,argumentsAfter:args,initialized:elk.initialized});}
  }
 }
 fs.writeFileSync(outPath,JSON.stringify(observation,null,2)+'\n',{flag:'wx'});
}
main().catch(e=>{process.stderr.write(String(e.stack||e)+'\n');process.exitCode=2;});
