// New real outer recursive DisCo and underlying Fixed use shared descriptor pools.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__recursiveSharedPool=function(s){
 registerLayoutAlgorithms(['layered','disco']);$clinit_CoreOptions();
 const input=JSON.parse(JSON.stringify(s.graph)),json=new JSONObject_0(input),importer=new JsonImporter,root=$transformNode_0(importer,json,null);$transformEdges_2(importer,json);
 const children=n=>{const a=[],it=$getChildren(n).iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 if(s.nativeOnlySetup&&s.nativeOnlySetup.rootResolvedAlgorithm)$setProperty_1(root,RESOLVED_ALGORITHM,$getAlgorithmData(getInstance(),s.nativeOnlySetup.rootResolvedAlgorithm));
 const nodes=[];function visit(n){nodes.push(n);children(n).forEach(visit);}visit(root);
 const poolNames=new Map(s.observePools.map(id=>[$getAlgorithmData(getInstance(),id).providerPool,id])),usedPools=new Set;
 const events=[],providers=new Map,recursion=[],executing=[],saved=[$layoutRecursively,$executeAlgorithm,$fetch,$release];let providerSerial=0;
 const token=p=>{if(!providers.has(p))providers.set(p,++providerSerial);return providers.get(p);};
 const geometry=n=>({id:n.identifier,x:n.x_0,y:n.y_0,width:n.width_0,height:n.height});
 $layoutRecursively=function(...args){const n=args[1];recursion.push(n.identifier);events.push({kind:'enter',node:n.identifier,geometry:geometry(n)});try{return saved[0](...args);}finally{events.push({kind:'leave',node:n.identifier,geometry:geometry(n)});recursion.pop();}};
 $executeAlgorithm=function(...args){const n=args[0];events.push({kind:'execute',node:n.identifier,geometry:geometry(n)});executing.push(n.identifier);try{return saved[1](...args);}finally{executing.pop();}};
 $fetch=function(pool){if(!poolNames.has(pool))throw Error('Unexpected actual provider pool');usedPools.add(pool);const before=pool.instances.size_0,out=saved[2](pool);events.push({kind:'fetch',algorithm:poolNames.get(pool),node:recursion[recursion.length-1]||null,execution:executing.length?executing[executing.length-1]:null,before,after:pool.instances.size_0,provider:token(out)});return out;};
 $release=function(pool,p){const before=pool.instances.size_0,out=saved[3](pool,p);events.push({kind:'release',algorithm:poolNames.get(pool),execution:executing.length?executing[executing.length-1]:null,before,after:pool.instances.size_0,provider:token(p)});return out;};
 const monitor=new BasicProgressMonitor;try{$layout_3(new RecursiveGraphLayoutEngine,root,monitor);}finally{[$layoutRecursively,$executeAlgorithm,$fetch,$release]=saved;}
 const iterator=new ElkGraphUtil$PropertiesSkippingTreeIterator(root);forEach_43(iterator,new JsonImporter$lambda$35$Type(importer));forEach_43(new ElkGraphUtil$PropertiesSkippingTreeIterator(root),new JsonImporter$lambda$36$Type(importer));
 const descriptor=$getProperty_0(root,RESOLVED_ALGORITHM),pool=descriptor.providerPool,queued=[],it=pool.instances.iterator_0();while(it.hasNext_0())queued.push(token(it.next_1()));
 return {result:input,pools:Array.from(usedPools).map(pool=>({algorithm:poolNames.get(pool),fetches:events.filter(e=>e.kind==='fetch'&&e.algorithm===poolNames.get(pool)).length,releases:events.filter(e=>e.kind==='release'&&e.algorithm===poolNames.get(pool)).length,queued:Array.from((()=>{const a=[],it=pool.instances.iterator_0();while(it.hasNext_0())a.push(token(it.next_1()));return a;})())})),nativeOnlySetup:s.nativeOnlySetup||null,descriptors:nodes.map(n=>({id:n.identifier,present:$hasProperty_0(n,RESOLVED_ALGORITHM),algorithm:$hasProperty_0(n,RESOLVED_ALGORITHM)?$getProperty_0(n,RESOLVED_ALGORITHM).id_0:null,hierarchy:$getProperty_0(n,HIERARCHY_HANDLING_0).name_0})),events,providerCount:providers.size,queuedProviders:queued,geometry:nodes.map(geometry),scaleFactors:nodes.map(n=>[n.identifier,$getProperty_0(n,TOPDOWN_SCALE_FACTOR_2)]),monitor:{name:monitor.taskName,closed:monitor.closed_0},layoutExecuted:true};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__recursiveSharedPool(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-recursive-sharedpool-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false},null,2)+'\n',{flag:'wx'});
