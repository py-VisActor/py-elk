// Development-only actual LayoutOptionData parser observation, without a layout.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestBytes=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__fullPropertyCatalogue=function(cases){
 registerLayoutAlgorithms(['layered','force','stress','mrtree','radial','disco','sporeOverlap','sporeCompaction','rectpacking']);
 const list=c=>{const values=[],it=c.iterator_0();while(it.hasNext_0())values.push(it.next_1());return values;};
 const number=n=>Number.isNaN(n)?{number:'NaN'}:n===Infinity?{number:'Infinity'}:n===-Infinity?{number:'-Infinity'}:Object.is(n,-0)?{number:'-0'}:n;
 const scalar=v=>v&&typeof v==='object'&&'value_0'in v?v.value_0:v;
 const point=v=>({x:number(v.x_0),y:number(v.y_0)});
 return cases.map(c=>{
  const option=$getOptionDataBySuffix(SERVICE,c.option);if(!option)throw Error('Missing metadata '+c.option);
  try {
   const parsed=$parseValue(option,c.text);let value;
   if(parsed==null)value=null;
   else if(c.kind==='enum_ordinal')value=parsed.name_0;
   else if(c.kind==='enumset')value=list(parsed).map(e=>e.name_0).sort();
   else if(c.kind==='vector')value=point(parsed);
   else if(c.kind==='vector_chain')value=list(parsed).map(point);
   else if(c.kind==='insets')value={top:number(parsed.top_0),right:number(parsed.right),bottom:number(parsed.bottom),left:number(parsed.left)};
   else if(c.kind==='individual_spacings')value={nodeNode:number(scalar($getProperty(parsed,$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.spacing.nodeNode'))))};
   else {value=scalar(parsed);if(typeof value==='number')value=number(value);}
   return {id:c.id,option:option.id_0,outcome:'returned',value};
  }catch(error){return {id:c.id,option:option.id_0,outcome:'threw',error:{name:error.name,message:error.message}};}
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const observation=global.__fullPropertyCatalogue(JSON.parse(requestBytes).cases);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestBytes),
 pid:process.pid,parentPid:process.ppid,node:process.version,observation,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
