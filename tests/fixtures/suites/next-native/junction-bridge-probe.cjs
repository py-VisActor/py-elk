const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker),requestBytes=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__junctionBridge=function(cases){
 registerLayoutAlgorithms(['layered']);return cases.map(c=>{
  const input={id:'r',children:[{id:'a'},{id:'b'}],edges:[{id:'e',sources:['a'],targets:['b'],junctionPoints:[{x:90,y:91}]}]};
  if(c.typed!==undefined)input.edges[0].layoutOptions={'elk.junctionPoints':c.typed};
  const importer=new JsonImporter,json=new JSONObject_0(input),root=$transformNode_0(importer,json,null);$transformEdges_2(importer,json);
  const edge=$getChildren(root).get_0(0).getOutgoingEdges_0().get_0(0),key=JUNCTION_POINTS_0;
  if(c.operation==='remove'||c.operation==='rematerialize')$setProperty_1(edge,key,null);
  if(c.operation==='generated'){const chain=new KVectorChain;c.points.forEach(p=>$add_7(chain,new KVector_1(...p)));$setProperty_1(edge,key,chain.size_0?chain:null);}
  if(c.offset)lambda$1_22(...c.offset,edge);
  if(c.operation==='rematerialize')$getProperty_0(edge,key);
  const holder=new ElkNodeImpl;$copyProperties_0(holder,edge);
  const present=$hasProperty_0(edge,key),snapshotHas=$hasProperty_0(holder,key);
  forEach_43(new ElkGraphUtil$PropertiesSkippingTreeIterator(root),new JsonImporter$lambda$35$Type(importer));
  forEach_43(new ElkGraphUtil$PropertiesSkippingTreeIterator(root),new JsonImporter$lambda$36$Type(importer));
  return {id:c.id,present,snapshotHas,points:input.edges[0].junctionPoints};
 });
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const cases=global.__junctionBridge(JSON.parse(requestBytes).cases);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestBytes),pid:process.pid,parentPid:process.ppid,cases,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
