const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__snapshotDefault=function(){
 $clinit_CoreOptions();const origin=new MapPropertyHolder,one=new MapPropertyHolder,two=new MapPropertyHolder;
 $copyProperties(one,origin);$copyProperties(two,origin);
 const pad=$getProperty(one,PADDING_6),other=$getProperty(two,PADDING_6),enums=$getProperty(one,NODE_SIZE_OPTIONS_6),enums2=$getProperty(two,NODE_SIZE_OPTIONS_6);
 return {padding:[pad.top_0,pad.right,pad.bottom,pad.left],paddingStored:$hasProperty(one,PADDING_6),
  originPaddingAbsent:!$hasProperty(origin,PADDING_6),paddingIndependent:pad!==other,paddingCached:$getProperty(one,PADDING_6)===pad,
  enumShared:enums===enums2,enumAbsent:!$hasProperty(one,NODE_SIZE_OPTIONS_6),
  aspectNull:$getProperty(one,ASPECT_RATIO_5)==null,aspectAbsent:!$hasProperty(one,ASPECT_RATIO_5),
  borderNull:$getProperty(one,PORT_BORDER_OFFSET_0)==null,borderAbsent:!$hasProperty(one,PORT_BORDER_OFFSET_0)};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
const observation=global.__snapshotDefault();fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),pid:process.pid,parentPid:process.ppid,observation,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
