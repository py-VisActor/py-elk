const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const [pkgArg,requestPath,out]=process.argv.slice(2),pkg=path.resolve(pkgArg),worker=path.join(pkg,'lib/elk-worker.js'),raw=fs.readFileSync(worker),r=JSON.parse(fs.readFileSync(requestPath)),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('worker differs');global.__ceilInput=r;
const bridge=String.raw`
global.__actualSelectorCeil=function(){getInstance();$clinit_LayeredOptions();$clinit_InternalProperties_1();$clinit_LNode$NodeType();$clinit_LabelSide();
 const r=global.__ceilInput,g=new LGraph,n=new LNode(g),p=new LPort,e=new LEdge,l=new LLabel,labels=new ArrayList;
 n.type_0=LABEL;n.size_0.y_0=r.height;$setNode(p,n);$setProperty_0(g,SPACING_EDGE_LABEL_0,r.spacing);$setProperty_0(e,EDGE_THICKNESS_0,r.thickness);$setProperty_0(l,EDGE_LABELS_INLINE_0,true);$add_3(labels,l);$setProperty_0(n,ORIGIN_0,e);$setProperty_0(n,REPRESENTED_LABELS,labels);
 $applyLabelSide_1(n,ABOVE);return {side:$getProperty(n,LABEL_SIDE).name_0,portY:Object.is(p.pos.y_0,-0)?'-0':p.pos.y_0,height:n.size_0.y_0};};`;
const m=new Module(worker,module);m.filename=worker;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,worker);
fs.writeFileSync(out,JSON.stringify({workerSha256:sha(raw),requestSha256:sha(fs.readFileSync(requestPath)),probeSha256:sha(fs.readFileSync(__filename)),value:global.__actualSelectorCeil(),layoutExecuted:false,pid:process.pid},null,2)+'\n',{flag:'wx'});
