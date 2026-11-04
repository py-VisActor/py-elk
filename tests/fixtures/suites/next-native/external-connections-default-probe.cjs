const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__externalDefault=function(){
 getInstance();$clinit_InternalProperties_1();
 const missing=new LGraph,another=new LGraph,storedNull=new LGraph,explicit=new LGraph;
 storedNull.propertyMap=new HashMap;$put_6(storedNull.propertyMap,EXT_PORT_CONNECTIONS,null);
 const universe=$getEnumConstants(Lorg_eclipse_elk_core_options_PortSide_2_classLit),empty=new EnumSet$EnumSetImpl(universe,createFrom(universe,universe.length),0);$setProperty_0(explicit,EXT_PORT_CONNECTIONS,empty);
 const all=[missing,another,storedNull,explicit],before=all.map(g=>$hasProperty(g,EXT_PORT_CONNECTIONS)),a=$getProperty(missing,EXT_PORT_CONNECTIONS),b=$getProperty(another,EXT_PORT_CONNECTIONS),c=$getProperty(storedNull,EXT_PORT_CONNECTIONS),d=$getProperty(explicit,EXT_PORT_CONNECTIONS);
 const component=new ComponentsCompactor$InternalComponent(missing);component.rectilinearConvexHull=new ArrayList;$add_3(component.rectilinearConvexHull,new ElkRectangle_0(1,2,3,4));
 const connected=new ComponentsCompactor$InternalConnectedComponents;$add_3(connected.components,component);
 const graph=$transform_0(new ComponentsToCGraphTransformer(5),connected),node=graph.cNodes.array[0];
 return {before,after:all.map(g=>$hasProperty(g,EXT_PORT_CONNECTIONS)),sameShared:a===b&&a===c&&a===$getProperty(missing,EXT_PORT_CONNECTIONS),explicitSame:d===empty,explicitDistinct:d!==a,allEmpty:[a,b,c,d].map(x=>x.isEmpty()),defaultCloneType:instanceOf(a,4),lock:[node.lock.left,node.lock.right,node.lock.up,node.lock.down],transformCounts:[graph.cGroups.array.length,graph.cNodes.array.length],stillAbsentAfterTransform:!$hasProperty(missing,EXT_PORT_CONNECTIONS)};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),value:global.__externalDefault(),pid:process.pid,parentPid:process.ppid,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
