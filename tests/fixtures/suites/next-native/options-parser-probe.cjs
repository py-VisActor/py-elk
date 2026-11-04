// Actual original LayoutOptionData parser and registered data factories only.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__optionParserProbe=function(s){
 const option=$getOptionDataBySuffix(getInstance(),s.option);if(!option)throw Error('Unknown original option');
 function number(v){return Number.isFinite(v)?v:{nonfinite:String(v)};}
 function view(v,o){
  if(v==null)return null;
  switch(o.type_0.ordinal){
   case 1:return v.value_0===undefined?v:v.value_0;
   case 2:return v.value_0;
   case 4:return number(v);
   case 5:return v.name_0;
   case 6:{const a=[],it=v.iterator_0();while(it.hasNext_0())a.push(it.next_1().name_0);return a;}
   case 7:{
    if('x_0'in v)return {x:number(v.x_0),y:number(v.y_0)};
    if('top_0'in v)return {top:number(v.top_0),right:number(v.right),bottom:number(v.bottom),left:number(v.left)};
    const result={};if(v.propertyMap){const it=v.propertyMap.entrySet_0().iterator_0();while(it.hasNext_0()){const e=it.next_1(),key=e.getKey();result[key.getId()]=view(e.getValue(),key);}}return result;
   }
  }
 }
 const parsed=$parseValue(option,s.value);return {type:option.type_0.name_0,value:view(parsed,option)};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const cases=JSON.parse(requestRaw).cases.map(s=>({id:s.id,option:s.option,input:s.value,result:global.__optionParserProbe(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-option-parser-observation/v1',mode:'original-parser-object-adapter',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,cases,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
