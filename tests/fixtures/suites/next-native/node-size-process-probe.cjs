// Complete source standalone process over real LGraph adapters, not generic
// ElkGraph adapters or a full layered/public layout pipeline.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__sizeProcess=function(s){
 $clinit_CoreOptions();$clinit_PortSide();
 const sides={NORTH:NORTH_3,EAST:EAST_2,SOUTH:SOUTH_2,WEST:WEST_2};
 const props=(object,values)=>{for(const[id,v]of Object.entries(values||{})){const option=$getOptionDataBySuffix(getInstance(),id);if(!option)throw Error(id);$setProperty(object,option,$parseValue(option,v));}};
 const label=spec=>{const l=new LLabel;[l.pos.x_0,l.pos.y_0]=spec.pos||[0,0];[l.size_0.x_0,l.size_0.y_0]=spec.size;props(l,spec.options);return l;};
 const g=new LGraph,n=new LNode(g);[n.pos.x_0,n.pos.y_0]=s.pos||[0,0];[n.size_0.x_0,n.size_0.y_0]=s.size;
 props(g,s.graphOptions);props(n,s.options);
 const ports=[];
 for(const item of s.ports||[]){const p=new LPort;$setNode(p,n);p.side=sides[item.side];[p.size_0.x_0,p.size_0.y_0]=item.size||[4,4];[p.pos.x_0,p.pos.y_0]=item.pos||[0,0];props(p,item.options);for(const l of item.labels||[])$add_3(p.labels,label(l));ports.push(p);}
 for(const l of s.labels||[])$add_3(n.labels,label(l));
 const lv=l=>[l.pos.x_0,l.pos.y_0,l.size_0.x_0,l.size_0.y_0];
 const snapshot=()=>({node:{pos:[n.pos.x_0,n.pos.y_0],size:[n.size_0.x_0,n.size_0.y_0],padding:[n.padding.top_0,n.padding.right,n.padding.bottom,n.padding.left],labels:n.labels.array.map(lv)},ports:ports.map(p=>({pos:[p.pos.x_0,p.pos.y_0],size:[p.size_0.x_0,p.size_0.y_0],labels:p.labels.array.map(lv)}))});
 const before=snapshot(),ga=new LGraphAdapters$LGraphAdapter(g,true,false,null),na=new LGraphAdapters$LNodeAdapter(ga,n,true);
 const staged=process(ga,na,s.apply!==false,false);
 return {before,stagedSize:[staged.x_0,staged.y_0],after:snapshot()};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const results=JSON.parse(requestRaw).cases.map(s=>({id:s.id,value:global.__sizeProcess(s)}));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-node-size-process-observation/v1',mode:'unchanged-worker-standalone-process-LGraph-adapter',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,results,candidateExecuted:false,fullLayoutValidated:false},null,2)+'\n',{flag:'wx'});
