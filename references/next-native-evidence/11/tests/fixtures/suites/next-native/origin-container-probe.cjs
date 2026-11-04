// Source origin identifier follows the actual imported model eContainer.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__originContainer=function(s){
 registerLayoutAlgorithms(['layered']);$clinit_InternalProperties_1();const importer=new JsonImporter,json=new JSONObject_0(JSON.parse(JSON.stringify(s))),root=$transformNode_0(importer,json,null);$transformEdges_2(importer,json);
 const list=l=>{const a=[];if(l){const it=l.iterator_0();while(it.hasNext_0())a.push(it.next_1());}return a;};
 const child=$getChildren(root).get_0(0),a=$getChildren(child).get_0(0),all=list(root.containedEdges).concat(list(child.containedEdges)),edge=all.find(e=>e.identifier==='e'),label=list(edge.labels)[0],port=$getPorts_3(a).get_0(0);
 const origin=element=>{const n=new LNode(null);$setProperty_0(n,ORIGIN_0,element);return getOriginIdentifier(n);};
 return {containedAtRoot:list(root.containedEdges).map(e=>e.identifier),containedAtChild:list(child.containedEdges).map(e=>e.identifier),edgeContainer:edge.eContainer_0().identifier,labelContainer:label.eContainer_0().identifier,identifiers:{edge:getIdentifier(edge),label:getIdentifier(label),port:getIdentifier(port)},originIdentifiers:{edge:origin(edge),label:origin(label),port:origin(port)},layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__originContainer(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-origin-container-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
