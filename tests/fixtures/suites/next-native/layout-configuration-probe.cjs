// Source object API only: lazy buckets, membership, copying and clear return.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__layoutConfiguration=function(s){
 getInstance();$clinit_LayeredPhases();$clinit_IntermediateProcessorStrategy();
 const phases=[P1_CYCLE_BREAKING,P2_LAYERING,P3_NODE_ORDERING,P4_NODE_PLACEMENT,P5_EDGE_ROUTING];
 const processors=s.processors.map((name,i)=>new IntermediateProcessorStrategy(name,i));
 const c=new LayoutProcessorConfiguration,list=c.list;
 const saved=$getListItem(c,s.initialReadIndex),initialBuckets=list.array.slice();
 const initial={currentIndex:c.currentIndex,length:list.array.length,distinct:initialBuckets.every((x,i)=>initialBuckets.every((y,j)=>i===j||x!==y))};
 const fluent=$before(c,phases[s.beforePhase])===c;
 for(const index of s.beforeMembers)$add_17(c,processors[index]);
 const copy=createFrom_0(c),copyBucket=$getListItem(copy,s.beforePhase),originalBucket=$getListItem(c,s.beforePhase);
 const sharesProcessorObjects=$contains_6(copyBucket,processors[0])&&$contains_6(originalBucket,processors[0]);
 $add_6(copyBucket,processors[s.copyExtraProcessor]);
 const membership=cfg=>cfg.list.array.map(bucket=>bucket===null?null:processors.map(p=>$contains_6(bucket,p)));
 const copyState={listDistinct:copy.list!==list,bucketsDistinct:copy.list.array.every((bucket,i)=>bucket!==list.array[i]),sharesProcessorObjects,currentIndex:copy.currentIndex,original:membership(c),copy:membership(copy)};
 const tailFluent=$addAfter(c,phases[s.tailPhase],processors[s.tailProcessor])===c;
 const tail={currentIndex:c.currentIndex,length:list.array.length,membership:membership(c)};
 $setListItem(c,s.nullIndex,null);const explicitNull=$getListItem(c,s.nullIndex)===null;
 const cleared=$clear_10(c),clear={returnUndefined:cleared===undefined,listIdentity:c.list===list,length:c.list.array.length,currentIndex:c.currentIndex,detachedBucketStillAlive:saved!==null};
 const fresh=$getListItem(c,s.initialReadIndex);
 return {initial,fluent,copyState,tailFluent,tail,explicitNull,clear,newBucket:fresh!==saved,newBucketsEmpty:membership(c),sourceObjectApi:true,layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__layoutConfiguration(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-layout-configuration-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
