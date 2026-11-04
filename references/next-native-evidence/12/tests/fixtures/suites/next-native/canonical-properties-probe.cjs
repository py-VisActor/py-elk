// Real importer -> copyProperties. Foreign registered option must retain full id.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__canonicalProperties=function(s){
 getInstance();registerLayoutAlgorithms(['layered','force']);$clinit_InternalProperties_1();
 const importer=new JsonImporter,root=$transformNode_0(importer,new JSONObject_0(s),null),g=new LGraph;
 $copyProperties(g,root);
 const property=new Property('org.eclipse.elk.force.model'),present=$hasProperty(g,property),value=present?$getProperty(g,property):null;
 const keys=[],it=$getAllProperties(g).keySet_0().iterator_0();while(it.hasNext_0())keys.push(it.next_1().getId());keys.sort();
 return {keys,foreignFullIdPresent:present,foreignValue:value===null?null:value.name_0,foreignValueShared:value===$getProperty_0(root,property),layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const observation=global.__canonicalProperties(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-canonical-properties-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,observation,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
