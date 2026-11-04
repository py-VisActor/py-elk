const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__poolDeprecated=function(){
 registerLayoutAlgorithms(['layered']);
 const arr=l=>{const a=[],it=l.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const events=[],factory={next:0,create_0(){const o={id:++this.next};events.push('create:'+o.id);return o;},destroy(o){events.push('destroy:'+o.id);}};
 const pool=new InstancePool(factory),a=$fetch(pool),b=$fetch(pool);$release(pool,a);$release(pool,b);
 const fifo=[$fetch(pool).id,$fetch(pool).id];pool.limit=0;$release(pool,a);pool.limit=1;$release(pool,a);$release(pool,b);fifo.push($fetch(pool).id);pool.limit=-7;$release(pool,a);$release(pool,b);fifo.push($fetch(pool).id,$fetch(pool).id);
 const normalEvents=[],failure=new Error('layout fault'),fetchFailure=new Error('fetch fault');let shouldThrow=false,serial=0;
 const realFactory={create_0(){const p=new FixedLayoutProvider;p.serial=++serial;const real=p.layout;p.layout=function(node,monitor){normalEvents.push('layout:'+this.serial);if(shouldThrow)throw failure;return real.call(this,node,monitor);};normalEvents.push('create:'+p.serial);return p;},destroy(p){normalEvents.push('destroy:'+p.serial);}};
 const data=new LayoutAlgorithmData($providerFactory($id(new LayoutAlgorithmData$Builder,'org.eclipse.elk.fixed'),realFactory));
 const sameId=new LayoutAlgorithmData($providerFactory($id(new LayoutAlgorithmData$Builder,'org.eclipse.elk.fixed'),realFactory));
 const ji=new JsonImporter,json=new JSONObject_0({id:'r',children:[{id:'n',x:5,y:7,width:10,height:20}]}),root=$transformNode_0(ji,json,null);$transformEdges_2(ji,json);
 const monitor=new BasicProgressMonitor;$executeAlgorithm(root,data,monitor);const first=data.providerPool.instances.size_0;
 $executeAlgorithm(root,data,new BasicProgressMonitor);shouldThrow=true;let sameLayoutFailure=false;
 try{$executeAlgorithm(root,data,new BasicProgressMonitor);}catch(e){sameLayoutFailure=e===failure;}
 const afterFailure=data.providerPool.instances.size_0;shouldThrow=false;$executeAlgorithm(root,data,new BasicProgressMonitor);
 const bad={providerPool:new InstancePool({create_0(){throw fetchFailure;},destroy(){throw Error('unexpected destroy');}})};let sameFetchFailure=false;
 try{$executeAlgorithm(root,bad,new BasicProgressMonitor);}catch(e){sameFetchFailure=e===fetchFailure;}
 const execution={events:normalEvents,firstPoolSize:first,afterFailure,sameLayoutFailure,sameFetchFailure,dimensions:[root.width_0,root.height],task:monitor.taskName,childTasks:monitor.children?monitor.children.size_0:0,distinctEqualIdPools:data.providerPool!==sameId.providerPool};
 const json2=new JSONObject_0({id:'legacy',layoutOptions:{'elk.portLabels.nextToPortIfPossible':false,'elk.nodeSize.options':'SPACE_EFFICIENT_PORT_LABELS'},children:[{id:'default'},{id:'explicit',layoutOptions:{'elk.portLabels.placement':'INSIDE'}}]}),ji2=new JsonImporter,node=$transformNode_0(ji2,json2,null);$transformEdges_2(ji2,json2);
 const get=(n,key)=>$getProperty_0(n,key),has=(n,key)=>$hasProperty_0(n,key),view=n=>({legacy:has(n,PORT_LABELS_NEXT_TO_PORT_IF_POSSIBLE_0),placementPresent:has(n,PORT_LABELS_PLACEMENT_5),placement:arr(get(n,PORT_LABELS_PLACEMENT_5)).map(e=>e.name_0),optionsPresent:has(n,NODE_SIZE_OPTIONS_6),options:arr(get(n,NODE_SIZE_OPTIONS_6)).map(e=>e.name_0)});
 const shared=get(node,PORT_LABELS_PLACEMENT_5),before=view(node);new DeprecatedLayoutOptionReplacer().visit(node);
 const deprecated={before,after:view(node),defaultChild:view($getChildren(node).get_0(0)),explicitChild:view($getChildren(node).get_0(1)),sameShared:get(node,PORT_LABELS_PLACEMENT_5)===shared&&get($getChildren(node).get_0(0),PORT_LABELS_PLACEMENT_5)===shared};
 return {pool:{events,fifo},execution,deprecated};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const observation=global.__poolDeprecated();fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,parentPid:process.ppid,observation,scope:'New pool protocol plus real Fixed body and per-element deprecated rules, no whole coordinator'},null,2)+'\n',{flag:'wx'});
