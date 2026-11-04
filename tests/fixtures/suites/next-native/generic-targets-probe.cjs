// Actual JsonImporter + selected global LayoutConfigurator, no layout.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),Module=require('node:module');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const [pkgArg,requestPath,outPath]=process.argv.slice(2),pkg=path.resolve(pkgArg),workerPath=path.join(pkg,'lib/elk-worker.js');
const raw=fs.readFileSync(workerPath),requestRaw=fs.readFileSync(requestPath);
if(sha(raw)!=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86')throw Error('Worker differs');
const bridge=String.raw`
global.__genericTargets=function(s){
 registerLayoutAlgorithms(['layered']);const input=JSON.parse(JSON.stringify(s.graph)),before=JSON.stringify(input),ji=new JsonImporter,json=new JSONObject_0(input),root=$transformNode_0(ji,json,null);$transformEdges_2(ji,json);
 const lc=optsToCfg(new JSONObject_0(s.global));applyVisitors(root,stampJavaTypeInfo(getClassLiteralForArray(Lorg_eclipse_elk_core_util_IGraphElementVisitor_2_classLit,1),$intern_2,544,0,[lc]));
 const list=l=>{const a=[],it=l.iterator_0();while(it.hasNext_0())a.push(it.next_1());return a;};
 const a=list($getChildren(root))[0],b=list($getChildren(root))[1],port=list($getPorts_3(a))[0],edge=list($getContainedEdges(root))[0];
 const holders=[['root',root],['a',a],['b',b],['port',port],['edge',edge],['rootLabel',list(root.getLabels_0())[0]],['aLabel',list(a.getLabels_0())[0]],['portLabel',list(port.getLabels_0())[0]],['edgeLabel',list(edge.getLabels_0())[0]]];
 const keys=['org.eclipse.elk.font.name','org.eclipse.elk.priority','org.eclipse.elk.nodeSize.constraints','org.eclipse.elk.layered.crossingMinimization.semiInteractive'];
 const encode=v=>v==null?null:typeof v==='object'&&'value_0'in v?v.value_0:typeof v.iterator_0==='function'?list(v).map(x=>x.name_0):v;
 const rows=holders.map(([id,h])=>({id,properties:keys.map(key=>{const p=$getOptionDataBySuffix(SERVICE,key),present=$hasProperty_0(h,p);return{id:key,present,value:present?encode($getProperty_0(h,p)):null};})}));
 const p=$getOptionDataBySuffix(SERVICE,'org.eclipse.elk.nodeSize.constraints'),rv=$getProperty_0(root,p),av=$getProperty_0(a,p),bv=$getProperty_0(b,p);
 return {rows,globalEnumSetShared:rv===bv,localEnumSetIndependent:av!==rv,inputBefore:before,inputAfter:JSON.stringify(input),layoutExecuted:false};
};`;
const m=new Module(workerPath,module);m.filename=workerPath;m.paths=Module._nodeModulePaths(pkg);m._compile(raw.toString()+bridge,workerPath);
const value=global.__genericTargets(JSON.parse(requestRaw));
fs.writeFileSync(outPath,JSON.stringify({schema:'py-elk-next-generic-targets-observation/v1',workerSha256:sha(raw),probeSha256:sha(fs.readFileSync(__filename)),requestSha256:sha(requestRaw),pid:process.pid,parentPid:process.ppid,node:process.version,value,candidateExecuted:false,layoutExecuted:false},null,2)+'\n',{flag:'wx'});
