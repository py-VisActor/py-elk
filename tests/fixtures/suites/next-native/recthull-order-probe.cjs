const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),sha=b=>crypto.createHash('sha256').update(b).digest('hex'),raw=fs.readFileSync(worker);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');
const bridge=String.raw`
global.__rectOrder=function(){
 $clinit_RectilinearConvexHull();$clinit_Point$Quadrant();
 const saved=[execute_0,addConcaveCorners],calls=[];let failed=false,error;
 execute_0=function(...a){calls.push(['sweep',a[2].array[0].quadrant.name_0]);return saved[0](...a);};
 addConcaveCorners=function(...a){calls.push(['concave',a[1].name_0]);return saved[1](...a);};
 try{of_5(new ArrayList);}catch(e){failed=true;error=String(e);}finally{[execute_0,addConcaveCorners]=saved;}
 return {value:{calls,failed},rawError:error};
};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(outPath,JSON.stringify({workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),...global.__rectOrder(),pid:process.pid,parentPid:process.ppid,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
