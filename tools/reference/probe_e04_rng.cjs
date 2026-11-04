// Fixed generated-source Java RNG oracle, exposed in memory only for research.
// Usage: node tools/reference/probe_e04_rng.cjs PACKAGE NEW_OUTPUT_JSON
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const ROOT=path.resolve(__dirname,'../..');
const lock=JSON.parse(fs.readFileSync(path.join(ROOT,'UPSTREAM.json'),'utf8'));
if(process.argv.length!==4)throw Error('Usage: node probe_e04_rng.cjs PACKAGE NEW_OUTPUT_JSON');
const packageRoot=path.resolve(process.argv[2]),outputPath=path.resolve(process.argv[3]);
const filename=path.join(packageRoot,'lib/elk-worker.js');
const bytes=fs.readFileSync(filename),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
for(const [name,expected] of Object.entries(lock.distribution.sha256Files))
 if(sha(fs.readFileSync(path.join(packageRoot,name)))!==expected)throw Error('Package SHA drift: '+name);
const bridge='\nmodule.exports.__E04RandomBridge={make:s=>new Random_0(fromDouble_0(s)),bits:$nextInternal,int:$nextInt,long:$nextLong,double:$nextDouble,setSeed:$setSeed_0};\n';
const source=bytes.toString('utf8')+bridge;
const compiled=new Module(filename,module);compiled.filename=filename;compiled.paths=Module._nodeModulePaths(path.dirname(filename));compiled._compile(source,filename);
const r=compiled.exports.__E04RandomBridge;
const integer64=v=>BigInt.asIntN(64,BigInt(v.l)+(BigInt(v.m)<<22n)+(BigInt(v.h)<<44n)).toString();
const cases=[];
for(const seed of [1,7,-17,19,-2147483648,2147483647]){
 const random=r.make(seed),records=[];
 const add=(method,arg,operation)=>{
  const before={seedhi:random.seedhi,seedlo:random.seedlo},value=operation();
  records.push({method,arg,before,value,after:{seedhi:random.seedhi,seedlo:random.seedlo}});return value;
 };
 for(const bits of [1,24,26,27,31,32])add('next',bits,()=>r.bits(random,bits));
 for(const bound of [1,2,3,7,2147483647])add('nextInt',bound,()=>r.int(random,bound));
 add('nextDouble',null,()=>r.double(random));
 let long;
 add('nextLong',null,()=>{long=r.long(random);return integer64(long);});
 add('setSeedPreviousLong',null,()=>{r.setSeed(random,long);return null;});
 for(const bits of [32,1,24,32])add('next',bits,()=>r.bits(random,bits));
 cases.push({seed,records});
}
const report={schema:'py-elk-e04-generated-rng-oracle/v1',workerSha256:sha(bytes),instrumentedSourceSha256:sha(Buffer.from(source)),toolSha256:sha(fs.readFileSync(__filename)),
 baseline:{version:lock.javascript.version,commit:lock.javascript.commit},memoryOnlyBridge:bridge,cases,
 limitation:'Actual generated Java Random implementation interpreter/oracle; not Python production RNG or exact upstream Java source identity.'};
fs.writeFileSync(outputPath,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({cases:cases.length,operations:cases.reduce((n,c)=>n+c.records.length,0)}));
