// Caller-selected actual metadata, local import and full recursive Box path.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__selectedRecursive=function(s){
 instance_2=null;SERVICE=getInstance();registerLayoutAlgorithms(s.algorithms);$clinit_CoreOptions();
 const input=JSON.parse(JSON.stringify(s.graph)),json=new JSONObject_0(input),importer=new JsonImporter,root=$transformNode_0(importer,json,null);$transformEdges_2(importer,json);
 const children=n=>{const a=[],it=$getChildren(n).iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const nodes=[];function visit(n){nodes.push(n);children(n).forEach(visit);}visit(root);
 const properties=()=>s.observeProperties.map(id=>{const d=$getOptionDataBySuffix(SERVICE,id),has=!!d&&$hasProperty_0(root,d);let value=null;if(has){const v=$getProperty_0(root,d);value=d.type_0.ordinal===5?v.name_0:v;}return {id,has,value};});
 const beforeProperties=properties(),events=[],providers=new Map,recursion=[],executing=[],saved=[$layoutRecursively,$executeAlgorithm,$fetch,$release];let serial=0;
 const token=p=>{if(!providers.has(p))providers.set(p,++serial);return providers.get(p);};
 const geometry=n=>({id:n.identifier,x:n.x_0,y:n.y_0,width:n.width_0,height:n.height});
 $layoutRecursively=function(...args){const n=args[1];recursion.push(n.identifier);events.push({kind:'enter',node:n.identifier,geometry:geometry(n)});try{return saved[0](...args);}finally{events.push({kind:'leave',node:n.identifier,geometry:geometry(n)});recursion.pop();}};
 $executeAlgorithm=function(...args){const n=args[0];events.push({kind:'execute',node:n.identifier,geometry:geometry(n)});executing.push(n.identifier);try{return saved[1](...args);}finally{executing.pop();}};
 $fetch=function(pool){const before=pool.instances.size_0,out=saved[2](pool);events.push({kind:'fetch',node:recursion[recursion.length-1]||null,execution:executing.length?executing[executing.length-1]:null,before,after:pool.instances.size_0,provider:token(out)});return out;};
 $release=function(pool,p){const before=pool.instances.size_0,out=saved[3](pool,p);events.push({kind:'release',execution:executing.length?executing[executing.length-1]:null,before,after:pool.instances.size_0,provider:token(p)});return out;};
 const monitor=new BasicProgressMonitor;try{$layout_3(new RecursiveGraphLayoutEngine,root,monitor);}finally{[$layoutRecursively,$executeAlgorithm,$fetch,$release]=saved;}
 forEach_43(new ElkGraphUtil$PropertiesSkippingTreeIterator(root),new JsonImporter$lambda$35$Type(importer));forEach_43(new ElkGraphUtil$PropertiesSkippingTreeIterator(root),new JsonImporter$lambda$36$Type(importer));
 const descriptor=$getProperty_0(root,RESOLVED_ALGORITHM),pool=descriptor.providerPool,queued=[],it=pool.instances.iterator_0();while(it.hasNext_0())queued.push(token(it.next_1()));
 const metadata=map=>getLayoutData(($clinit_Collections(),new Collections$UnmodifiableCollection(new AbstractMap$2(map))));
 return {result:input,beforeProperties,afterProperties:properties(),metadata:{algorithms:metadata(SERVICE.layoutAlgorithmMap),options:metadata(SERVICE.layoutOptionMap),categories:metadata(SERVICE.layoutCategoryMap)},
 nativeOnlySetup:null,descriptors:nodes.map(n=>({id:n.identifier,present:$hasProperty_0(n,RESOLVED_ALGORITHM),algorithm:$hasProperty_0(n,RESOLVED_ALGORITHM)?$getProperty_0(n,RESOLVED_ALGORITHM).id_0:null,hierarchy:$getProperty_0(n,HIERARCHY_HANDLING_0).name_0})),
 events,providerCount:providers.size,queuedProviders:queued,geometry:nodes.map(geometry),scaleFactors:nodes.map(n=>[n.identifier,$getProperty_0(n,TOPDOWN_SCALE_FACTOR_2)]),monitor:{name:monitor.taskName,closed:monitor.closed_0},layoutExecuted:true};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation:global.__selectedRecursive(JSON.parse(requestRaw)),candidateExecuted:false,fullValidation:false},null,2)+'\n',{flag:'wx'});
